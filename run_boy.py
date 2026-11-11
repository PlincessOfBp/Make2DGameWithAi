import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

py313 = r"C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe"

# Python 3.13이 있으면 그거 사용, 없으면 py 런처 사용
if os.path.exists(py313):
    cmd = [py313, "main.py"]
else:
    cmd = ["py", "-3.13", "main.py"]

sys.exit(subprocess.call(cmd))
