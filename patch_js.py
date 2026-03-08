with open('/root/repo/pharmai_portal/frontend/js/chat.js', 'r') as f:
    content = f.read()

old_js = "    const sourceBadge = msg.source ? `<span class=\\\"source-badge\\\">${msg.source === 'kb' ? '📚 AWS KB' : '🤖 Sarvam AI'}</span>` : '';"
new_js = """    let badgeText = '🔬 AI Analysis';
    if (msg.source === 'aws-bedrock' || msg.source === 'kb') badgeText = '🔬 AWS Bedrock KB';
    else if (msg.source === 'sarvam') badgeText = '🤖 Sarvam AI';
    const sourceBadge = msg.source ? `<span class="source-badge">${badgeText}</span>` : '';"""

if old_js in content:
    content = content.replace(old_js, new_js)
    print("Replaced JS")
else:
    print("Could not find JS to replace")

with open('/root/repo/pharmai_portal/frontend/js/chat.js', 'w') as f:
    f.write(content)
