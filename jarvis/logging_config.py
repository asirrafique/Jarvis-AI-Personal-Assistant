"""
Centralized production logging for Jarvis.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from jarvis.config import (
    LOG_FILE,
    LOG_LEVEL,
)


_CONFIGURED = False


def setup_logging():

    global _CONFIGURED


    if _CONFIGURED:

        return logging.getLogger(
            "jarvis"
        )


    root = logging.getLogger()


    level = getattr(
        logging,
        LOG_LEVEL,
        logging.INFO,
    )


    root.setLevel(
        level
    )


    formatter = logging.Formatter(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


    # ========================================================
    # CONSOLE
    # ========================================================

    console = logging.StreamHandler()

    console.setLevel(
        level
    )

    console.setFormatter(
        formatter
    )


    # ========================================================
    # FILE
    # ========================================================

    file_handler = (
        RotatingFileHandler(
            LOG_FILE,
            maxBytes=2_000_000,
            backupCount=3,
            encoding="utf-8",
        )
    )


    file_handler.setLevel(
        level
    )

    file_handler.setFormatter(
        formatter
    )


    root.addHandler(
        console
    )

    root.addHandler(
        file_handler
    )


    _CONFIGURED = True


    return logging.getLogger(
        "jarvis"
    )


logger = setup_logging()