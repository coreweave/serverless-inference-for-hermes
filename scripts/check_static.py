# SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
# SPDX-License-Identifier: MIT
# SPDX-PackageName: serverless-inference-for-hermes

"""Syntax and source-distribution checks; does not import or launch Hermes."""
import ast
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for relative in ("__init__.py", "tests/test_provider.py", "scripts/check_static.py", "scripts/live_smoke.py"):
    ast.parse((root / relative).read_text(), filename=relative)
manifest = dict(
    line.split(": ", 1) for line in (root / "plugin.yaml").read_text().splitlines()
    if line.strip() and not line.lstrip().startswith("#")
)
assert manifest["kind"] == "model-provider"
assert manifest["name"] == "serverless-inference-for-hermes"
print("PASS: Python syntax and model-provider manifest. No Hermes runtime or network executed.")
