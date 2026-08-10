"""
Jarvis Production Launcher

Starts Jarvis, validates the environment, checks Ollama,
and provides a clean interactive command-line interface.
"""

from __future__ import annotations

import sys
import time

import ollama

from jarvis.agent import run_agent
from jarvis.config import (
    OLLAMA_MODEL,
    validate_config,
)
from jarvis.logging_config import setup_logging


logger = setup_logging()


# ============================================================
# CONSTANTS
# ============================================================

APP_NAME = "JARVIS"
VERSION = "1.0.0"

EXIT_COMMANDS = {
    "exit",
    "quit",
    "bye",
    "shutdown",
}


# ============================================================
# DISPLAY
# ============================================================

def print_banner():

    print()
    print("=" * 60)
    print("                 JARVIS")
    print("=" * 60)
    print(f" Version: {VERSION}")
    print(" Personal AI Assistant")
    print("=" * 60)
    print()


def print_help():

    print()
    print("Available commands:")
    print()
    print("  help      Show this help message")
    print("  status    Show Jarvis system status")
    print("  exit      Exit Jarvis")
    print()
    print("You can also type normal commands, for example:")
    print()
    print("  What is the weather in Delhi?")
    print("  What about tomorrow?")
    print("  Open YouTube and play Believer")
    print("  Tell me the latest news")
    print()
    

# ============================================================
# OLLAMA CHECK
# ============================================================

def check_ollama():

    try:

        response = ollama.list()

        models = getattr(
            response,
            "models",
            [],
        )

        model_names = []

        for model in models:

            name = getattr(
                model,
                "model",
                "",
            )

            if name:

                model_names.append(
                    name
                )

        required_model = OLLAMA_MODEL

        available = any(
            name == required_model
            or name.startswith(
                required_model + ":"
            )
            for name in model_names
        )

        if not available:

            print(
                f"ERROR: Ollama model "
                f"'{required_model}' "
                f"is not installed."
            )

            print()
            print(
                "Available models:"
            )

            for name in model_names:

                print(
                    f"  - {name}"
                )

            print()

            return False

        return True

    except Exception as exc:

        logger.exception(
            "Ollama health check failed"
        )

        print(
            "ERROR: Could not connect "
            "to Ollama."
        )

        print(
            f"Details: {exc}"
        )

        print()
        print(
            "Make sure Ollama is running."
        )

        return False


# ============================================================
# HEALTH CHECK
# ============================================================

def health_check():

    print(
        "Checking Jarvis environment..."
    )

    # --------------------------------------------------------
    # Configuration
    # --------------------------------------------------------

    config = validate_config()

    if not config["success"]:

        print(
            "Configuration validation failed:"
        )

        for error in config["errors"]:

            print(
                f"  - {error}"
            )

        return False

    print(
        "  Configuration       OK"
    )

    # --------------------------------------------------------
    # Ollama
    # --------------------------------------------------------

    if not check_ollama():

        return False

    print(
        "  Ollama               OK"
    )

    print(
        f"  Model                {OLLAMA_MODEL}"
    )

    print()

    return True


# ============================================================
# STATUS
# ============================================================

def show_status():

    print()
    print("=" * 60)
    print("                    STATUS")
    print("=" * 60)

    config = validate_config()

    print(
        f"Environment : "
        f"{config['environment']}"
    )

    print(
        f"Model       : "
        f"{config['model']}"
    )

    print(
        f"News API    : "
        f"{'configured' if config['news_api_configured'] else 'not configured'}"
    )

    print(
        f"Config      : "
        f"{'OK' if config['success'] else 'ERROR'}"
    )

    ollama_ok = check_ollama()

    print(
        f"Ollama      : "
        f"{'OK' if ollama_ok else 'ERROR'}"
    )

    print("=" * 60)
    print()


# ============================================================
# COMMAND EXECUTION
# ============================================================

def process_command(command):

    command = command.strip()

    if not command:

        return

    command_lower = command.lower()

    # --------------------------------------------------------
    # HELP
    # --------------------------------------------------------

    if command_lower in {
        "help",
        "?",
    }:

        print_help()

        return

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if command_lower in {
        "status",
        "health",
        "health check",
    }:

        show_status()

        return

    # --------------------------------------------------------
    # EXIT
    # --------------------------------------------------------

    if command_lower in EXIT_COMMANDS:

        return "EXIT"

    # --------------------------------------------------------
    # AGENT
    # --------------------------------------------------------

    start_time = time.perf_counter()

    try:

        response = run_agent(
            command
        )

        elapsed = (
            time.perf_counter()
            - start_time
        )

        print()
        print(
            f"Jarvis: {response}"
        )

        logger.info(
            "Command completed in %.2fs",
            elapsed,
        )

        return response

    except KeyboardInterrupt:

        print()

        return "EXIT"

    except Exception as exc:

        logger.exception(
            "Command execution failed"
        )

        print()
        print(
            "Jarvis encountered an error "
            "while processing that request."
        )

        if config_debug_enabled():

            print(
                f"Details: {exc}"
            )

        return None


# ============================================================
# DEBUG
# ============================================================

def config_debug_enabled():

    try:

        from jarvis.config import DEBUG

        return DEBUG

    except Exception:

        return False


# ============================================================
# MAIN LOOP
# ============================================================

def main():

    print_banner()

    if not health_check():

        print(
            "Jarvis startup failed."
        )

        print(
            "Fix the issue above and "
            "start Jarvis again."
        )

        return 1

    print(
        "JARVIS ONLINE"
    )

    print(
        "Type 'help' for commands."
    )

    print(
        "Type 'exit' to quit."
    )

    print()

    while True:

        try:

            command = input(
                "You: "
            )

        except EOFError:

            print()

            break

        except KeyboardInterrupt:

            print()
            print(
                "\nShutting down Jarvis..."
            )

            break

        result = process_command(
            command
        )

        if result == "EXIT":

            print()
            print(
                "Shutting down Jarvis..."
            )

            break

    print(
        "Jarvis offline."
    )

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        sys.exit(
            main()
        )

    except KeyboardInterrupt:

        print(
            "\nJarvis offline."
        )

        sys.exit(0) 