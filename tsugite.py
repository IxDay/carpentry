#!/usr/bin/env python3
"""Launch Tsugite from any directory: `uv run tsugite.py`."""
import os
import runpy
import sys

sys.dont_write_bytecode = True  # upstream tracks setup/__pycache__ in git
setup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "setup")
os.chdir(setup_dir)  # the app loads textures, .ui and icons by relative path
sys.path.insert(0, setup_dir)
runpy.run_path("Tsugite_app.py", run_name="__main__")
