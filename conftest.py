"""Test HOME isolation: pytest loads this before any test module.

The test process gets a fresh HOME. Setup proves that Path.home() follows it
and differs from the operator HOME (from the password database) before any
test code runs. On 2026-10-29 a test run under a runtime that ignored a
runtime HOME wrote an operator's ~/.pi; this check stops that class here.
"""

from __future__ import annotations

import atexit
import os
import pwd
import shutil
import tempfile
from pathlib import Path

_home = tempfile.mkdtemp(prefix="colorstack-test-home-")
atexit.register(shutil.rmtree, _home, ignore_errors=True)
os.environ["HOME"] = _home
_resolved = Path.home().resolve()
_operator = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
if _resolved != Path(_home).resolve() or _resolved == _operator:
    raise RuntimeError(
        f"HOME isolation failed: Path.home() is {_resolved}, HOME is {_home}, "
        f"the operator HOME is {_operator}. No test code ran."
    )
