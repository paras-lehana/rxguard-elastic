"""
LLM generation — AWS Bedrock primary, platform proxy for the live demo.
======================================================================

Two providers behind one interface. `BedrockProvider` is the production path
and is written against the real `bedrock-runtime.Converse` API, including the
tool-use loop the agents rely on. `PlatformProvider` calls the Lehana platform
LLM proxy and exists for one reason: the public demo has to answer while no AWS
credential is present.

The provider that actually ran is returned on every response and written into
the audit trail, so an answer produced by the fallback is never displayed or
logged as an AWS-generated one. `LLM_PROVIDER=bedrock` disables the fallback
entirely, which is the setting to use for a judged run.
"""

import hashlib
import json
import logging
import re

import requests

from . import config

logger = logging.getLogger(__name__)


class LLMResult:
    """A generation plus the provenance needed to make it auditable."""

    def __init__(self, text, provider, model, prompt, usage=None,
                 degraded=False):
        self.text = text
        self.provider = provider
        self.model = model
        self.usage = usage or {}
        self.degraded = degraded
        self.prompt_sha256 = hashlib.sha256(prompt.encode()).hexdigest()

    def as_dict(self):
        return {
            'provider': self.provider,
            'model': self.model,
            'prompt_sha256': self.prompt_sha256,
            'usage': self.usage,
            # True whenever the answer did NOT come from AWS Bedrock.
            'degraded': self.degraded,
        }

    def json(self):
        """
        Parse the generation as JSON, tolerating fenced code blocks.

        Models honour `json_mode` well but not perfectly; stripping a ```json
        fence is cheaper than a retry and loses nothing.
        """
        raw = (self.text or '').strip()
        fence = re.match(r'^```(?:json)?\s*(.*?)\s*```$', raw, re.DOTALL)
        if fence:
            raw = fence.group(1)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Last resort: the outermost {...} span.
            start, end = raw.find('{'), raw.rfind('}')
            if start != -1 and end > start:
                try:
                    return json.loads(raw[start:end + 1])
                except json.JSONDecodeError:
                    pass
        return None


# ─── AWS Bedrock (production) ────────────────────────────────────────────────

def _bedrock_client():
    import boto3
    return boto3.client(
        'bedrock-runtime',
        region_name=config.AWS_REGION,
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
    )


def _generate_bedrock(system, user, json_mode=False, max_tokens=2048,
                      temperature=0.2):
    """
    Generate via the Bedrock Converse API.

    Converse rather than InvokeModel because it normalises the message shape
    across Nova, Claude and Llama — swapping BEDROCK_MODEL_ID needs no code
    change — and because it is the API the tool-use loop in
    `converse_with_tools` builds on.
    """
    client = _bedrock_client()
    instruction = system
    if json_mode:
        instruction += (
            '\n\nRespond with a single valid JSON object and nothing else. '
            'No prose, no markdown fence.'
        )
    response = client.converse(
        modelId=config.BEDROCK_MODEL_ID,
        system=[{'text': instruction}],
        messages=[{'role': 'user', 'content': [{'text': user}]}],
        inferenceConfig={'maxTokens': max_tokens, 'temperature': temperature},
    )
    text = ''.join(
        block.get('text', '')
        for block in response['output']['message']['content']
    )
    usage = response.get('usage', {})
    return LLMResult(
        text=text,
        provider='aws-bedrock',
        model=config.BEDROCK_MODEL_ID,
        prompt=instruction + user,
        usage={'input_tokens': usage.get('inputTokens'),
               'output_tokens': usage.get('outputTokens')},
        degraded=False,
    )


def converse_with_tools(system, user, tools, tool_impls, max_turns=4,
                        temperature=0.2):
    """
    Bedrock tool-use loop — the mechanism behind the RxGuard agents.

    `tools` is a list of Bedrock toolSpec dicts; `tool_impls` maps tool name to
    a callable. The model decides which retrieval tools to call and in what
    order; we execute them against Elasticsearch and feed results back until it
    stops requesting tools. Requires AWS credentials.

    Returns (LLMResult, trace) where trace is the ordered list of tool calls —
    the explainability record for the audit trail.
    """
    if not config.aws_configured():
        raise RuntimeError('Bedrock tool-use requires AWS credentials')

    client = _bedrock_client()
    messages = [{'role': 'user', 'content': [{'text': user}]}]
    trace = []

    for _ in range(max_turns):
        response = client.converse(
            modelId=config.BEDROCK_MODEL_ID,
            system=[{'text': system}],
            messages=messages,
            toolConfig={'tools': tools},
            inferenceConfig={'temperature': temperature, 'maxTokens': 2048},
        )
        out = response['output']['message']
        messages.append(out)

        if response.get('stopReason') != 'tool_use':
            text = ''.join(b.get('text', '') for b in out['content'])
            return (
                LLMResult(text, 'aws-bedrock', config.BEDROCK_MODEL_ID,
                          system + user, response.get('usage', {})),
                trace,
            )

        results = []
        for block in out['content']:
            if 'toolUse' not in block:
                continue
            call = block['toolUse']
            impl = tool_impls.get(call['name'])
            try:
                output = impl(**call['input']) if impl else {
                    'error': f"unknown tool {call['name']}"
                }
            except Exception as exc:
                output = {'error': str(exc)}
            trace.append({'tool': call['name'], 'input': call['input'],
                          'output_summary': _summarise(output)})
            results.append({'toolResult': {
                'toolUseId': call['toolUseId'],
                'content': [{'json': output}],
            }})
        messages.append({'role': 'user', 'content': results})

    raise RuntimeError(f'tool-use loop exceeded {max_turns} turns')


def _summarise(output):
    """Keep the audit trace small — ids and counts, not whole documents."""
    if isinstance(output, dict):
        if 'hits' in output and isinstance(output['hits'], list):
            return {'hit_count': len(output['hits']),
                    'ids': [h.get('_id') for h in output['hits'][:10]]}
        return {k: str(v)[:120] for k, v in list(output.items())[:6]}
    return {'value': str(output)[:200]}


# ─── Platform proxy (demo only) ──────────────────────────────────────────────

def _generate_platform(system, user, json_mode=False, max_tokens=2048,
                       temperature=0.2):
    headers = {'Content-Type': 'application/json'}
    if config.PLATFORM_LLM_KEY:
        headers['X-Internal-Key'] = config.PLATFORM_LLM_KEY

    payload = {
        'messages': [{'role': 'user', 'content': user}],
        'system_prompt': system,
        'json_mode': json_mode,
        'max_tokens': max_tokens,
        'temperature': temperature,
    }
    res = requests.post(config.PLATFORM_LLM_URL, headers=headers, json=payload,
                        timeout=config.REQUEST_TIMEOUT)
    res.raise_for_status()
    body = res.json()
    text = body.get('choices', [{}])[0].get('message', {}).get('content', '')
    return LLMResult(
        text=text,
        provider='platform-proxy',
        model=body.get('model', 'unknown'),
        prompt=system + user,
        usage=body.get('usage', {}),
        # Always degraded: this is not the AWS path the architecture specifies.
        degraded=True,
    )


# ─── Public entry point ──────────────────────────────────────────────────────

def generate(system, user, json_mode=False, max_tokens=2048, temperature=0.2):
    """
    Generate text with the configured provider.

    'bedrock'  → Bedrock only; raises if unavailable (correct for judged runs)
    'platform' → demo proxy only
    'auto'     → Bedrock when credentials exist, otherwise the demo proxy
    """
    mode = config.LLM_PROVIDER
    use_bedrock = mode == 'bedrock' or (mode == 'auto' and config.aws_configured())

    if use_bedrock:
        try:
            return _generate_bedrock(system, user, json_mode, max_tokens,
                                     temperature)
        except Exception as exc:
            if mode == 'bedrock':
                raise
            logger.warning("Bedrock generation failed, falling back: %s", exc)

    if mode == 'bedrock':
        raise RuntimeError('LLM_PROVIDER=bedrock but AWS is not configured')

    return _generate_platform(system, user, json_mode, max_tokens, temperature)


def provider_report():
    """Which reasoning path is live — surfaced on /health and in the UI."""
    mode = config.LLM_PROVIDER
    active = 'aws-bedrock' if (mode == 'bedrock' or
                               (mode == 'auto' and config.aws_configured())) \
        else 'platform-proxy'
    return {
        'mode': mode,
        'active': active,
        'bedrock_model': config.BEDROCK_MODEL_ID,
        'bedrock_ready': config.aws_configured(),
        'aws_region': config.AWS_REGION,
        'note': (
            'AWS Bedrock is the specified production path. It activates on '
            'presence of AWS credentials with no code change; until then the '
            'platform proxy answers and every response is flagged degraded.'
        ) if not config.aws_configured() else 'Bedrock active.',
    }
