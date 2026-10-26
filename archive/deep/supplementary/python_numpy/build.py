"""Build optimized bytecode with the pinned interpreter; no dependencies."""
from pathlib import Path
import py_compile

root = Path(__file__).resolve().parent
py_compile.compile(str(root / "main.py"), cfile=str(root / "worker.pyc"),
                   doraise=True, optimize=2)
print("Built optimized Python bytecode: worker.pyc")
