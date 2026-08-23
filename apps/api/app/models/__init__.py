"""Model package.

All model modules under this package are auto-imported for Alembic metadata discovery.
"""

from __future__ import annotations

import importlib
import pkgutil

from app.db.base import Base


def register_models() -> None:
    """Import all concrete model modules so metadata is fully populated."""
    package = importlib.import_module(__name__)
    prefix = f"{package.__name__}."

    for module_info in pkgutil.walk_packages(package.__path__, prefix):
        if module_info.ispkg:
            continue
        if module_info.name == __name__:
            continue
        importlib.import_module(module_info.name)


register_models()

__all__ = ["Base", "register_models"]
