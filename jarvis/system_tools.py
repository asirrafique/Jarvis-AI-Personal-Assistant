"""
Jarvis System Tools
===================

Safe Windows system-control tools for Jarvis.

The module deliberately uses allow-listed applications and validates
filesystem targets before opening them.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


def _failure(message: str) -> Dict[str, Any]:
    return {"success": False, "error": message}


def _success(message: str, **extra: Any) -> Dict[str, Any]:
    return {"success": True, "message": message, **extra}


def _windows_only() -> Optional[Dict[str, Any]]:
    if os.name != "nt":
        return _failure("System control tools are currently supported on Windows only.")
    return None


def _first_existing(paths: list[Path]) -> Optional[str]:
    for path in paths:
        try:
            if path.is_file():
                return str(path)
        except OSError:
            continue
    return None


def _which_any(names: list[str]) -> Optional[str]:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _app_command(name: str) -> Optional[list[str]]:
    """
    Resolve an allow-listed application to an executable command.
    No arbitrary shell commands are accepted.
    """
    home = Path.home()
    local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    program_files = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    program_files_x86 = Path(
        os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    )

    aliases = {
        "chrome": "chrome",
        "google chrome": "chrome",
        "edge": "edge",
        "microsoft edge": "edge",
        "firefox": "firefox",
        "vscode": "vscode",
        "vs code": "vscode",
        "visual studio code": "vscode",
        "notepad": "notepad",
        "calculator": "calculator",
        "calc": "calculator",
        "paint": "paint",
        "mspaint": "paint",
        "explorer": "explorer",
        "file explorer": "explorer",
        "terminal": "terminal",
        "windows terminal": "terminal",
        "powershell": "powershell",
        "command prompt": "cmd",
        "cmd": "cmd",
    }

    key = aliases.get(name.strip().lower())
    if not key:
        return None

    if key == "notepad":
        return ["notepad.exe"]

    if key == "calculator":
        return ["calc.exe"]

    if key == "paint":
        return ["mspaint.exe"]

    if key == "explorer":
        return ["explorer.exe"]

    if key == "powershell":
        return ["powershell.exe"]

    if key == "cmd":
        return ["cmd.exe"]

    if key == "terminal":
        found = _which_any(["wt.exe", "wt"])
        return [found] if found else ["wt.exe"]

    if key == "vscode":
        found = _which_any(["code.cmd", "code", "Code.exe"])
        if found:
            return [found]

        exe = _first_existing([
            local / "Programs" / "Microsoft VS Code" / "Code.exe",
            program_files / "Microsoft VS Code" / "Code.exe",
            program_files_x86 / "Microsoft VS Code" / "Code.exe",
        ])
        return [exe] if exe else None

    if key == "chrome":
        found = _which_any(["chrome.exe", "chrome"])
        if found:
            return [found]

        exe = _first_existing([
            local / "Google" / "Chrome" / "Application" / "chrome.exe",
            program_files / "Google" / "Chrome" / "Application" / "chrome.exe",
            program_files_x86 / "Google" / "Chrome" / "Application" / "chrome.exe",
        ])
        return [exe] if exe else None

    if key == "edge":
        found = _which_any(["msedge.exe", "msedge"])
        if found:
            return [found]

        exe = _first_existing([
            program_files / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            program_files_x86 / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        ])
        return [exe] if exe else None

    if key == "firefox":
        found = _which_any(["firefox.exe", "firefox"])
        if found:
            return [found]

        exe = _first_existing([
            program_files / "Mozilla Firefox" / "firefox.exe",
            program_files_x86 / "Mozilla Firefox" / "firefox.exe",
        ])
        return [exe] if exe else None

    return None


def open_app(name: str) -> Dict[str, Any]:
    """Open an allow-listed Windows application."""
    platform_error = _windows_only()
    if platform_error:
        return platform_error

    if not isinstance(name, str):
        return _failure("Application name must be a string.")

    name = name.strip().lower()
    if not name:
        return _failure("Application name is required.")

    command = _app_command(name)
    if not command:
        return _failure(f"Unsupported or unavailable application: {name}.")

    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
        return _success(f"Opened {name}.", application=name)
    except FileNotFoundError:
        return _failure(f"Application '{name}' is not installed or not available.")
    except Exception as exc:
        return _failure(f"Failed to open {name}: {exc}")


def _resolve_folder(path: str) -> Optional[Path]:
    aliases = {
        "home": Path.home(),
        "user home": Path.home(),
        "desktop": Path.home() / "Desktop",
        "downloads": Path.home() / "Downloads",
        "documents": Path.home() / "Documents",
        "pictures": Path.home() / "Pictures",
        "music": Path.home() / "Music",
        "videos": Path.home() / "Videos",
        "project": Path.cwd(),
        "project folder": Path.cwd(),
        "current folder": Path.cwd(),
    }

    key = path.strip().lower()
    if key in aliases:
        return aliases[key]

    expanded = os.path.expandvars(os.path.expanduser(path.strip()))
    return Path(expanded)


def open_folder(path: str) -> Dict[str, Any]:
    """Open an existing folder in Windows File Explorer."""
    platform_error = _windows_only()
    if platform_error:
        return platform_error

    if not isinstance(path, str):
        return _failure("Folder path must be a string.")

    path = path.strip()
    if not path:
        return _failure("Folder path is required.")

    folder = _resolve_folder(path)
    if folder is None:
        return _failure("Could not resolve the requested folder.")

    try:
        folder = folder.resolve()
    except OSError:
        return _failure(f"Invalid folder path: {path}")

    if not folder.exists():
        return _failure(f"Folder does not exist: {folder}")

    if not folder.is_dir():
        return _failure(f"Path is not a folder: {folder}")

    try:
        os.startfile(str(folder))
        return _success(f"Opened folder {folder}.", path=str(folder))
    except Exception as exc:
        return _failure(f"Failed to open folder {folder}: {exc}")


def open_file(path: str) -> Dict[str, Any]:
    """Open an existing file with its Windows default application."""
    platform_error = _windows_only()
    if platform_error:
        return platform_error

    if not isinstance(path, str):
        return _failure("File path must be a string.")

    path = path.strip()
    if not path:
        return _failure("File path is required.")

    expanded = os.path.expandvars(os.path.expanduser(path))
    file_path = Path(expanded)

    try:
        file_path = file_path.resolve()
    except OSError:
        return _failure(f"Invalid file path: {path}")

    if not file_path.exists():
        return _failure(f"File does not exist: {file_path}")

    if not file_path.is_file():
        return _failure(f"Path is not a file: {file_path}")

    try:
        os.startfile(str(file_path))
        return _success(f"Opened file {file_path}.", path=str(file_path))
    except Exception as exc:
        return _failure(f"Failed to open file {file_path}: {exc}")