Phase 1: Add a Direct Chat Endpoint to the AWS RAG Microservice

I will navigate to endpoints and create an independent /api/chat route.
Instead of calling retrieve_and_generate (Knowledge Base queries), this new endpoint will simply use your existing boto3 client to call Anthropic Claude (e.g., anthropic.claude-3-haiku-20240307-v1:0 or Sonnet) via Bedrock's InvokeModel API block. This acts purely as a raw AI inference engine with no Vector Database constraints.
Phase 2: Refactor app.py in PharmAI Portal

Remove all traces of OpenRouter / Gemini.
Re-write the Tier 3 layer as search_tier3_bedrock_direct() mapped to the new /api/chat endpoint.
For the extract_medicines request, reroute it to use this new Direct Chat Bedrock function instead of search_tier2_aws. This allows Claude/Bedrock to freely read the full prescription payload and spit out the [{"name": "TELMA"...}] array natively without searching the Knowledge Base.
Phase 3: Clean up Constraints

We will expand the max token limit in doc-analysis from 3,000 characters to 15,000. Under a direct InvokeModel call, AWS Bedrock Models can handle over 50,000 tokens easily, meaning you'll get far smarter analysis on large multiple-page PDFs.