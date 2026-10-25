# Launcher sem console: roda o main.py via pythonw.
# Mantém o app sempre espelhado no main.py (sem duplicar código).
import sys
import os

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import runpy
runpy.run_path(os.path.join(BASE, "main.py"), run_name="__main__")
