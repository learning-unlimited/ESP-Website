import os, re
root_dir = 'd:/Placement/GSSOC/ESP-Website/esp'
model_field_pattern = re.compile(r'(models\.(?:CharField|TextField|EmailField|SlugField)\b\s*\([^)]*?)\bnull=True\b([^)]*\))')

changed_files = 0
for dirpath, dirs, files in os.walk(root_dir):
    if 'migrations' in dirpath:
        continue
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(dirpath, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            original_content = content
            
            def replace_in_field(match):
                prefix = match.group(1)
                suffix = match.group(2)
                return prefix + 'default=""' + suffix
                
            prev_content = None
            while prev_content != content:
                prev_content = content
                content = model_field_pattern.sub(replace_in_field, content)
            
            if content != original_content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                changed_files += 1
                print(f'Modified: {path}')

print(f'Total files modified: {changed_files}')
