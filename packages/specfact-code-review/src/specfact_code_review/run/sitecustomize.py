"""Fail-closed startup for native Python CLI calls inside the target namespace."""

from __future__ import annotations

import os
import runpy
from pathlib import Path


if os.environ.get("SPECFACT_PROJECT_PYTHON") == "1":
    try:
        bootstrap = runpy.run_path(str(Path(__file__).with_name("target_bootstrap.py")))
        bootstrap["_configure_runtime"](bootstrap["python_execution_domain"]())
    except BaseException:
        # Python normally swallows sitecustomize failures and executes -c anyway.
        # Exit this isolated child before any requested project code can run.
        os._exit(78)
