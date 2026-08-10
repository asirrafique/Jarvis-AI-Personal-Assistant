import json
import re

import ollama

from jarvis.tool_registry import TOOLS
from jarvis.context import update_context
from jarvis.context_resolver import resolve_command
from jarvis.memory_context import build_memory_context


MODEL = "llama3.2"


# ============================================================
# TOOL DESCRIPTIONS
# ============================================================

def get_tool_descriptions():

    descriptions = []

    for name, tool in TOOLS.items():

        descriptions.append({
            "name": name,
            "description": tool.get(
                "description",
                ""
            ),
            "arguments": tool.get(
                "arguments",
                {}
            )
        })

    return descriptions


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_response(text):

    if text is None:
        return ""

    text = str(text).strip()

    # Remove code fences
    text = text.replace(
        "```",
        ""
    ).strip()

    # Remove common prefixes
    prefixes = [
        "assistant:",
        "jarvis:",
        "answer:",
        "response:"
    ]

    for prefix in prefixes:

        if text.lower().startswith(prefix):

            text = text[
                len(prefix):
            ].strip()

            break

    # Remove surrounding quotes
    if (
        len(text) >= 2
        and text[0] in "\"'"
        and text[-1] == text[0]
    ):

        text = text[1:-1].strip()

    # Fix common spacing problems
    text = re.sub(
        r"\bisexpected\b",
        "is expected",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\ba(low)\b",
        "a low",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\bwithalow\b",
        "with a low",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\bhighof\b",
        "high of",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\blowof\b",
        "low of",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\bglobalLNG\b",
        "global LNG",
        text
    )

    text = re.sub(
        r"\bmentalhealth\b",
        "mental health",
        text
    )

    text = re.sub(
        r"\bsuspendingSIPs\b",
        "suspending SIPs",
        text
    )

    # Collapse excessive whitespace
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# COMPLETE COMMAND DETECTOR
# ============================================================

def is_complete_command(command):

    command_lower = command.lower().strip()

    # --------------------------------------------------------
    # WEATHER
    # --------------------------------------------------------

    weather_requested = any(
        word in command_lower
        for word in [
            "weather",
            "temperature",
            "forecast"
        ]
    )

    if weather_requested:

        if (
            " in " in command_lower
            or " for " in command_lower
            or " at " in command_lower
        ):

            return True

        common_cities = [
            "delhi",
            "new delhi",
            "kolkata",
            "calcutta",
            "mumbai",
            "bombay",
            "bangalore",
            "bengaluru",
            "hyderabad",
            "chennai",
            "pune",
            "noida",
            "gurgaon",
            "gurugram",
            "jaipur",
            "ahmedabad",
            "lucknow",
            "goa",
            "surat",
            "patna",
            "indore",
            "bhopal",
            "chandigarh"
        ]

        for city in common_cities:

            if re.search(
                rf"\b{re.escape(city)}\b",
                command_lower
            ):

                return True

    # --------------------------------------------------------
    # NEWS
    # --------------------------------------------------------

    if (
        "news" in command_lower
        and (
            "latest" in command_lower
            or "headlines" in command_lower
            or "tell me" in command_lower
            or "give me" in command_lower
        )
    ):

        return True

    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    if any(
        phrase in command_lower
        for phrase in [
            "what time",
            "current time",
            "time is it"
        ]
    ):

        return True

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    if any(
        phrase in command_lower
        for phrase in [
            "today's date",
            "current date",
            "what date",
            "what day is it"
        ]
    ):

        return True

    # --------------------------------------------------------
    # WEBSITE
    # --------------------------------------------------------

    if command_lower.startswith("open "):

        websites = [
            "google",
            "youtube",
            "facebook",
            "linkedin"
        ]

        if any(
            website in command_lower
            for website in websites
        ):

            return True

    # --------------------------------------------------------
    # MUSIC
    # --------------------------------------------------------

    if command_lower.startswith("play "):

        return True

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    if is_memory_question(command):

        return True

    return False


# ============================================================
# EXTRACT CITY
# ============================================================

def extract_city(command):

    text = command.strip()

    text = text.strip(
        " \t\r\n.,?!'\"`"
    )

    patterns = [

        # Weather in Delhi and tell me...
        r"\b(?:weather|temperature|forecast)"
        r"\s+(?:in|for)\s+"
        r"(.+?)"
        r"(?=\s+(?:and|but|then|please|tell|give)\b|[?.!,]|$)",

        # Weather in Delhi
        r"\b(?:weather|temperature|forecast)"
        r"\s+(?:in|for)\s+(.+)$",

        # Generic in Delhi
        r"\b(?:in|for)\s+"
        r"([A-Za-z][A-Za-z .'-]*?)"
        r"(?=\s+(?:and|but|then|please|tell|give)\b|[?.!,]|$)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if not match:
            continue

        city = match.group(1).strip()

        # Remove date phrases
        city = re.sub(
            r"\bday after tomorrow\b",
            "",
            city,
            flags=re.IGNORECASE
        )

        city = re.sub(
            r"\btomorrow\b",
            "",
            city,
            flags=re.IGNORECASE
        )

        city = re.sub(
            r"\btoday\b",
            "",
            city,
            flags=re.IGNORECASE
        )

        city = re.sub(
            r"\btonight\b",
            "",
            city,
            flags=re.IGNORECASE
        )

        # Remove command continuation
        city = re.split(
            r"\s+(?:and|but|then|please|tell|give)\b",
            city,
            maxsplit=1,
            flags=re.IGNORECASE
        )[0]

        city = city.strip(
            " \t\r\n.,?!'\"`"
        )

        if city:
            return city

    return None


# ============================================================
# EXTRACT DAYS
# ============================================================

def extract_days(command):

    command_lower = command.lower()

    if "day after tomorrow" in command_lower:
        return 2

    if "tomorrow" in command_lower:
        return 1

    if (
        "today" in command_lower
        or "tonight" in command_lower
    ):
        return 0

    return 0


# ============================================================
# MEMORY QUESTION DETECTOR
# ============================================================

def is_memory_question(command):

    command_lower = command.lower().strip()

    patterns = [

        "what do i prefer",

        "what is my preferred",

        "what's my preferred",

        "what is my favorite",

        "what's my favorite",

        "what is my favourite",

        "what's my favourite",

        "what do i like",

        "do you remember",

        "what do you remember",

        "what do you know about me",

        "what did i tell you",

        "what have i told you"
    ]

    for pattern in patterns:

        if pattern in command_lower:
            return True

    if (
        "programming language" in command_lower
        and (
            "prefer" in command_lower
            or "favorite" in command_lower
            or "favourite" in command_lower
            or "like" in command_lower
        )
    ):

        return True

    return False


# ============================================================
# NORMALIZE PLAN
# ============================================================

def normalize_plan(data):

    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    # Standard single tool
    if isinstance(
        data.get("tool"),
        str
    ):

        arguments = data.get(
            "arguments",
            {}
        )

        if not isinstance(
            arguments,
            dict
        ):

            arguments = {}

        return [
            {
                "tool": data["tool"],
                "arguments": arguments
            }
        ]

    # Tool list
    if isinstance(
        data.get("tool"),
        list
    ):

        return data["tool"]

    # tools list
    if isinstance(
        data.get("tools"),
        list
    ):

        return data["tools"]

    # plan list
    if isinstance(
        data.get("plan"),
        list
    ):

        return data["plan"]

    # result list
    if isinstance(
        data.get("result"),
        list
    ):

        return data["result"]

    return []


# ============================================================
# VALIDATE PLAN
# ============================================================

def validate_plan(plan):

    valid_plan = []

    if not isinstance(
        plan,
        list
    ):

        return valid_plan

    for step in plan:

        if not isinstance(
            step,
            dict
        ):

            continue

        tool_name = step.get(
            "tool"
        )

        if not isinstance(
            tool_name,
            str
        ):

            continue

        tool_name = tool_name.strip()

        if tool_name not in TOOLS:

            print(
                f"Agent skipped unknown tool: {tool_name}"
            )

            continue

        arguments = step.get(
            "arguments",
            {}
        )

        if not isinstance(
            arguments,
            dict
        ):

            arguments = {}

        valid_plan.append({
            "tool": tool_name,
            "arguments": arguments
        })

    return valid_plan


# ============================================================
# PLAN COMMAND
# ============================================================

def plan_command(command):

    command_lower = command.lower().strip()

    # ========================================================
    # MEMORY QUESTION
    # ========================================================

    if is_memory_question(command):

        print(
            "Memory question detected."
        )

        return []

    plan = []

    # ========================================================
    # WEATHER
    # ========================================================

    weather_words = [
        "weather",
        "temperature",
        "forecast"
    ]

    if any(
        word in command_lower
        for word in weather_words
    ):

        city = extract_city(
            command
        )

        days = extract_days(
            command
        )

        if city:

            plan.append({
                "tool": "get_weather",
                "arguments": {
                    "city": city,
                    "days": days
                }
            })

    # ========================================================
    # NEWS
    # ========================================================

    news_words = [
        "news",
        "headlines",
        "latest news",
        "today's news"
    ]

    if any(
        word in command_lower
        for word in news_words
    ):

        plan.append({
            "tool": "get_news",
            "arguments": {}
        })

    # ========================================================
    # TIME
    # ========================================================

    time_words = [
        "what time",
        "current time",
        "time is it"
    ]

    if any(
        word in command_lower
        for word in time_words
    ):

        plan.append({
            "tool": "get_time",
            "arguments": {}
        })

    # ========================================================
    # DATE
    # ========================================================

    date_words = [
        "today's date",
        "what date",
        "current date",
        "what day is it"
    ]

    if any(
        word in command_lower
        for word in date_words
    ):

        plan.append({
            "tool": "get_date",
            "arguments": {}
        })

    # ========================================================
    # WEBSITE
    # ========================================================

    websites = [
        "google",
        "youtube",
        "facebook",
        "linkedin"
    ]

    if command_lower.startswith(
        "open "
    ):

        for website in websites:

            if website in command_lower:

                plan.append({
                    "tool": "open_website",
                    "arguments": {
                        "name": website
                    }
                })

                break

    # ========================================================
    # MUSIC
    # ========================================================

    if command_lower.startswith(
        "play "
    ):

        song = command[5:].strip()

        if song:

            plan.append({
                "tool": "play_music",
                "arguments": {
                    "song": song
                }
            })

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    unique_plan = []

    seen = set()

    for step in plan:

        key = (
            step["tool"],
            json.dumps(
                step["arguments"],
                sort_keys=True
            )
        )

        if key not in seen:

            seen.add(key)

            unique_plan.append(
                step
            )

    # ========================================================
    # DETERMINISTIC PLAN
    # ========================================================

    if unique_plan:

        print(
            "Deterministic plan:",
            unique_plan
        )

        return unique_plan

    # ========================================================
    # LLAMA FALLBACK
    # ========================================================

    tools = get_tool_descriptions()

    prompt = f"""
You are the planning engine for Jarvis.

Available tools:

{json.dumps(
    tools,
    indent=2,
    ensure_ascii=False
)}

User request:

{command}

Return ONLY valid JSON.

Use this format:

{{
  "tools": [
    {{
      "tool": "tool_name",
      "arguments": {{}}
    }}
  ]
}}

If no tool is required:

{{
  "tools": []
}}

Rules:

1. Use only available tools.

2. Never invent tools.

3. Personal-memory questions require no tools.

4. For weather, city must contain ONLY the city name.

5. Never put tomorrow/today/day-after-tomorrow
   inside the city.

6. Weather days:

   today = 0
   tomorrow = 1
   day after tomorrow = 2

Example:

User:
What is the weather in Delhi tomorrow?

Return:

{{
  "tools": [
    {{
      "tool": "get_weather",
      "arguments": {{
        "city": "Delhi",
        "days": 1
      }}
    }}
  ]
}}

Example:

User:
What programming language do I prefer?

Return:

{{
  "tools": []
}}
"""

    try:

        response = ollama.chat(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            format="json"
        )

        raw = response[
            "message"
        ][
            "content"
        ].strip()

        print(
            "Agent raw response:",
            raw
        )

        data = json.loads(
            raw
        )

        plan = normalize_plan(
            data
        )

        return validate_plan(
            plan
        )

    except Exception as e:

        print(
            "Agent planning error:",
            e
        )

        return []


# ============================================================
# EXECUTE PLAN
# ============================================================

def execute_plan(plan):

    from jarvis.tool_registry import execute_tool

    results = []

    for step in plan:

        tool_name = step.get(
            "tool"
        )

        arguments = step.get(
            "arguments",
            {}
        )

        if not tool_name:
            continue

        print(
            f"Executing tool: {tool_name}"
        )

        print(
            f"Arguments: {arguments}"
        )

        try:

            result = execute_tool(
                tool_name,
                arguments
            )

        except Exception as e:

            result = {
                "success": False,
                "error": str(e)
            }

        results.append({
            "tool": tool_name,
            "arguments": arguments,
            "result": result
        })

    return results


# ============================================================
# ANSWER FROM MEMORY
# ============================================================

def answer_from_memory(
    command,
    memory_text
):

    if (
        not memory_text
        or memory_text.strip()
        == "No relevant long-term memories were found."
    ):

        return (
            "I don't remember that yet."
        )

    command_lower = command.lower()

    # --------------------------------------------------------
    # Programming language
    # --------------------------------------------------------

    if (
        "programming language" in command_lower
        and (
            "prefer" in command_lower
            or "favorite" in command_lower
            or "favourite" in command_lower
            or "like" in command_lower
        )
    ):

        if re.search(
            r"\bpython\b",
            memory_text,
            re.IGNORECASE
        ):

            return (
                "Your preferred programming "
                "language is Python."
            )

    # --------------------------------------------------------
    # Generic memory
    # --------------------------------------------------------

    lines = []

    for line in memory_text.splitlines():

        line = line.strip()

        if line.startswith("-"):

            line = line[1:].strip()

        if line:

            lines.append(
                line
            )

    if lines:

        return (
            "I remember: "
            + lines[0]
        )

    return (
        "I remember that you've "
        "mentioned this before."
    )


# ============================================================
# WEATHER RESPONSE
# ============================================================

def format_weather_response(
    result
):

    if not result:

        return (
            "I couldn't get the weather "
            "information right now."
        )

    if isinstance(
        result,
        dict
    ):

        if result.get(
            "success"
        ) is False:

            return result.get(
                "error",
                "I couldn't get the weather information."
            )

        message = result.get(
            "message"
        )

        if message:

            return str(
                message
            )

    # Weather tool currently returns
    # a natural-language string.
    if isinstance(
        result,
        str
    ):

        return clean_response(
            result
        )

    return (
        "I couldn't get the weather "
        "information right now."
    )


# ============================================================
# NEWS RESPONSE
# ============================================================

def format_news_response(
    result
):

    if not isinstance(
        result,
        dict
    ):

        return (
            "I couldn't get the latest news right now."
        )

    if result.get(
        "success"
    ) is False:

        return result.get(
            "error",
            "I couldn't get the latest news right now."
        )

    articles = result.get(
        "articles",
        []
    )

    if not articles:

        return (
            "I couldn't find any recent news."
        )

    lines = []

    for article in articles[:5]:

        if not isinstance(
            article,
            dict
        ):

            continue

        title = article.get(
            "title"
        )

        source = article.get(
            "source"
        )

        if not title:

            continue

        if source:

            lines.append(
                f"{title} — {source}"
            )

        else:

            lines.append(
                title
            )

    if not lines:

        return (
            "I couldn't find any usable "
            "news headlines."
        )

    return (
        "Here are the latest headlines:\n"
        + "\n".join(
            f"• {line}"
            for line in lines
        )
    )


# ============================================================
# TIME RESPONSE
# ============================================================

def format_time_response(
    result
):

    if isinstance(
        result,
        dict
    ):

        time = result.get(
            "time"
        )

        if time:

            return (
                f"It's currently {time}."
            )

    return str(
        result
    )


# ============================================================
# DATE RESPONSE
# ============================================================

def format_date_response(
    result
):

    if isinstance(
        result,
        dict
    ):

        date = result.get(
            "date"
        )

        if date:

            return (
                f"Today is {date}."
            )

    return str(
        result
    )


# ============================================================
# WEBSITE RESPONSE
# ============================================================

def format_website_response(
    result,
    arguments
):

    if isinstance(
        result,
        dict
    ):

        message = result.get(
            "message"
        )

        if message:

            return clean_response(
                str(message)
            )

    name = arguments.get(
        "name",
        "the website"
    )

    return (
        f"{name.capitalize()} is now open."
    )


# ============================================================
# MUSIC RESPONSE
# ============================================================

def format_music_response(
    result,
    arguments
):

    if isinstance(
        result,
        dict
    ):

        message = result.get(
            "message"
        )

        if message:

            return clean_response(
                str(message)
            )

    song = arguments.get(
        "song",
        "the song"
    )

    return (
        f"Playing {song}."
    )


# ============================================================
# DETERMINISTIC RESPONSE BUILDER
# ============================================================

def build_deterministic_response(
    results
):

    if not results:

        return None

    responses = []

    for item in results:

        tool = item.get(
            "tool"
        )

        result = item.get(
            "result"
        )

        arguments = item.get(
            "arguments",
            {}
        )

        # ----------------------------------------------------
        # WEATHER
        # ----------------------------------------------------

        if tool == "get_weather":

            responses.append(
                format_weather_response(
                    result
                )
            )

        # ----------------------------------------------------
        # NEWS
        # ----------------------------------------------------

        elif tool == "get_news":

            responses.append(
                format_news_response(
                    result
                )
            )

        # ----------------------------------------------------
        # TIME
        # ----------------------------------------------------

        elif tool == "get_time":

            responses.append(
                format_time_response(
                    result
                )
            )

        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        elif tool == "get_date":

            responses.append(
                format_date_response(
                    result
                )
            )

        # ----------------------------------------------------
        # WEBSITE
        # ----------------------------------------------------

        elif tool == "open_website":

            responses.append(
                format_website_response(
                    result,
                    arguments
                )
            )

        # ----------------------------------------------------
        # MUSIC
        # ----------------------------------------------------

        elif tool == "play_music":

            responses.append(
                format_music_response(
                    result,
                    arguments
                )
            )

        # ----------------------------------------------------
        # UNKNOWN / ERROR
        # ----------------------------------------------------

        elif isinstance(
            result,
            dict
        ):

            if result.get(
                "success"
            ) is False:

                error = result.get(
                    "error"
                )

                if error:

                    responses.append(
                        str(error)
                    )

        elif result:

            responses.append(
                str(result)
            )

    if not responses:

        return None

    # --------------------------------------------------------
    # One tool
    # --------------------------------------------------------

    if len(responses) == 1:

        return clean_response(
            responses[0]
        )

    # --------------------------------------------------------
    # Multiple tools
    # --------------------------------------------------------

    combined = "\n\n".join(
        response
        for response in responses
        if response
    )

    return clean_response(
        combined
    )


# ============================================================
# BUILD FALLBACK RESPONSE
# ============================================================

def build_fallback_response(
    results
):

    response = build_deterministic_response(
        results
    )

    if response:

        return response

    return (
        "The requested action was completed."
    )


# ============================================================
# GENERATE FINAL RESPONSE
# ============================================================

def generate_final_response(
    command,
    results,
    memory_text=""
):

    # ========================================================
    # IMPORTANT:
    #
    # If tools returned structured results,
    # DON'T ask Llama to rewrite them.
    #
    # This prevents:
    #
    # isexpected
    # alow
    # hallucinated facts
    # invented headlines
    # ========================================================

    if results:

        deterministic_response = (
            build_deterministic_response(
                results
            )
        )

        if deterministic_response:

            return deterministic_response

    # ========================================================
    # NO TOOL RESULT
    # ========================================================

    no_memory = (
        not memory_text
        or memory_text.strip()
        == "No relevant long-term memories were found."
    )

    if no_memory:

        return (
            "I couldn't find an action "
            "to perform for that request."
        )

    # ========================================================
    # LLM FALLBACK
    # ========================================================

    prompt = f"""
You are Jarvis, a concise personal AI assistant.

User request:

{command}

Relevant long-term memories:

{memory_text}

No tool result was available.

Answer the user naturally.

Rules:

1. Answer the user directly.

2. Use relevant memories.

3. Never invent facts.

4. Never claim Jarvis has personal preferences
   when the memory belongs to the user.

5. Never mention tools.

6. Never mention JSON.

7. Never mention the planner.

8. Never mention internal architecture.

9. Keep the answer concise.

10. Return ONLY the answer.
"""

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

        answer = response[
            "message"
        ][
            "content"
        ].strip()

        return clean_response(
            answer
        )

    except Exception as e:

        print(
            "Final response error:",
            e
        )

        return (
            "I wasn't able to generate "
            "a response right now."
        )


# ============================================================
# RUN AGENT
# ============================================================

def run_agent(command):

    print(
        "\n================================"
    )

    print(
        "Agent request:",
        command
    )

    original_command = command.strip()

    # ========================================================
    # STEP 1 — CONTEXT RESOLUTION
    # ========================================================

    if is_complete_command(
        original_command
    ):

        resolved_command = (
            original_command
        )

    else:

        try:

            resolved_command = (
                resolve_command(
                    original_command
                )
            )

        except Exception as e:

            print(
                "Context resolver error:",
                e
            )

            resolved_command = (
                original_command
            )

        resolved_command = clean_response(
            resolved_command
        )

    if (
        resolved_command.lower()
        != original_command.lower()
    ):

        print(
            "Context resolved:",
            resolved_command
        )

    # ========================================================
    # STEP 2 — LONG-TERM MEMORY
    # ========================================================

    try:

        memory_data = (
            build_memory_context(
                resolved_command
            )
        )

        if isinstance(
            memory_data,
            dict
        ):

            memory_text = (
                memory_data.get(
                    "formatted",
                    ""
                )
            )

        else:

            memory_text = str(
                memory_data
            )

    except Exception as e:

        print(
            "Memory context error:",
            e
        )

        memory_text = ""

    if not memory_text:

        memory_text = (
            "No relevant long-term "
            "memories were found."
        )

    print(
        "Relevant long-term memories:",
        memory_text
    )

    # ========================================================
    # STEP 3 — MEMORY QUESTION
    # ========================================================

    if is_memory_question(
        resolved_command
    ):

        print(
            "Memory question detected."
        )

        final_response = (
            answer_from_memory(
                resolved_command,
                memory_text
            )
        )

        final_response = clean_response(
            final_response
        )

        print(
            "Agent plan: []"
        )

        print(
            "Agent final response:",
            final_response
        )

        return final_response

    # ========================================================
    # STEP 4 — PLAN
    # ========================================================

    plan = plan_command(
        resolved_command
    )

    print(
        "Agent plan:",
        plan
    )

    # ========================================================
    # STEP 5 — NO TOOL
    # ========================================================

    if not plan:

        final_response = (
            generate_final_response(
                resolved_command,
                [],
                memory_text
            )
        )

        final_response = clean_response(
            final_response
        )

        print(
            "Agent final response:",
            final_response
        )

        return final_response

    # ========================================================
    # STEP 6 — EXECUTE TOOLS
    # ========================================================

    results = execute_plan(
        plan
    )

    print(
        "Agent results:",
        results
    )

    # ========================================================
    # STEP 7 — FINAL RESPONSE
    # ========================================================

    final_response = (
        generate_final_response(
            resolved_command,
            results,
            memory_text
        )
    )

    final_response = clean_response(
        final_response
    )

    print(
        "Agent final response:",
        final_response
    )

    # ========================================================
    # STEP 8 — UPDATE SHORT-TERM CONTEXT
    # ========================================================

    for item in results:

        try:

            update_context(
                command=resolved_command,
                tool=item.get(
                    "tool"
                ),
                arguments=item.get(
                    "arguments",
                    {}
                ),
                response=final_response
            )

        except Exception as e:

            print(
                "Context update error:",
                e
            )

    return final_response


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    commands = [

        "What time is it?",

        "Open YouTube",

        "Play Believer",

        "Tell me the latest news",

        "What's the weather in Delhi?",

        "What's the weather in Delhi tomorrow?",

        "What's the weather in Delhi day after tomorrow?",

        "Check the weather in Delhi and tell me the latest news",

        "What programming language do I prefer?"
    ]

    for command in commands:

        print(
            "\n================================"
        )

        print(
            "USER:",
            command
        )

        response = run_agent(
            command
        )

        print(
            "JARVIS:",
            response
        )