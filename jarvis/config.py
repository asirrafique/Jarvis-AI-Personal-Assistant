"""
Jarvis production configuration.

All environment-based configuration is centralized here.
Secrets are never printed or returned by public configuration helpers.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(
    dotenv_path=ENV_FILE
)


# ============================================================
# HELPERS
# ============================================================

def _get_env(
    name: str,
    default: str = "",
) -> str:

    value = os.getenv(
        name,
        default,
    )

    if not isinstance(
        value,
        str,
    ):
        return default

    return value.strip()


def _get_int(
    name: str,
    default: int,
) -> int:

    value = _get_env(
        name,
        str(default),
    )

    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


# ============================================================
# APPLICATION
# ============================================================

APP_ENV = _get_env(
    "JARVIS_ENV",
    "development",
).lower()


DEBUG = (
    _get_env(
        "JARVIS_DEBUG",
        "false",
    ).lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)


LOG_LEVEL = _get_env(
    "JARVIS_LOG_LEVEL",
    "INFO",
).upper()


# ============================================================
# OLLAMA
# ============================================================

OLLAMA_MODEL = _get_env(
    "OLLAMA_MODEL",
    "llama3.2",
)


OLLAMA_HOST = _get_env(
    "OLLAMA_HOST",
)


# ============================================================
# NEWS
# ============================================================

NEWS_API_KEY = _get_env(
    "NEWS_API_KEY",
)


# ============================================================
# HTTP
# ============================================================

HTTP_TIMEOUT = _get_int(
    "JARVIS_HTTP_TIMEOUT",
    10,
)

if HTTP_TIMEOUT <= 0:
    HTTP_TIMEOUT = 10


# ============================================================
# DATA DIRECTORIES
# ============================================================

DATA_DIR = Path(
    _get_env(
        "JARVIS_DATA_DIR",
        str(
            PROJECT_ROOT / "data"
        ),
    )
)


DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


CONTEXT_FILE = Path(
    _get_env(
        "JARVIS_CONTEXT_FILE",
        str(
            DATA_DIR
            / "jarvis_context.json"
        ),
    )
)


MEMORY_FILE = Path(
    _get_env(
        "JARVIS_MEMORY_FILE",
        str(
            DATA_DIR
            / "jarvis_memory.json"
        ),
    )
)


# ============================================================
# LOGGING
# ============================================================

LOG_DIR = Path(
    _get_env(
        "JARVIS_LOG_DIR",
        str(
            PROJECT_ROOT / "logs"
        ),
    )
)


LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


LOG_FILE = (
    LOG_DIR
    / "jarvis.log"
)


# ============================================================
# VALIDATION
# ============================================================

def validate_config(
    require_news_key=False,
):

    errors = []


    if not OLLAMA_MODEL:

        errors.append(
            "OLLAMA_MODEL is missing."
        )


    if HTTP_TIMEOUT <= 0:

        errors.append(
            "JARVIS_HTTP_TIMEOUT must be greater than zero."
        )


    if (
        require_news_key
        and not NEWS_API_KEY
    ):

        errors.append(
            "NEWS_API_KEY is missing."
        )


    return {
        "success": not errors,
        "environment": APP_ENV,
        "model": OLLAMA_MODEL,
        "news_api_configured": bool(
            NEWS_API_KEY
        ),
        "errors": errors,
    }


# ============================================================
# SAFE CONFIGURATION
# ============================================================

def get_public_config():

    return {
        "environment": APP_ENV,
        "debug": DEBUG,
        "log_level": LOG_LEVEL,
        "ollama_model": OLLAMA_MODEL,
        "ollama_host_configured": bool(
            OLLAMA_HOST
        ),
        "news_api_configured": bool(
            NEWS_API_KEY
        ),
        "http_timeout": HTTP_TIMEOUT,
        "context_file": str(
            CONTEXT_FILE
        ),
        "memory_file": str(
            MEMORY_FILE
        ),
        "log_file": str(
            LOG_FILE
        ),
    }


# ============================================================
# CLI TEST
# ============================================================

if __name__ == "__main__":

    import json

    print(
        json.dumps(
            get_public_config(),
            indent=2,
        )
    )

    print()

    print(
        json.dumps(
            validate_config(),
            indent=2,
        )
    )