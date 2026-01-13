"""
.. include:: ../README.md
"""
from .version import __version__
from .telegram_send import configure, delete, send


__all__ = ["configure", "delete", "send", "__version__"]
