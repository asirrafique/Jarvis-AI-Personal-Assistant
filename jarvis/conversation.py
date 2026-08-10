from typing import Any, Dict, List, Optional


# ============================================================
# JARVIS CONVERSATION STATE
# ============================================================

MAX_HISTORY = 20


_conversation_state = {
    "last_command": None,
    "last_resolved_command": None,
    "last_topic": None,
    "last_city": None,
    "last_song": None,
    "last_website": None,
    "last_tool": None,
    "last_tool_arguments": None,
    "last_tool_result": None,
    "history": [],
}


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _normalize_text(value: Any) -> Optional[str]:
    """
    Safely convert a value to a stripped string.
    """
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def _limit_history() -> None:
    """
    Keep only the most recent conversation entries.
    """
    if len(_conversation_state["history"]) > MAX_HISTORY:
        _conversation_state["history"] = (
            _conversation_state["history"][-MAX_HISTORY:]
        )


def _detect_topic(
    command: Optional[str],
    tool_name: Optional[str] = None,
) -> Optional[str]:
    """
    Detect the main conversation topic.
    """

    # --------------------------------------------------------
    # Tool-based topic detection
    # --------------------------------------------------------

    if tool_name:

        tool_topics = {
            "get_weather": "weather",
            "get_news": "news",
            "get_time": "time",
            "get_date": "date",
            "play_music": "music",
            "open_website": "website",
        }

        if tool_name in tool_topics:
            return tool_topics[tool_name]

    # --------------------------------------------------------
    # Command-based topic detection
    # --------------------------------------------------------

    if not command:
        return None

    text = command.lower().strip()

    # Weather
    if any(
        word in text
        for word in [
            "weather",
            "temperature",
            "forecast",
        ]
    ):
        return "weather"

    # News
    if any(
        word in text
        for word in [
            "news",
            "headline",
            "headlines",
        ]
    ):
        return "news"

    # Time
    if any(
        phrase in text
        for phrase in [
            "what time",
            "current time",
            "time is it",
            "time?",
        ]
    ):
        return "time"

    # Date
    if any(
        phrase in text
        for phrase in [
            "today's date",
            "todays date",
            "current date",
            "what date",
            "what day",
            "date?",
        ]
    ):
        return "date"

    # Music
    if text.startswith("play "):
        return "music"

    # Website
    if text.startswith("open "):
        return "website"

    return None


def _extract_city(
    arguments: Any,
) -> Optional[str]:
    """
    Extract city from tool arguments.
    """

    if not isinstance(arguments, dict):
        return None

    city = arguments.get("city")

    if not city:
        return None

    return str(city).strip()


def _extract_song(
    arguments: Any,
) -> Optional[str]:
    """
    Extract song from tool arguments.
    """

    if not isinstance(arguments, dict):
        return None

    song = arguments.get("song")

    if not song:
        return None

    return str(song).strip()


def _extract_website(
    arguments: Any,
) -> Optional[str]:
    """
    Extract website from tool arguments.
    """

    if not isinstance(arguments, dict):
        return None

    website = arguments.get("name")

    if not website:
        return None

    return str(website).strip()


# ============================================================
# UPDATE CONVERSATION
# ============================================================

def update_conversation(
    command: Optional[str] = None,
    resolved_command: Optional[str] = None,
    response: Optional[str] = None,
    tool_name: Optional[str] = None,
    tool_arguments: Optional[Dict[str, Any]] = None,
    tool_result: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Main conversation-state update API.

    This is the API used by agent.py.
    """

    # --------------------------------------------------------
    # Compatibility argument names
    # --------------------------------------------------------

    if command is None:
        command = kwargs.get("original_command")

    if resolved_command is None:
        resolved_command = kwargs.get("resolved")

    if response is None:
        response = kwargs.get("final_response")

    if tool_name is None:
        tool_name = kwargs.get("tool")

    if tool_arguments is None:
        tool_arguments = kwargs.get("arguments")

    if tool_result is None and "result" in kwargs:
        tool_result = kwargs.get("result")

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    command = _normalize_text(command)
    resolved_command = _normalize_text(resolved_command)
    response = _normalize_text(response)
    tool_name = _normalize_text(tool_name)

    # --------------------------------------------------------
    # Basic state
    # --------------------------------------------------------

    if command:
        _conversation_state["last_command"] = command

    if resolved_command:
        _conversation_state[
            "last_resolved_command"
        ] = resolved_command

    if tool_name:
        _conversation_state["last_tool"] = tool_name

    if tool_arguments is not None:
        _conversation_state[
            "last_tool_arguments"
        ] = tool_arguments

    if tool_result is not None:
        _conversation_state[
            "last_tool_result"
        ] = tool_result

    # --------------------------------------------------------
    # Topic
    # --------------------------------------------------------

    topic = _detect_topic(
        resolved_command or command,
        tool_name,
    )

    if topic:
        _conversation_state["last_topic"] = topic

    # --------------------------------------------------------
    # Extract entities
    # --------------------------------------------------------

    city = _extract_city(tool_arguments)

    if city:
        _conversation_state["last_city"] = city

    song = _extract_song(tool_arguments)

    if song:
        _conversation_state["last_song"] = song

    website = _extract_website(tool_arguments)

    if website:
        _conversation_state["last_website"] = website

    # --------------------------------------------------------
    # User history
    # --------------------------------------------------------

    if command:

        _conversation_state["history"].append(
            {
                "role": "user",
                "command": command,
                "resolved_command": (
                    resolved_command or command
                ),
            }
        )

    # --------------------------------------------------------
    # Assistant history
    # --------------------------------------------------------

    if response:

        _conversation_state["history"].append(
            {
                "role": "assistant",
                "response": response,
            }
        )

    # --------------------------------------------------------
    # Limit history
    # --------------------------------------------------------

    _limit_history()

    return get_conversation_context()


# ============================================================
# ADD USER MESSAGE
# ============================================================

def add_user_message(
    command: Optional[str],
    resolved_command: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Add a user message.

    Used by test_conversation.py and other conversation
    components that manage messages separately.
    """

    command = _normalize_text(command)

    resolved_command = _normalize_text(
        resolved_command
    )

    if not command:
        return get_conversation_context()

    if resolved_command is None:
        resolved_command = command

    # --------------------------------------------------------
    # Store last command
    # --------------------------------------------------------

    _conversation_state[
        "last_command"
    ] = command

    _conversation_state[
        "last_resolved_command"
    ] = resolved_command

    # --------------------------------------------------------
    # Detect topic
    # --------------------------------------------------------

    topic = _detect_topic(
        resolved_command
    )

    if topic:
        _conversation_state[
            "last_topic"
        ] = topic

    # --------------------------------------------------------
    # Add history
    # --------------------------------------------------------

    _conversation_state["history"].append(
        {
            "role": "user",
            "command": command,
            "resolved_command": resolved_command,
        }
    )

    _limit_history()

    return get_conversation_context()


# ============================================================
# ADD ASSISTANT MESSAGE
# ============================================================

def add_assistant_message(
    response: Optional[str],
) -> Dict[str, Any]:
    """
    Add an assistant response to conversation history.
    """

    response = _normalize_text(response)

    if not response:
        return get_conversation_context()

    _conversation_state["history"].append(
        {
            "role": "assistant",
            "response": response,
        }
    )

    _limit_history()

    return get_conversation_context()


# ============================================================
# UPDATE CONTEXT
# ============================================================

def update_context(
    topic: Optional[str] = None,
    city: Optional[str] = None,
    song: Optional[str] = None,
    website: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Update individual short-term context fields.

    Used by test_conversation.py.
    """

    topic = _normalize_text(topic)
    city = _normalize_text(city)
    song = _normalize_text(song)
    website = _normalize_text(website)

    if topic:
        _conversation_state[
            "last_topic"
        ] = topic

    if city:
        _conversation_state[
            "last_city"
        ] = city

    if song:
        _conversation_state[
            "last_song"
        ] = song

    if website:
        _conversation_state[
            "last_website"
        ] = website

    return get_conversation_context()


# ============================================================
# UPDATE TOOL RESULT
# ============================================================

def update_tool_result(
    tool_name: Optional[str],
    arguments: Optional[Dict[str, Any]] = None,
    result: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Store the latest tool execution.
    """

    tool_name = _normalize_text(tool_name)

    # --------------------------------------------------------
    # Compatibility aliases
    # --------------------------------------------------------

    if tool_name is None:
        tool_name = _normalize_text(
            kwargs.get("tool")
        )

    if arguments is None:
        arguments = kwargs.get(
            "tool_arguments"
        )

    if result is None and "tool_result" in kwargs:
        result = kwargs.get(
            "tool_result"
        )

    # --------------------------------------------------------
    # Store tool information
    # --------------------------------------------------------

    if tool_name:
        _conversation_state[
            "last_tool"
        ] = tool_name

    if arguments is not None:

        _conversation_state[
            "last_tool_arguments"
        ] = arguments

        city = _extract_city(arguments)

        if city:
            _conversation_state[
                "last_city"
            ] = city

        song = _extract_song(arguments)

        if song:
            _conversation_state[
                "last_song"
            ] = song

        website = _extract_website(arguments)

        if website:
            _conversation_state[
                "last_website"
            ] = website

    if result is not None:
        _conversation_state[
            "last_tool_result"
        ] = result

    # --------------------------------------------------------
    # Detect topic from tool
    # --------------------------------------------------------

    topic = _detect_topic(
        None,
        tool_name,
    )

    if topic:
        _conversation_state[
            "last_topic"
        ] = topic

    return get_conversation_context()


# ============================================================
# GET CONVERSATION CONTEXT
# ============================================================

def get_conversation_context() -> Dict[str, Any]:
    """
    Return the current short-term conversation state.
    """

    return {
        "last_command": (
            _conversation_state[
                "last_command"
            ]
        ),
        "last_resolved_command": (
            _conversation_state[
                "last_resolved_command"
            ]
        ),
        "last_topic": (
            _conversation_state[
                "last_topic"
            ]
        ),
        "last_city": (
            _conversation_state[
                "last_city"
            ]
        ),
        "last_song": (
            _conversation_state[
                "last_song"
            ]
        ),
        "last_website": (
            _conversation_state[
                "last_website"
            ]
        ),
        "last_tool": (
            _conversation_state[
                "last_tool"
            ]
        ),
        "last_tool_arguments": (
            _conversation_state[
                "last_tool_arguments"
            ]
        ),
        "last_tool_result": (
            _conversation_state[
                "last_tool_result"
            ]
        ),
        "history": list(
            _conversation_state[
                "history"
            ]
        ),
    }


# ============================================================
# CONTEXT ALIASES
# ============================================================

def get_context() -> Dict[str, Any]:
    """
    Compatibility alias.
    """

    return get_conversation_context()


def get_context_dict() -> Dict[str, Any]:
    """
    Compatibility alias used by test_conversation.py.
    """

    return get_conversation_context()


# ============================================================
# RECENT HISTORY
# ============================================================

def get_recent_history(
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Return the most recent conversation entries.
    """

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 10

    if limit <= 0:
        return []

    return list(
        _conversation_state[
            "history"
        ][-limit:]
    )


# ============================================================
# LAST TOOL
# ============================================================

def get_last_tool() -> Optional[str]:
    """
    Return the most recently executed tool.
    """

    return _conversation_state[
        "last_tool"
    ]


# ============================================================
# LAST TOOL ARGUMENTS
# ============================================================

def get_last_tool_arguments() -> Optional[Dict[str, Any]]:
    """
    Return arguments from the most recent tool.
    """

    return _conversation_state[
        "last_tool_arguments"
    ]


# ============================================================
# LAST TOOL RESULT
# ============================================================

def get_last_tool_result() -> Any:
    """
    Return the most recent tool result.
    """

    return _conversation_state[
        "last_tool_result"
    ]


# ============================================================
# CLEAR CONVERSATION
# ============================================================

def clear_conversation() -> None:
    """
    Completely reset short-term conversation state.
    """

    _conversation_state[
        "last_command"
    ] = None

    _conversation_state[
        "last_resolved_command"
    ] = None

    _conversation_state[
        "last_topic"
    ] = None

    _conversation_state[
        "last_city"
    ] = None

    _conversation_state[
        "last_song"
    ] = None

    _conversation_state[
        "last_website"
    ] = None

    _conversation_state[
        "last_tool"
    ] = None

    _conversation_state[
        "last_tool_arguments"
    ] = None

    _conversation_state[
        "last_tool_result"
    ] = None

    _conversation_state[
        "history"
    ] = []


# ============================================================
# RESET ALIAS
# ============================================================

def reset_conversation() -> None:
    """
    Compatibility alias used by test_conversation.py.
    """

    clear_conversation()


# ============================================================
# EXPORT STATE
# ============================================================

def export_conversation() -> Dict[str, Any]:
    """
    Return a JSON-safe conversation-state dictionary.
    """

    return get_conversation_context()


# ============================================================
# DEBUG DISPLAY
# ============================================================

def print_conversation_state() -> None:
    """
    Print the current conversation state.
    """

    context = get_conversation_context()

    print()
    print("================================")
    print("JARVIS CONVERSATION STATE")
    print("================================")

    print(
        "Last command:",
        context["last_command"],
    )

    print(
        "Last resolved command:",
        context["last_resolved_command"],
    )

    print(
        "Last topic:",
        context["last_topic"],
    )

    print(
        "Last city:",
        context["last_city"],
    )

    print(
        "Last song:",
        context["last_song"],
    )

    print(
        "Last website:",
        context["last_website"],
    )

    print(
        "Last tool:",
        context["last_tool"],
    )

    print(
        "Last tool arguments:",
        context["last_tool_arguments"],
    )

    print(
        "History entries:",
        len(
            context["history"]
        ),
    )


# ============================================================
# DEBUG / SELF TEST
# ============================================================

if __name__ == "__main__":

    print(
        "================================"
    )

    print(
        "JARVIS CONVERSATION TEST"
    )

    print(
        "================================"
    )

    reset_conversation()

    # --------------------------------------------------------
    # FIRST USER MESSAGE
    # --------------------------------------------------------

    add_user_message(
        "What's the weather in Delhi?",
        "What's the weather in Delhi?",
    )

    update_context(
        topic="weather",
        city="Delhi",
    )

    update_tool_result(
        "get_weather",
        {
            "city": "Delhi",
            "days": 0,
        },
        "Today's weather in Delhi is expected "
        "to be a thunderstorm.",
    )

    add_assistant_message(
        "Today's weather in Delhi is expected "
        "to be a thunderstorm."
    )

    # --------------------------------------------------------
    # SECOND USER MESSAGE
    # --------------------------------------------------------

    add_user_message(
        "What about tomorrow?",
        "What's the weather in Delhi tomorrow?",
    )

    update_context(
        topic="weather",
        city="Delhi",
    )

    update_tool_result(
        "get_weather",
        {
            "city": "Delhi",
            "days": 1,
        },
        "Tomorrow's weather in Delhi is expected "
        "to be a thunderstorm.",
    )

    add_assistant_message(
        "Tomorrow's weather in Delhi is expected "
        "to be a thunderstorm."
    )

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    print_conversation_state()

    print()
    print("================================")
    print("CONTEXT DICTIONARY")
    print("================================")

    print(
        get_context_dict()
    )

    print()
    print("================================")
    print("RECENT HISTORY")
    print("================================")

    for item in get_recent_history(10):
        print(item)