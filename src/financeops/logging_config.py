from __future__ import annotations

import logging
import sys

from financeops.config import get_settings

_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    if settings.environment == "production":
        fmt = (
            '{"ts":"%(asctime)s","level":"%(levelname)s",'
            '"logger":"%(name)s","msg":"%(message)s"}'
        )
    else:
        fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)