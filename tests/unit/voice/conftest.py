"""
Conftest for voice unit tests.

Stubs chromadb before pytest collects modules so the pre-existing
chromadb/NumPy2 incompatibility doesn't block voice-layer tests.
The archon package itself is NOT stubbed — only chromadb is.
"""

import sys
import types
from pathlib import Path

# Ensure the installed archon package (via poetry) is used.
# The pyproject editable install handles this via the venv; no sys.path
# manipulation is needed when running via `poetry run pytest`.

# ── Stub chromadb so the chromadb→NumPy2 crash never fires ───────────────────

_CHROMADB_MODULES = [
    "chromadb",
    "chromadb.api",
    "chromadb.api.client",
    "chromadb.api.models",
    "chromadb.api.models.Collection",
    "chromadb.config",
    "chromadb.utils",
    "chromadb.utils.embedding_functions",
    "chromadb.api.types",
]

for _name in _CHROMADB_MODULES:
    if _name not in sys.modules:
        _stub = types.ModuleType(_name)
        # Provide a no-op Client class so any `import chromadb; chromadb.Client()` works
        _stub.Client = object  # type: ignore[attr-defined]
        sys.modules[_name] = _stub
