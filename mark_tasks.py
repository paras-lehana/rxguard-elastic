import re

file_path = '/root/repo/pharmai_portal/v2_upgrade/docs/plan/tasks.md'
with open(file_path, 'r') as f:
    lines = f.readlines()

# Phases to mark complete
completed_phases = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 19, 21, 22]

current_phase = 0
in_target_phase = False

new_lines = []
for line in lines:
    m = re.match(r'^## Phase (\d+):', line)
    if m:
        current_phase = int(m.group(1))
        in_target_phase = current_phase in completed_phases
    
    if in_target_phase:
        # Replace '- [ ]' with '- [x]'
        if '- [ ]' in line:
            line = line.replace('- [ ]', '- [x]')
        # Also replace sub-tasks
        if '  - [ ]' in line:
            line = line.replace('  - [ ]', '  - [x]')
            
    new_lines.append(line)

with open(file_path, 'w') as f:
    f.writelines(new_lines)
print("Updated tasks.md")
