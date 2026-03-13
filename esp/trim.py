import sys
for f in sys.argv[1:]:
    with open(f, 'r') as file:
        lines = file.readlines()
    with open(f, 'w') as file:
        file.writelines(l.rstrip() + '\n' for l in lines)
