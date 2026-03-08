import re

with open('/root/repo/pharmai_portal/frontend/app.py', 'r') as f:
    content = f.read()

# 1. Update PHARMAI_SYSTEM_PROMPT
old_prompt = """PHARMAI_SYSTEM_PROMPT = (
    "You are PharmaAI, an expert Indian pharmaceutical assistant specialized "
    "in drug safety. When given a medicine name, composition, or scanned text "
    "from a medicine package, provide a comprehensive analysis:\\n\\n"
    "**Status:** Whether it is BANNED / RESTRICTED / ALLOWED in India "
    "(check CDSCO/FSSAI regulations)\\n"
    "**Safety:** Side effects, contraindications, drug interactions, warnings\\n"
    "**Usage:** What it is used for, dosage guidelines\\n"
    "**Regulatory:** CDSCO schedule classification, gazette notifications if banned\\n"
    "**Alternatives:** Safer alternatives if the medicine is banned or restricted\\n\\n"
    "**💰 Jan Aushadhi (Generic) Alternatives:**\\n"
    "For EVERY branded medicine mentioned, you MUST provide:\\n"
    "- The equivalent generic medicine available under Pradhan Mantri Bhartiya "
    "Janaushadhi Pariyojana (PMBJP)\\n"
    "- Approximate branded price vs. Jan Aushadhi generic price\\n"
    "- Percentage cost savings (e.g., '₹120 branded → ₹15 Jan Aushadhi = 87% savings')\\n"
    "- Nearest Jan Aushadhi Kendra availability tip\\n"
    "If no Jan Aushadhi equivalent exists, state that clearly.\\n\\n"
    "Be concise, accurate, and respond in the same language the user uses. "
    "If the query is in Hindi or another Indian language, respond in that language. "
    "Use Markdown bold (**text**) for section headers. Start your response with a "
    "clear status indicator: ✅ ALLOWED, 🚫 BANNED, or ⚠️ RESTRICTED."
)"""

new_prompt = """PHARMAI_SYSTEM_PROMPT = (
    "You are PharmaAI, an expert Indian pharmaceutical assistant specialized "
    "in drug safety. When given a medicine name, composition, or scanned text "
    "from a medicine package, provide a comprehensive analysis. Include the "
    "regulatory status in India (such as whether it is allowed, restricted, or banned by CDSCO/FSSAI), "
    "safety details (side effects, contraindications, drug interactions), "
    "and usage guidelines.\\n\\n"
    "**💰 Jan Aushadhi (Generic) Alternatives:**\\n"
    "For EVERY branded medicine mentioned, you MUST provide:\\n"
    "- The equivalent generic medicine available under Pradhan Mantri Bhartiya "
    "Janaushadhi Pariyojana (PMBJP)\\n"
    "- Approximate branded price vs. Jan Aushadhi generic price\\n"
    "- Percentage cost savings (e.g., '₹120 branded → ₹15 Jan Aushadhi = 87% savings')\\n"
    "- Nearest Jan Aushadhi Kendra availability tip\\n"
    "If no Jan Aushadhi equivalent exists, state that clearly.\\n\\n"
    "Be concise, accurate, and highly conversational. Keep the response fluid and natural. "
    "Respond in the same language the user uses. "
    "Use Markdown for formatting."
)"""

if old_prompt in content:
    content = content.replace(old_prompt, new_prompt)
    print("Replaced PHARMAI_SYSTEM_PROMPT")
else:
    print("Could not find PHARMAI_SYSTEM_PROMPT to replace")

# 2. Update search_tier2_aws
old_tier2 = """            # If structured result available, build a richer response
            if data.get('medicine_searched') and data.get('current_status'):
                badges = {'open': '✅ ALLOWED', 'banned': '🚫 BANNED', 'restricted': '⚠️ RESTRICTED'}
                status = data.get('current_status', 'unknown')
                badge = badges.get(status, 'ℹ️ ' + status.upper())
                
                # Extract structured details
                results = data.get('results', {})
                summary = ''
                if isinstance(results, dict):
                    summary = results.get('summary', '')
                elif isinstance(results, str):
                    summary = results
                
                answer_parts = [f"{badge}", f"**Medicine:** {data['medicine_searched']}", ""]
                if summary:
                    answer_parts.append(summary)
                elif answer:
                    answer_parts.append(answer)
                
                answer = '\\n\\n'.join(answer_parts)
            
            if answer:
                return {'source': 'aws-bedrock', 'answer': f"🔬 **AI Analysis (AWS Bedrock KB)**\\n\\n{answer}"}"""

new_tier2 = """            # Let Bedrock handle it naturally
            if data.get('medicine_searched'):
                results = data.get('results', {})
                summary = ''
                if isinstance(results, dict):
                    summary = results.get('summary', '')
                elif isinstance(results, str):
                    summary = results
                
                if summary:
                    answer = summary
            
            if answer:
                return {'source': 'aws-bedrock', 'answer': answer}"""

if old_tier2 in content:
    content = content.replace(old_tier2, new_tier2)
    print("Replaced search_tier2_aws logic")
else:
    print("Could not find search_tier2_aws logic to replace")

with open('/root/repo/pharmai_portal/frontend/app.py', 'w') as f:
    f.write(content)
