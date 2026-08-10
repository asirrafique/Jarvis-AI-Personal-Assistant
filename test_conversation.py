from jarvis.conversation import (
    add_user_message,
    add_assistant_message,
    update_context,
    update_tool_result,
    get_context_dict,
    get_recent_history,
    print_conversation_state,
    reset_conversation
)


print(
    "\n================================"
)

print(
    "JARVIS CONVERSATION TEST"
)

print(
    "================================"
)


# ============================================================
# RESET
# ============================================================

reset_conversation()


# ============================================================
# FIRST USER MESSAGE
# ============================================================

add_user_message(
    "What's the weather in Delhi?",
    "What's the weather in Delhi?"
)

update_context(
    topic="weather",
    city="Delhi"
)

update_tool_result(
    "get_weather",
    {
        "city": "Delhi",
        "days": 0
    },
    "Today's weather in Delhi is expected to be a thunderstorm."
)

add_assistant_message(
    "Today's weather in Delhi is expected to be a thunderstorm."
)


# ============================================================
# SECOND USER MESSAGE
# ============================================================

add_user_message(
    "What about tomorrow?",
    "What's the weather in Delhi tomorrow?"
)

update_context(
    topic="weather",
    city="Delhi"
)

update_tool_result(
    "get_weather",
    {
        "city": "Delhi",
        "days": 1
    },
    "Tomorrow's weather in Delhi is expected to be a thunderstorm."
)

add_assistant_message(
    "Tomorrow's weather in Delhi is expected to be a thunderstorm."
)


# ============================================================
# DISPLAY STATE
# ============================================================

print_conversation_state()


# ============================================================
# DISPLAY CONTEXT
# ============================================================

print(
    "\n================================"
)

print(
    "CONTEXT DICTIONARY"
)

print(
    "================================"
)

print(
    get_context_dict()
)


# ============================================================
# DISPLAY HISTORY
# ============================================================

print(
    "\n================================"
)

print(
    "RECENT HISTORY"
)

print(
    "================================"
)

for item in get_recent_history(10):

    print(item)