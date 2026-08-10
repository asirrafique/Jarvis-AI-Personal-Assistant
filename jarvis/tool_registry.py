"""
Jarvis Tool Registry
====================

Central registry for all executable Jarvis tools.

Responsibilities:
- Register available tools
- Describe tools to the planner
- Validate tool arguments
- Execute tools safely
- Normalize tool results
- Prevent unknown tools / arguments from crashing Jarvis
"""

from __future__ import annotations

import inspect
import logging
import webbrowser
from typing import Any, Callable, Dict, Optional

from tools.news import get_news
from tools.weather import get_weather
from tools.web import search_web, open_url

from jarvis.system_tools import open_app, open_folder, open_file

import musicLibrary


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger("jarvis.tool_registry")


# ============================================================
# WEBSITE TOOL
# ============================================================

def open_website(name: str) -> Dict[str, Any]:
    """
    Open a supported website in the default browser.
    """

    if not isinstance(name, str):
        return {
            "success": False,
            "error": "Website name must be a string."
        }

    name = name.strip().lower()

    websites = {
        "google": "https://www.google.com",
        "youtube": "https://www.youtube.com",
        "facebook": "https://www.facebook.com",
        "linkedin": "https://www.linkedin.com",
        "instagram": "https://www.instagram.com",
        "github": "https://github.com",
        "gmail": "https://mail.google.com",
        "spotify": "https://open.spotify.com",
    }

    if not name:
        return {
            "success": False,
            "error": "Website name is required."
        }

    if name not in websites:
        return {
            "success": False,
            "error": f"Unsupported website: {name}."
        }

    try:
        opened = webbrowser.open(websites[name])

        if not opened:
            return {
                "success": False,
                "error": f"Could not open {name}."
            }

        return {
            "success": True,
            "website": name,
            "message": f"Opened {name}."
        }

    except Exception as exc:
        logger.exception(
            "Failed to open website '%s'",
            name
        )

        return {
            "success": False,
            "error": f"Failed to open {name}: {exc}"
        }


# ============================================================
# MUSIC TOOL
# ============================================================

def play_music(song: str) -> Dict[str, Any]:
    """
    Play a song from the configured music library.
    """

    if not isinstance(song, str):
        return {
            "success": False,
            "error": "Song name must be a string."
        }

    song = song.strip()

    if not song:
        return {
            "success": False,
            "error": "Song name is required."
        }

    # Normalize only for library lookup.
    normalized_song = song.lower()

    try:
        music = getattr(
            musicLibrary,
            "music",
            {}
        )

        if not isinstance(music, dict):
            return {
                "success": False,
                "error": "Music library is unavailable."
            }

        if normalized_song not in music:
            return {
                "success": False,
                "error": f"Song '{song}' not found in the music library."
            }

        url = music[normalized_song]

        if not isinstance(url, str) or not url.strip():
            return {
                "success": False,
                "error": f"No playable URL configured for '{song}'."
            }

        opened = webbrowser.open(url)

        if not opened:
            return {
                "success": False,
                "error": f"Could not open the music URL for '{song}'."
            }

        return {
            "success": True,
            "song": song,
            "message": f"Playing {song}."
        }

    except Exception as exc:
        logger.exception(
            "Failed to play music '%s'",
            song
        )

        return {
            "success": False,
            "error": f"Failed to play '{song}': {exc}"
        }


# ============================================================
# TIME TOOL
# ============================================================

def get_time() -> Dict[str, Any]:
    """
    Return the current local time.
    """

    from datetime import datetime

    try:
        current_time = datetime.now().strftime(
            "%I:%M %p"
        )

        return {
            "success": True,
            "time": current_time
        }

    except Exception as exc:
        logger.exception(
            "Failed to get current time"
        )

        return {
            "success": False,
            "error": f"Could not get current time: {exc}"
        }


# ============================================================
# DATE TOOL
# ============================================================

def get_date() -> Dict[str, Any]:
    """
    Return today's local date.
    """

    from datetime import datetime

    try:
        current_date = datetime.now().strftime(
            "%A, %d %B %Y"
        )

        return {
            "success": True,
            "date": current_date
        }

    except Exception as exc:
        logger.exception(
            "Failed to get current date"
        )

        return {
            "success": False,
            "error": f"Could not get current date: {exc}"
        }


# ============================================================
# TOOL REGISTRY
# ============================================================

TOOLS: Dict[str, Dict[str, Any]] = {

    # --------------------------------------------------------
    # WEBSITE
    # --------------------------------------------------------

    "open_website": {
        "function": open_website,
        "description": (
            "Open a supported website such as "
            "Google, YouTube, Facebook, LinkedIn, "
            "Instagram, GitHub, Gmail or Spotify."
        ),
        "arguments": {
            "name": {
                "type": "string",
                "required": True,
                "description": "Website name."
            }
        }
    },

    # --------------------------------------------------------
    # MUSIC
    # --------------------------------------------------------

    "play_music": {
        "function": play_music,
        "description": (
            "Play a song from the configured music library."
        ),
        "arguments": {
            "song": {
                "type": "string",
                "required": True,
                "description": "Song name."
            }
        }
    },

    # --------------------------------------------------------
    # SYSTEM / APP CONTROL
    # --------------------------------------------------------

    "open_app": {
        "function": open_app,
        "description": (
            "Open an allow-listed Windows application such as "
            "Chrome, Edge, Firefox, VS Code, Notepad, Calculator, "
            "Paint, File Explorer, Terminal, PowerShell or Command Prompt."
        ),
        "arguments": {
            "name": {
                "type": "string",
                "required": True,
                "description": "Application name."
            }
        }
    },

    "open_folder": {
        "function": open_folder,
        "description": (
            "Open a local folder. Supports aliases such as Desktop, "
            "Downloads, Documents, Pictures, Music, Videos, Home and Project."
        ),
        "arguments": {
            "path": {
                "type": "string",
                "required": True,
                "description": "Folder path or supported folder alias."
            }
        }
    },

    "open_file": {
        "function": open_file,
        "description": (
            "Open an existing local file with its default Windows application."
        ),
        "arguments": {
            "path": {
                "type": "string",
                "required": True,
                "description": "Existing file path."
            }
        }
    },

    # --------------------------------------------------------
    # NEWS
    # --------------------------------------------------------

    "get_news": {
        "function": get_news,
        "description": (
            "Fetch the latest news headlines."
        ),
        "arguments": {}
    },

    # --------------------------------------------------------
    # WEATHER
    # --------------------------------------------------------

    "get_weather": {
        "function": get_weather,
        "description": (
            "Get weather information for a city. "
            "days=0 means today, days=1 means tomorrow, "
            "and days=2 means the day after tomorrow."
        ),
        "arguments": {
            "city": {
                "type": "string",
                "required": True,
                "description": "City name."
            },
            "days": {
                "type": "integer",
                "required": False,
                "description": (
                    "Forecast offset: "
                    "0=today, 1=tomorrow, "
                    "2=day after tomorrow."
                )
            }
        }
    },

    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    "get_time": {
        "function": get_time,
        "description": (
            "Get the current local time."
        ),
        "arguments": {}
    },

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

        "get_date": {
        "function": get_date,
        "description": (
            "Get today's date."
        ),
        "arguments": {}
    },

    "search_web": {
        "function": search_web,
        "description": (
            "Search the public web for information and return "
            "relevant search results with titles, URLs and snippets."
        ),
        "arguments": {
            "query": {
                "type": "string",
                "required": True,
                "description": "The web search query."
            },
            "max_results": {
                "type": "integer",
                "required": False,
                "description": "Maximum number of results, from 1 to 10."
            }
        }
    },

    "open_url": {
        "function": open_url,
        "description": (
            "Open a specific HTTP or HTTPS URL in the default browser."
        ),
        "arguments": {
            "url": {
                "type": "string",
                "required": True,
                "description": "The complete HTTP or HTTPS URL."
            }
        }
    }
}




# ============================================================
# TOOL DESCRIPTION GENERATOR
# ============================================================

def get_tool_descriptions() -> list:
    """
    Return planner-friendly descriptions of all tools.

    This function is intentionally exposed because agent.py
    uses it when constructing the LLM planning prompt.
    """

    descriptions = []

    for name, definition in TOOLS.items():

        descriptions.append({
            "tool": name,
            "description": definition.get(
                "description",
                ""
            ),
            "arguments": definition.get(
                "arguments",
                {}
            )
        })

    return descriptions


# ============================================================
# TOOL NAME HELPERS
# ============================================================

def get_available_tools() -> list:
    """
    Return a list of registered tool names.
    """

    return list(TOOLS.keys())


def tool_exists(tool_name: str) -> bool:
    """
    Check whether a tool exists.
    """

    if not isinstance(tool_name, str):
        return False

    return tool_name.strip() in TOOLS


# ============================================================
# ARGUMENT VALIDATION
# ============================================================

def _validate_arguments(
    tool_name: str,
    arguments: Dict[str, Any]
) -> Optional[str]:
    """
    Validate arguments against the registry definition.

    Returns:
        None when valid.
        Error message when invalid.
    """

    tool = TOOLS.get(tool_name)

    if tool is None:
        return f"Tool '{tool_name}' does not exist."

    if not isinstance(arguments, dict):
        return (
            f"Arguments for '{tool_name}' "
            "must be a dictionary."
        )

    expected = tool.get(
        "arguments",
        {}
    )

    # --------------------------------------------------------
    # Unknown arguments
    # --------------------------------------------------------

    unknown = set(arguments.keys()) - set(
        expected.keys()
    )

    if unknown:

        unknown_text = ", ".join(
            sorted(str(item) for item in unknown)
        )

        return (
            f"Unknown argument(s) for "
            f"'{tool_name}': {unknown_text}"
        )

    # --------------------------------------------------------
    # Required arguments
    # --------------------------------------------------------

    for argument_name, definition in expected.items():

        if not isinstance(
            definition,
            dict
        ):
            continue

        required = definition.get(
            "required",
            False
        )

        if (
            required
            and argument_name not in arguments
        ):

            return (
                f"Missing required argument "
                f"'{argument_name}' for '{tool_name}'."
            )

    # --------------------------------------------------------
    # Basic type validation
    # --------------------------------------------------------

    for argument_name, value in arguments.items():

        definition = expected.get(
            argument_name,
            {}
        )

        expected_type = definition.get(
            "type"
        )

        if expected_type == "string":

            if not isinstance(
                value,
                str
            ):

                return (
                    f"Argument '{argument_name}' "
                    f"for '{tool_name}' must be a string."
                )

            if not value.strip():

                return (
                    f"Argument '{argument_name}' "
                    f"for '{tool_name}' cannot be empty."
                )

        elif expected_type == "integer":

            # bool is technically an int in Python,
            # but should not be accepted here.
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
            ):

                return (
                    f"Argument '{argument_name}' "
                    f"for '{tool_name}' must be an integer."
                )

    # --------------------------------------------------------
    # Weather-specific validation
    # --------------------------------------------------------

    if tool_name == "get_weather":

        days = arguments.get(
            "days",
            0
        )

        if (
            isinstance(days, bool)
            or not isinstance(days, int)
        ):

            return (
                "Weather 'days' must be an integer."
            )

        if days < 0:

            return (
                "Weather 'days' cannot be negative."
            )

        if days > 7:

            return (
                "Weather forecast is limited "
                "to 7 days ahead."
            )

    return None


# ============================================================
# RESULT NORMALIZATION
# ============================================================

def _normalize_result(
    tool_name: str,
    result: Any
) -> Dict[str, Any]:
    """
    Normalize every tool response into a dictionary.
    """

    if result is None:

        return {
            "success": True,
            "message": (
                f"{tool_name} completed successfully."
            )
        }

    if isinstance(result, dict):

        # Always guarantee success field.
        if "success" not in result:

            result = {
                "success": True,
                **result
            }

        return result

    return {
        "success": True,
        "result": result
    }


# ============================================================
# EXECUTE TOOL
# ============================================================

def execute_tool(
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute a registered Jarvis tool safely.

    Never raises a normal tool execution exception
    back into the agent pipeline.

    Instead returns:

        {
            "success": True/False,
            ...
        }
    """

    # --------------------------------------------------------
    # Validate tool name
    # --------------------------------------------------------

    if not isinstance(
        tool_name,
        str
    ):

        return {
            "success": False,
            "error": "Tool name must be a string."
        }

    tool_name = tool_name.strip()

    if not tool_name:

        return {
            "success": False,
            "error": "Tool name is required."
        }

    # --------------------------------------------------------
    # Find tool
    # --------------------------------------------------------

    tool = TOOLS.get(
        tool_name
    )

    if tool is None:

        return {
            "success": False,
            "error": (
                f"Tool '{tool_name}' "
                "does not exist."
            )
        }

    # --------------------------------------------------------
    # Normalize arguments
    # --------------------------------------------------------

    if arguments is None:

        arguments = {}

    if not isinstance(
        arguments,
        dict
    ):

        return {
            "success": False,
            "error": (
                f"Arguments for '{tool_name}' "
                "must be a dictionary."
            )
        }

    # --------------------------------------------------------
    # Validate arguments
    # --------------------------------------------------------

    validation_error = _validate_arguments(
        tool_name,
        arguments
    )

    if validation_error:

        logger.warning(
            "Tool validation failed: %s",
            validation_error
        )

        return {
            "success": False,
            "error": validation_error
        }

    # --------------------------------------------------------
    # Execute
    # --------------------------------------------------------

    function: Callable = tool["function"]

    try:

        logger.info(
            "Executing tool '%s' with arguments %s",
            tool_name,
            arguments
        )

        result = function(
            **arguments
        )

        normalized = _normalize_result(
            tool_name,
            result
        )

        logger.info(
            "Tool '%s' completed: success=%s",
            tool_name,
            normalized.get("success")
        )

        return normalized

    except TypeError as exc:

        # Usually indicates a function/argument mismatch.
        logger.exception(
            "Argument error while executing '%s'",
            tool_name
        )

        return {
            "success": False,
            "error": (
                f"Invalid arguments for "
                f"'{tool_name}': {exc}"
            )
        }

    except Exception as exc:

        logger.exception(
            "Tool '%s' failed",
            tool_name
        )

        return {
            "success": False,
            "error": (
                f"Tool '{tool_name}' failed: "
                f"{exc}"
            )
        }


# ============================================================
# TOOL REGISTRY HEALTH CHECK
# ============================================================

def validate_registry() -> Dict[str, Any]:
    """
    Validate the registry itself.

    Useful during startup/testing.
    """

    errors = []

    for name, definition in TOOLS.items():

        if not isinstance(
            name,
            str
        ) or not name.strip():

            errors.append(
                "A tool has an invalid name."
            )

        function = definition.get(
            "function"
        )

        if not callable(function):

            errors.append(
                f"Tool '{name}' has no callable function."
            )

        if not isinstance(
            definition.get("description"),
            str
        ):

            errors.append(
                f"Tool '{name}' has no valid description."
            )

        if not isinstance(
            definition.get("arguments"),
            dict
        ):

            errors.append(
                f"Tool '{name}' has invalid arguments metadata."
            )

    if errors:

        return {
            "success": False,
            "errors": errors
        }

    return {
        "success": True,
        "tool_count": len(TOOLS),
        "tools": get_available_tools()
    }


# ============================================================
# OPTIONAL STARTUP CHECK
# ============================================================

if __name__ == "__main__":

    print("=" * 50)
    print("JARVIS TOOL REGISTRY")
    print("=" * 50)

    health = validate_registry()

    print(
        "Registry status:",
        health
    )

    print()
    print("Available tools:")

    for tool in get_tool_descriptions():

        print(
            f"- {tool['tool']}: "
            f"{tool['description']}"
        )