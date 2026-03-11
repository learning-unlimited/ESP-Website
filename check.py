import sys
with open(r"c:\Users\User\Documents\Marcia\Programas\devsite\esp\esp\program\views.py", "rb") as f:
    code = f.read()

try:
    compile(code, "views.py", "exec")
except Exception as e:
    import traceback
    traceback.print_exc()
