import re

file_path = '/root/repo/pharmai_portal/v2_upgrade/docs/plan/tasks.md'
with open(file_path, 'r') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    # Phase 20 Testing
    if '- [ ] 61. E2E Search Flow' in line: line = line.replace('[ ]', '[x]')
    if '- [ ] 62. E2E OCR Flow' in line: line = line.replace('[ ]', '[x]')
    if '- [ ] 63. E2E Voice Flow' in line: line = line.replace('[ ]', '[x]')
    if '- [ ] 64. E2E Translation Flow' in line: line = line.replace('[ ]', '[x]')
    if '- [ ] 65. Document Management' in line: line = line.replace('[ ]', '[x]')
    if '- [ ] 66. Data Persistence' in line: line = line.replace('[ ]', '[x]')
    if '- [ ] 67. UI State' in line: line = line.replace('[ ]', '[x]')
    
    # Sub-tasks check off
    if '- [ ] 61.' in line or '- [ ] 62.' in line or '- [ ] 63.' in line or '- [ ] 64.' in line or '- [ ] 65.' in line or '- [ ] 66.' in line or '- [ ] 67.' in line:
        line = line.replace('[ ]', '[x]')

    # Phase 23 Hackathon
    if '- [ ] 77. Create demo script' in line:
        line = line.replace('[ ]', '[x]')
    if '- [ ] 77.1 Step-by-step demo flow' in line:
        line = line.replace('[ ]', '[x]')
        
    new_lines.append(line)

with open(file_path, 'w') as f:
    f.writelines(new_lines)
