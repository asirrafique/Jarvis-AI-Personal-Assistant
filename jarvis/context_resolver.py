import json
import os
import re
from click import command
import ollama

from jarvis.config import OLLAMA_MODEL
from jarvis.context import get_context
from jarvis.logging_config import setup_logging


logger = setup_logging()

MODEL = OLLAMA_MODEL


# ============================================================
# CLEAN RESPONSE
# ============================================================

def clean_resolved_command(text):

    if not text:
        return ""

    text = str(text).strip()

    # Remove code fences.
    text = text.replace("```", "").strip()

    # Remove common prefixes.
    prefixes = [
        "Resolved:",
        "Answer:",
        "Command:",
        "Rewritten command:",
        "Output:",
    ]

    for prefix in prefixes:

        if text.lower().startswith(
            prefix.lower()
        ):

            text = text[
                len(prefix):
            ].strip()

            break

    # Remove surrounding quotes.
    if (
        len(text) >= 2
        and text[0] in "\"'"
        and text[-1] == text[0]
    ):

        text = text[
            1:-1
        ].strip()

    return text

# ============================================================
# EXPLICIT WEB COMMAND
# ============================================================

def is_explicit_web_command(command):
    """
    Detect commands whose web intent is already explicit.

    These commands must NOT be rewritten by the LLM context
    resolver because rewriting can accidentally remove part
    of the user's original request.

    Examples:

        Search the web for React tutorials
        Search for latest AI news
        Open https://github.com
        Search Python 3.13 and open https://python.org
    """

    if not command:
        return False

    text = command.lower().strip()

    search_patterns = [
        r"\bsearch\s+(?:the\s+)?web\b",
        r"\bsearch\s+for\b",
        r"\bsearch\b",
        r"\blook\s+up\b",
        r"\bfind\b",
    ]

    url_patterns = [
        r"\bopen\s+https?://",
        r"\bgo\s+to\s+https?://",
        r"\blaunch\s+https?://",
        r"https?://",
    ]

    has_search = any(
        re.search(
            pattern,
            text,
        )
        for pattern in search_patterns
    )

    has_url = any(
        re.search(
            pattern,
            text,
        )
        for pattern in url_patterns
    )

    return has_search or has_url


# ============================================================
# CHECK WHETHER COMMAND IS COMPLETE
# ============================================================

def is_complete_command(command):

    if not command:
        return False

    text = command.lower().strip()

    # --------------------------------------------------------
    # Complete weather command
    # --------------------------------------------------------

    has_weather = any(
        word in text
        for word in [
            "weather",
            "temperature",
            "forecast",
        ]
    )

    if has_weather:

        has_location = bool(
            re.search(
                r"\b(?:in|for)\s+[a-zA-Z][a-zA-Z .'-]*",
                text
            )
        )

        if has_location:
            return True

    # --------------------------------------------------------
    # Complete news command
    # --------------------------------------------------------

    if any(
        phrase in text
        for phrase in [
            "latest news",
            "latest headlines",
            "today's news",
            "todays news",
            "news",
        ]
    ):

        return True

    # --------------------------------------------------------
    # Complete time command
    # --------------------------------------------------------

    if any(
        phrase in text
        for phrase in [
            "what time",
            "current time",
            "time is it",
            "tell me the time",
        ]
    ):

        return True

    # --------------------------------------------------------
    # Complete date command
    # --------------------------------------------------------

    if any(
        phrase in text
        for phrase in [
            "today's date",
            "todays date",
            "what date",
            "current date",
            "what is the date",
            "what's the date",
        ]
    ):

        return True

    # --------------------------------------------------------
    # Complete web command
    # --------------------------------------------------------

    if is_explicit_web_command(
       command
    ):

      return True

    # --------------------------------------------------------
    # Complete music command
    # --------------------------------------------------------

    if text.startswith("play "):

        return True

    return False


# ============================================================
# DETERMINISTIC WEATHER CONTEXT
# ============================================================

def resolve_weather_context(
    command,
    context
):

    if not command:
        return None

    text = command.lower().strip()

    last_city = context.get(
        "last_city"
    )

    last_topic = context.get(
        "last_topic"
    )

    # --------------------------------------------------------
    # We can only resolve relative weather commands when the
    # previous topic was weather and a city is known.
    # --------------------------------------------------------

    if (
        last_topic != "weather"
        or not last_city
    ):

        return None

    # --------------------------------------------------------
    # DAY AFTER TOMORROW
    #
    # This MUST be checked before tomorrow.
    # --------------------------------------------------------

    if (
        "day after tomorrow"
        in text
    ):

        return (
            f"What is the weather in "
            f"{last_city} day after tomorrow?"
        )

    # --------------------------------------------------------
    # TOMORROW
    # --------------------------------------------------------

    if re.search(
        r"\btomorrow\b",
        text
    ):

        return (
            f"What is the weather in "
            f"{last_city} tomorrow?"
        )

    # --------------------------------------------------------
    # TODAY
    # --------------------------------------------------------

    if re.search(
        r"\btoday\b",
        text
    ):

        return (
            f"What is the weather in "
            f"{last_city} today?"
        )

    # --------------------------------------------------------
    # "What about it?"
    # --------------------------------------------------------

    if text in {
        "what about it?",
        "what about it",
        "how about it?",
        "how about it",
    }:

        return (
            f"What is the weather in "
            f"{last_city}?"
        )

    return None


# ============================================================
# DETERMINISTIC CONTEXT RESOLUTION
# ============================================================

def deterministic_resolution(
    command,
    context
):

    if not command:
        return command

    text = command.lower().strip()

    last_city = context.get(
        "last_city"
    )

    last_topic = context.get(
        "last_topic"
    )

    last_song = context.get(
        "last_song"
    )

    last_website = context.get(
        "last_website"
    )

    # ========================================================
    # WEATHER
    # ========================================================

    weather_result = resolve_weather_context(
        command,
        context
    )

    if weather_result:

        return weather_result

    # ========================================================
    # MUSIC
    # ========================================================

    if last_topic == "music" and last_song:

        if (
            "play it again" in text
            or "play it" in text
            or text in {
                "again",
                "play again",
            }
        ):

            return (
                f"Play {last_song} again."
            )

    # ========================================================
    # WEBSITE
    # ========================================================

    if last_website:

        if (
            text == "open it"
            or text == "open it again"
            or text == "go there"
            or text == "open that"
        ):

            return (
                f"Open {last_website} again."
            )

    # ========================================================
    # NEWS
    # ========================================================

    if last_topic == "news":

        if text in {
            "what about it?",
            "what about that?",
            "and the news?",
            "more?",
            "tell me more",
            "tell me more about that",
        }:

            return "Tell me more about the latest news."

    return None


# ============================================================
# RESOLVE COMMAND
# ============================================================

def resolve_command(command):

    if not command:
        return ""

    command = str(
        command
    ).strip()

    context = get_context()

    if not isinstance(
        context,
        dict
    ):

        context = {}

    # ========================================================
    # 1. DETERMINISTIC RESOLUTION
    # ========================================================
    #
    # IMPORTANT:
    # Handle simple relative commands ourselves.
    # Do NOT ask Llama to guess these.
    #

    deterministic = deterministic_resolution(
        command,
        context
    )

    if deterministic:

        print(
            "Deterministic context resolution:",
            deterministic
        )

        return deterministic

    # ========================================================
    # 2. ALREADY COMPLETE COMMAND
    # ========================================================

    if is_complete_command(
        command
    ):

        return command

    # ========================================================
    # 3. NO USEFUL CONTEXT
    # ========================================================

    if not any(
        context.values()
    ):

        return command

    # ========================================================
    # 4. LLM CONTEXT RESOLVER
    # ========================================================

    prompt = f"""
You are Jarvis's context resolver.

Previous context:

{json.dumps(
    context,
    indent=2,
    ensure_ascii=False
)}

New user command:

{command}

Rewrite the new command so it can be understood
without previous context.

IMPORTANT RULES:

1. Preserve the user's original meaning.

2. Use previous context only when necessary.

3. NEVER invent information.

4. NEVER change a city into a weekday,
   date, time, or unrelated word.

5. If the previous topic is weather and the
   user says:

   "What about tomorrow?"

   return:

   "What is the weather in <last_city> tomorrow?"

6. If the previous topic is weather and the
   user says:

   "And the day after tomorrow?"

   return:

   "What is the weather in <last_city> day after tomorrow?"

7. "day after tomorrow" means a weather-relative
   day. NEVER interpret it as a weekday.

8. If the previous topic is weather and the user
   says "today", preserve the previous city.

9. If the previous topic is music and the user
   says "play it again", use last_song.

10. If the previous website is YouTube and the
    user says "open it again", use last_website.

11. If the command is already complete,
    return it unchanged.

12. Return ONLY the rewritten command.

13. Do NOT return JSON.

14. Do NOT return tool names.

15. Do NOT return arguments.

16. Do NOT add explanations.

17. Do NOT add quotation marks.

Examples:

Previous context:
last_city = Delhi
last_topic = weather

User:
What about tomorrow?

Output:
What is the weather in Delhi tomorrow?

---

Previous context:
last_city = Delhi
last_topic = weather

User:
And the day after tomorrow?

Output:
What is the weather in Delhi day after tomorrow?

---

Previous context:
last_song = Believer
last_topic = music

User:
Play it again.

Output:
Play Believer again.

---

Previous context:
last_website = youtube

User:
Open it again.

Output:
Open YouTube again.
"""

    # ========================================================
    # ASK OLLAMA
    # ========================================================

    try:

        response = ollama.chat(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        resolved = (
            response
            .get("message", {})
            .get("content", "")
            .strip()
        )

        resolved = clean_resolved_command(
            resolved
        )

        if not resolved:

            return command

        # ====================================================
        # SAFETY CHECK
        #
        # If Llama produced something obviously broken for a
        # weather-relative command, reconstruct it ourselves.
        # ====================================================

        if (
            "day after tomorrow"
            in command.lower()
            and context.get("last_topic")
            == "weather"
            and context.get("last_city")
        ):

            return (
                f"What is the weather in "
                f"{context['last_city']} "
                f"day after tomorrow?"
            )

        if (
            re.search(
                r"\btomorrow\b",
                command.lower()
            )
            and "day after tomorrow"
            not in command.lower()
            and context.get("last_topic")
            == "weather"
            and context.get("last_city")
        ):

            return (
                f"What is the weather in "
                f"{context['last_city']} tomorrow?"
            )

        return resolved

    except Exception as e:

        print(
            "Context resolver error:",
            e
        )

        return command


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        resolve_command(
            "What is the weather in Delhi?"
        )
    )

    print(
        resolve_command(
            "What about tomorrow?"
        )
    )

    print(
        resolve_command(
            "And the day after tomorrow?"
        )
    )