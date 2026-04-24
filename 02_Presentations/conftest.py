"""Adds 02_Presentations/ to sys.path so tests can import style.* directly.

02_Presentations/ starts with a digit, so it cannot be a Python package.
Prepending its absolute path to sys.path lets pytest resolve imports like
`from style.palette import NAVY` without relying on package semantics.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
