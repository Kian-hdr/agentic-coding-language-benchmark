# Python baseline
Use {ORIGINAL_HOMEBREW}/bin/python3.14 (Python 3.14), standard library only.
Implement main.py accepting request filename as sys.argv[1], load via json.load,
print json.dumps(response). run.sh should execute Python with the script and
filename. Use unittest or assertions for local tests. Keep integer division
truncation toward zero explicit (Python // rounds toward negative infinity).

Command: {ORIGINAL_HOMEBREW}/bin/python3.14 main.py request.json
Validation: {ORIGINAL_HOMEBREW}/bin/python3.14 -m py_compile main.py
Python's standard library includes json, sys, re, heapq, collections, and unittest.
No pip installs. No required type checker installed in this baseline; annotations
are encouraged. This differs from TypeScript's static compiler and will be
reported as part of the actual available toolchain, not concealed.
