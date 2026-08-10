import json
import re

import ollama

from jarvis.tool_registry import TOOLS, execute_tool

from jarvis.context import (
    update_context,
)

from jarvis.context_resolver import (
    resolve_command,
)

try:
    from jarvis.memory_context import (
        build_memory_context,
    )
except ImportError:
    build_memory_context = None


# ============================================================
# CONFIGURATION
# ============================================================

MODEL = "llama3.2"

NO_MEMORY_TEXT = (
    "No relevant long-term memories were found."
)


# ============================================================
# TOOL DESCRIPTIONS
# ============================================================

def get_tool_descriptions():
    """
    Build clean tool descriptions for the LLM planner.
    """

    descriptions = []

    for name, tool in TOOLS.items():

        descriptions.append({
            "tool": name,
            "description": tool.get(
                "description",
                ""
            ),
            "arguments": tool.get(
                "arguments",
                {}
            ),
        })

    return descriptions


# ============================================================
# PLAN NORMALIZATION
# ============================================================

def normalize_plan(data):
    """
    Convert possible LLM planner outputs into:

    [
        {
            "tool": "...",
            "arguments": {...}
        }
    ]
    """

    # --------------------------------------------------------
    # Already a list
    # --------------------------------------------------------

    if isinstance(data, list):
        return data

    # --------------------------------------------------------
    # Dictionary
    # --------------------------------------------------------

    if isinstance(data, dict):

        # --------------------------------------------
        # {"tool": "...", "arguments": {...}}
        # --------------------------------------------

        tool = data.get(
            "tool"
        )

        arguments = data.get(
            "arguments",
            {}
        )

        if isinstance(
            tool,
            str
        ):

            if not isinstance(
                arguments,
                dict
            ):
                arguments = {}

            return [
                {
                    "tool": tool,
                    "arguments": arguments,
                }
            ]

        # --------------------------------------------
        # {"name": "...", "arguments": {...}}
        # --------------------------------------------

        name = data.get(
            "name"
        )

        if isinstance(
            name,
            str
        ):

            if not isinstance(
                arguments,
                dict
            ):
                arguments = {}

            return [
                {
                    "tool": name,
                    "arguments": arguments,
                }
            ]

        # --------------------------------------------
        # {"tools": [...]}
        # --------------------------------------------

        tools = data.get(
            "tools"
        )

        if isinstance(
            tools,
            list
        ):
            return tools

        # --------------------------------------------
        # {"plan": [...]}
        # --------------------------------------------

        plan = data.get(
            "plan"
        )

        if isinstance(
            plan,
            list
        ):
            return plan

    return []


# ============================================================
# CLEAN CITY
# ============================================================

def clean_city(city):

    if not city:
        return None

    city = str(
        city
    ).strip()

    # --------------------------------------------------------
    # Remove time expressions
    # --------------------------------------------------------

    time_patterns = [
        r"\bday\s+after\s+tomorrow\b",
        r"\btomorrow\b",
        r"\btoday\b",
        r"\btonight\b",
        r"\bthis evening\b",
        r"\bthis morning\b",
        r"\bthis afternoon\b",
    ]

    for pattern in time_patterns:

        city = re.sub(
            pattern,
            "",
            city,
            flags=re.IGNORECASE,
        )

    # --------------------------------------------------------
    # Stop at command separators
    # --------------------------------------------------------

    city = re.split(
        r"\s+(?:and|tell|please|now)\b",
        city,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]

    city = city.strip(
        " .,?!"
    )

    return city or None


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

            # Some LLMs may return "name"
            tool_name = step.get(
                "name"
            )

        if not isinstance(
            tool_name,
            str
        ):
            continue

        tool_name = tool_name.strip()

        # ----------------------------------------------------
        # Reject unknown tools
        # ----------------------------------------------------

        if tool_name not in TOOLS:

            print(
                f"Agent skipped unknown tool: {tool_name}"
            )

            continue

        # ----------------------------------------------------
        # Arguments
        # ----------------------------------------------------

        arguments = step.get(
            "arguments",
            {}
        )

        if not isinstance(
            arguments,
            dict
        ):
            arguments = {}

        # ----------------------------------------------------
        # Weather normalization
        # ----------------------------------------------------

        if tool_name == "get_weather":

            city = arguments.get(
                "city"
            )

            days = arguments.get(
                "days",
                0
            )

            if isinstance(
                city,
                str
            ):
                city = clean_city(
                    city
                )

            try:

                days = int(
                    days
                )

            except (
                TypeError,
                ValueError
            ):

                days = 0

            # Keep weather offsets sane.
            days = max(
                0,
                min(
                    days,
                    7
                )
            )

            if not city:
                continue

            arguments = {
                "city": city,
                "days": days,
            }

        valid_plan.append({
            "tool": tool_name,
            "arguments": arguments,
        })

    return valid_plan


# ============================================================
# EXTRACT CITY
# ============================================================

def extract_city(command):

    if not command:
        return None

    command = str(
        command
    ).strip()

    patterns = [

        # weather in Delhi
        r"(?:weather|temperature|forecast)"
        r"\s+(?:in|for)\s+(.+)",

        # weather Delhi
        r"(?:weather|temperature|forecast)"
        r"\s+(.+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            command,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        city = match.group(
            1
        )

        # ----------------------------------------------------
        # Stop before time expressions
        # ----------------------------------------------------

        city = re.split(
            r"\s+(?:day\s+after\s+tomorrow|tomorrow|today|tonight)\b",
            city,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        # ----------------------------------------------------
        # Stop before another command
        # ----------------------------------------------------

        city = re.split(
            r"\s+(?:and|tell|please|now)\b",
            city,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        city = clean_city(
            city
        )

        if city:
            return city

    return None


# ============================================================
# EXTRACT WEATHER DAYS
# ============================================================

def extract_weather_days(command):

    command_lower = (
        command or ""
    ).lower()

    if "day after tomorrow" in command_lower:
        return 2

    if re.search(
        r"\btomorrow\b",
        command_lower,
    ):
        return 1

    if re.search(
        r"\b(?:today|tonight)\b",
        command_lower,
    ):
        return 0

    return 0


# ============================================================
# EXTRACT MULTIPLE WEATHER DAYS
# ============================================================

def extract_weather_days_list(command):

    command_lower = (
        command or ""
    ).lower()

    days = []

    # --------------------------------------------------------
    # Detect "day after tomorrow" first
    # --------------------------------------------------------

    if re.search(
        r"\bday\s+after\s+tomorrow\b",
        command_lower,
    ):

        days.append(
            2
        )

    # Remove it so "tomorrow" inside the phrase
    # does not become another request.

    remaining = re.sub(
        r"\bday\s+after\s+tomorrow\b",
        " ",
        command_lower,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Tomorrow
    # --------------------------------------------------------

    if re.search(
        r"\btomorrow\b",
        remaining,
    ):

        days.append(
            1
        )

    # --------------------------------------------------------
    # Today / tonight
    # --------------------------------------------------------

    if re.search(
        r"\b(?:today|tonight)\b",
        remaining,
    ):

        days.append(
            0
        )

    return sorted(
        set(days)
    )


# ============================================================
# EXTRACT WEBSITE
# ============================================================

def extract_website(command):

    command_lower = (
        command or ""
    ).lower()

    websites = [
        "google",
        "youtube",
        "facebook",
        "linkedin",
        "instagram",
        "github",
        "gmail",
        "spotify",
    ]

    for website in websites:

        if website not in command_lower:
            continue

        # Only open when the user actually asks
        # to open / launch / visit the website.

        if (
            re.search(
                r"\bopen\b",
                command_lower,
            )
            or re.search(
                r"\blaunch\b",
                command_lower,
            )
            or re.search(
                r"\bgo\s+to\b",
                command_lower,
            )
            or re.search(
                r"\bvisit\b",
                command_lower,
            )
        ):

            return website

    return None


# ============================================================
# EXTRACT MUSIC
# ============================================================

# ============================================================
# EXTRACT URL
# ============================================================

def extract_url(command):
    """Extract an explicit HTTP/HTTPS URL from a command."""
    if not command:
        return None

    match = re.search(
        r"https?://[^\s<>'\"]+",
        str(command),
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    url = match.group(0).strip()
    url = url.rstrip(".,!?;:)")
    return url or None


# ============================================================
# EXTRACT WEB SEARCH QUERY
# ============================================================

def extract_web_search_query(command):
    """Extract a query from an explicit web-search request."""
    if not command:
        return None

    text = str(command).strip()
    if not text:
        return None

    patterns = [
        r"\bsearch\s+the\s+web\s+for\s+(.+)",
        r"\bsearch\s+web\s+for\s+(.+)",
        r"\bsearch\s+on\s+the\s+web\s+for\s+(.+)",
        r"\bweb\s+search\s+for\s+(.+)",
        r"\bsearch\s+for\s+(.+)",
        r"\bsearch\s+about\s+(.+)",
        r"\blook\s+up\s+(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        query = match.group(1).strip()
        query = re.split(
            r"\s+(?:and\s+then|then)\s+",
            query,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        query = query.strip(" .,?!")

        if query:
            return query

    return None


def extract_song(command):

    if not command:
        return None

    # --------------------------------------------------------
    # Examples:
    #
    # Play Believer
    # Play Believer and open YouTube
    # Open YouTube and play Believer
    # Play Believer and tell me the news
    # --------------------------------------------------------

    pattern = (
        r"\bplay\s+"
        r"(.+?)"
        r"(?:\s+and\s+"
        r"(?:open|launch|go\s+to|visit|tell|check|"
        r"get|show|play)\b|$)"
    )

    match = re.search(
        pattern,
        command,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    song = match.group(
        1
    ).strip()

    song = song.strip(
        " .,?!"
    )

    return song or None


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicate_steps(plan):

    unique_plan = []

    seen = set()

    for step in plan:

        if not isinstance(
            step,
            dict
        ):
            continue

        tool = step.get(
            "tool"
        )

        arguments = step.get(
            "arguments",
            {}
        )

        key = (
            tool,
            json.dumps(
                arguments,
                sort_keys=True,
                default=str,
            ),
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        unique_plan.append(
            step
        )

    return unique_plan


# ============================================================
# NORMALIZE TOOL ORDER
# ============================================================

def normalize_tool_order(plan):
    """
    Make deterministic multi-tool plans predictable.

    Example:

        Play Believer and open YouTube

    becomes:

        open_website
        play_music

    regardless of natural-language order.
    """

    priority = {
        "open_app": 10,
        "open_folder": 11,
        "open_file": 12,
        "open_url": 20,
        "open_website": 21,
        "search_web": 30,
        "get_weather": 40,
        "get_news": 50,
        "get_time": 60,
        "get_date": 70,
        "play_music": 80,
    }

    return sorted(
        plan,
        key=lambda step: priority.get(
            step.get("tool"),
            999,
        ),
    )


# ============================================================
# MEMORY QUESTION DETECTION
# ============================================================

def is_memory_question(command):

    text = (
        command or ""
    ).lower().strip()

    patterns = [

        # Explicit personal-memory questions.
        r"\bwhat\s+is\s+my\b",
        r"\bwhat\s+are\s+my\b",
        r"\bwhat\s+do\s+i\s+(?:prefer|like|love)\b",
        r"\bwhat\s+is\s+my\s+(?:favorite|favourite)\b",

        r"\bwhat\s+(?:is|are)\s+my\b",

        r"\bwhat\s+do\s+i\s+"
        r"(?:prefer|like|love)\b",

        r"\bwhat\s+is\s+my\s+"
        r"(?:favorite|favourite)\b",

        r"\bdo\s+you\s+remember\b",

        r"\bwhat\s+do\s+you\s+remember\b",

        r"\bwhat\s+did\s+i\s+tell\s+you\b",

        r"\bwhat\s+have\s+i\s+told\s+you\b",
    ]

    return any(
        re.search(
            pattern,
            text,
        )
        for pattern in patterns
    )


# ============================================================
# SYSTEM COMMAND EXTRACTION
# ============================================================

SYSTEM_APPS = [
    "google chrome",
    "chrome",
    "microsoft edge",
    "edge",
    "firefox",
    "visual studio code",
    "vs code",
    "vscode",
    "notepad",
    "calculator",
    "calc",
    "paint",
    "mspaint",
    "file explorer",
    "explorer",
    "windows terminal",
    "terminal",
    "powershell",
    "command prompt",
    "cmd",
]


def extract_system_app(command):
    """Extract an allow-listed app from an explicit open/launch request."""
    text = (command or "").strip()
    if not text:
        return None

    app_pattern = "|".join(
        re.escape(app)
        for app in sorted(SYSTEM_APPS, key=len, reverse=True)
    )

    match = re.search(
        rf"\b(?:open|launch|start|run)\s+(?:the\s+)?({app_pattern})\b",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1).strip().lower()


FOLDER_ALIASES = [
    "downloads",
    "documents",
    "desktop",
    "pictures",
    "music",
    "videos",
    "home",
    "user home",
    "project folder",
    "project",
    "current folder",
]


def extract_folder(command):
    """Extract a safe folder alias from an explicit open request."""
    text = (command or "").strip()
    if not text:
        return None

    aliases = "|".join(
        re.escape(item)
        for item in sorted(FOLDER_ALIASES, key=len, reverse=True)
    )

    match = re.search(
        rf"\b(?:open|launch)\s+(?:my\s+|the\s+)?({aliases})(?:\s+folder)?\b",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1).strip().lower()


def extract_file_path(command):
    """
    Extract an explicitly requested local file path.

    Deterministic parsing only handles quoted paths or paths with a
    recognizable file extension. Arbitrary natural-language file
    selection is left to the LLM planner.
    """
    text = (command or "").strip()
    if not text:
        return None

    quoted = re.search(
        r'\b(?:open|launch)\s+(?:the\s+)?["\']([^"\']+)["\']',
        text,
        flags=re.IGNORECASE,
    )
    if quoted:
        candidate = quoted.group(1).strip()
        if "." in candidate or "\\" in candidate or "/" in candidate:
            return candidate

    extension = (
        r"(?:txt|pdf|doc|docx|xls|xlsx|csv|py|js|ts|jsx|tsx|html|css|json|"
        r"xml|md|png|jpg|jpeg|gif|webp|mp3|wav|mp4|mkv|zip)"
    )

    match = re.search(
        rf"\b(?:open|launch)\s+(?:the\s+)?(.+?\.(?:{extension}))"
        rf"(?=\s+(?:and|then)\b|$)",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    candidate = match.group(1).strip().strip(" .,?!")
    return candidate or None


# ============================================================
# PLAN COMMAND
# ============================================================

def plan_command(command):

    if not command:
        return []

    command = str(
        command
    ).strip()

    if not command:
        return []

    command_lower = command.lower()

    explicit_web_search = bool(
    re.search(
        r"\b(?:search|look\s+up|look\s+for|search\s+for|google)\b",
        command_lower,
    )
)

    # ========================================================
    # MEMORY QUESTIONS NEVER NEED TOOLS
    # ========================================================

    if is_memory_question(
        command
    ):

        print(
            "Memory question detected."
        )

        return []

    # ========================================================
    # DETERMINISTIC PLAN
    # ========================================================

    plan = []

    # ========================================================
    # WEATHER
    # ========================================================

    weather_words = [
        "weather",
        "temperature",
        "forecast",
    ]

    if any(
        word in command_lower
        for word in weather_words
    ):

        city = extract_city(
            command
        )

        if city:

            requested_days = (
                extract_weather_days_list(
                    command
                )
            )

            # No explicit day = today

            if not requested_days:

                requested_days = [
                    0
                ]

            for days in requested_days:

                plan.append({
                    "tool": "get_weather",
                    "arguments": {
                        "city": city,
                        "days": days,
                    },
                })

    # ========================================================
    # NEWS
    # ========================================================

    news_patterns = [
        r"\bnews\b",
        r"\bheadlines\b",
        r"\blatest\s+news\b",
        r"\btoday'?s\s+news\b",
        r"\blatest\s+headlines\b",
    ]

    if (
    not explicit_web_search
    and any(
        re.search(
            pattern,
            command_lower,
        )
        for pattern in news_patterns
    )
):

        plan.append({
            "tool": "get_news",
            "arguments": {},
        })

    # ========================================================
    # TIME
    # ========================================================

    time_patterns = [
        r"\bwhat\s+time\b",
        r"\bcurrent\s+time\b",
        r"\btime\s+is\s+it\b",
        r"\btell\s+me\s+the\s+time\b",
        r"\bcurrent\s+local\s+time\b",
    ]

    if any(
        re.search(
            pattern,
            command_lower,
        )
        for pattern in time_patterns
    ):

        plan.append({
            "tool": "get_time",
            "arguments": {},
        })

    # ========================================================
    # DATE
    # ========================================================

    date_patterns = [
        r"\btoday'?s\s+date\b",
        r"\bwhat\s+date\b",
        r"\bcurrent\s+date\b",
        r"\bwhat\s+is\s+the\s+date\b",
        r"\bwhat'?s\s+the\s+date\b",
        r"\btell\s+me\s+the\s+date\b",
    ]

    if any(
        re.search(
            pattern,
            command_lower,
        )
        for pattern in date_patterns
    ):

        plan.append({
            "tool": "get_date",
            "arguments": {},
        })

    # ========================================================
    # SYSTEM APP / FOLDER / FILE CONTROL
    # ========================================================

    app = extract_system_app(
        command
    )

    if app:
        plan.append({
            "tool": "open_app",
            "arguments": {
                "name": app,
            },
        })

    folder = extract_folder(
        command
    )

    if folder:
        plan.append({
            "tool": "open_folder",
            "arguments": {
                "path": folder,
            },
        })

    file_path = extract_file_path(
        command
    )

    if file_path:
        plan.append({
            "tool": "open_file",
            "arguments": {
                "path": file_path,
            },
        })

    # ========================================================
    # WEBSITE
    # ========================================================

    website = None

    if not extract_url(command):
       website = extract_website(
        command
    )

    if website:

        plan.append({
            "tool": "open_website",
            "arguments": {
                "name": website,
            },
        })

    # ========================================================
    # WEB URL / SEARCH
    # ========================================================

    explicit_url = extract_url(command)

    if explicit_url:
        plan.append({
            "tool": "open_url",
            "arguments": {
                "url": explicit_url,
            },
        })
    else:
        search_query = extract_web_search_query(command)

        if search_query:
            plan.append({
                "tool": "search_web",
                "arguments": {
                    "query": search_query,
                    "max_results": 5,
                },
            })

    # ========================================================
    # MUSIC
    # ========================================================

    song = extract_song(
        command
    )

    if song:

        plan.append({
            "tool": "play_music",
            "arguments": {
                "song": song,
            },
        })

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    plan = remove_duplicate_steps(
        plan
    )

    # ========================================================
    # NORMALIZE DETERMINISTIC ORDER
    # ========================================================

    plan = normalize_tool_order(
        plan
    )

    # ========================================================
    # RETURN DETERMINISTIC PLAN
    # ========================================================

    if plan:

        print(
            "Deterministic plan:",
            plan,
        )

        return plan

    # ========================================================
    # LLM FALLBACK
    # ========================================================

    tools = get_tool_descriptions()

    prompt = f"""
You are the planning engine for Jarvis.

Available tools:

{json.dumps(
    tools,
    indent=2,
    ensure_ascii=False,
    default=str,
)}

User request:

{command}

Determine which available tools are required.

RULES:

1. Return ONLY valid JSON.

2. Prefer this format:

{{
    "tools": [
        {{
            "tool": "get_time",
            "arguments": {{}}
        }}
    ]
}}

3. If no tool is required:

{{
    "tools": []
}}

4. Use ONLY tools from the available tools list.

5. Never invent a tool.

6. Personal-memory questions require NO tools.

7. For weather:
   - city must contain ONLY the city name.
   - never put "today" in city.
   - never put "tomorrow" in city.
   - never put "day after tomorrow" in city.

8. Weather days:
   - today = 0
   - tomorrow = 1
   - day after tomorrow = 2

9. If tomorrow AND day after tomorrow are requested,
   return TWO get_weather calls.

10. For:
    "What is the weather in Delhi tomorrow?"

return:

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

11. For:
    "What programming language do I prefer?"

return:

{{
    "tools": []
}}

12. Do not add unnecessary tools.

13. For web searches:

    - use search_web ONLY when the user explicitly asks to
      search, look up, browse, or search the web.
    - put the actual search request in the "query" argument.
    - max_results should normally be 5.
    - do not use search_web for ordinary questions unless
      the user explicitly requests a web search.

14. For explicit URLs:

    - use open_url when the user explicitly asks to open
      a specific HTTP or HTTPS URL.
    - only use complete HTTP or HTTPS URLs.
    - never invent a URL.
    - preserve the URL exactly as provided by the user.

15. For:
    "Search the web for React tutorials"

return:

{{
    "tools": [
        {{
            "tool": "search_web",
            "arguments": {{
                "query": "React tutorials",
                "max_results": 5
            }}
        }}
    ]
}}

16. For:
    "Open https://github.com"

return:

{{
    "tools": [
        {{
            "tool": "open_url",
            "arguments": {{
                "url": "https://github.com"
            }}
        }}
    ]
}}

17. If multiple independent actions are requested, return all
    required tools.

18. Keep tools in the same logical order as the user's request
    whenever possible.

19. Use the minimum number of tools necessary.

20. Never execute a tool yourself.

21. Never explain your reasoning.

22. Never include Markdown or comments.

23. Do not mention anything outside the JSON.
"""

    try:

        response = ollama.chat(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            format="json",
        )

        raw = (
            response
            .get("message", {})
            .get("content", "")
            .strip()
        )

        print(
            "Agent raw response:",
            raw,
        )

        if not raw:
            return []

        data = json.loads(
            raw
        )

        plan = normalize_plan(
            data
        )

        plan = validate_plan(
            plan
        )

        plan = remove_duplicate_steps(
            plan
        )

        plan = normalize_tool_order(
            plan
        )

        return plan

    except Exception as e:

        print(
            "Agent planning error:",
            e,
        )

        return []


# ============================================================
# EXECUTE PLAN
# ============================================================

def execute_plan(plan):
    """Execute a validated tool plan defensively.

    Reliability guarantees:
      - Non-list plans return an empty result list.
      - Malformed steps are skipped without stopping later steps.
      - Tool exceptions are converted into structured failures.
      - A failed tool never prevents the next tool from running.
    """

    results = []

    if not isinstance(plan, list):
        return results

    for step in plan:
        if not isinstance(step, dict):
            print(f"Agent skipped invalid plan step: {step}")
            results.append({
                "tool": None,
                "arguments": {},
                "result": {
                    "success": False,
                    "error": "Invalid plan step; expected an object."
                },
            })
            continue

        tool_name = step.get("tool")
        if not isinstance(tool_name, str):
            tool_name = step.get("name")

        if not isinstance(tool_name, str) or not tool_name.strip():
            print(f"Agent skipped invalid plan step: {step}")
            results.append({
                "tool": tool_name,
                "arguments": {},
                "result": {
                    "success": False,
                    "error": "Invalid plan step: missing tool name."
                },
            })
            continue

        tool_name = tool_name.strip()
        arguments = step.get("arguments", {})
        if not isinstance(arguments, dict):
            arguments = {}

        print(f"Executing tool: {tool_name}")
        print(f"Arguments: {arguments}")

        try:
            result = execute_tool(tool_name, arguments)
        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
            }

        results.append({
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
        })

    return results


# ============================================================
# FORMAT WEATHER
# ============================================================

def format_weather_result(
    result,
    requested_days=0,
):

    if not isinstance(
        result,
        dict
    ):

        return str(
            result
        )

    if result.get(
        "success"
    ) is False:

        return str(
            result.get(
                "error"
            )
            or result.get(
                "message"
            )
            or "Weather data is unavailable."
        )

    city = result.get(
        "city"
    ) or "the requested city"

    description = (
        result.get(
            "description"
        )
        or result.get(
            "condition"
        )
        or "unknown conditions"
    )

    high = result.get(
        "high"
    )

    low = result.get(
        "low"
    )

    days = result.get(
        "days",
        requested_days,
    )

    # --------------------------------------------------------
    # Time wording
    # --------------------------------------------------------

    if days == 0:

        prefix = (
            f"Today's weather in {city}"
        )

    elif days == 1:

        prefix = (
            f"Tomorrow's weather in {city}"
        )

    elif days == 2:

        prefix = (
            f"The day after tomorrow's weather in {city}"
        )

    else:

        date = result.get(
            "date"
        )

        if date:

            prefix = (
                f"The weather in {city} on {date}"
            )

        else:

            prefix = (
                f"The weather in {city}"
            )

    text = (
        f"{prefix} is expected to be "
        f"{description}"
    )

    if (
        high is not None
        and low is not None
    ):

        text += (
            f", with a high of {high}°C "
            f"and a low of {low}°C"
        )

    elif high is not None:

        text += (
            f", with a high of {high}°C"
        )

    elif low is not None:

        text += (
            f", with a low of {low}°C"
        )

    return (
        text
        + "."
    )


# ============================================================
# MEMORY CONTEXT
# ============================================================

def _memory_text_for(command):

    if build_memory_context is None:

        return NO_MEMORY_TEXT

    try:

        data = build_memory_context(
            command
        )

        if isinstance(
            data,
            dict
        ):

            text = data.get(
                "formatted",
                ""
            )

        else:

            text = str(
                data or ""
            )

        text = text.strip()

        return (
            text
            if text
            else NO_MEMORY_TEXT
        )

    except Exception as e:

        print(
            "Memory context error:",
            e,
        )

        return NO_MEMORY_TEXT


# ============================================================
# ANSWER FROM MEMORY
# ============================================================

def answer_from_memory(
    command,
    memory_text,
):

    if (
        not memory_text
        or NO_MEMORY_TEXT in memory_text
    ):

        return (
            "I don't remember that yet."
        )

    command_lower = (
        command or ""
    ).lower()

    # --------------------------------------------------------
    # Programming language
    # --------------------------------------------------------

    if (
        "programming language"
        in command_lower
        and (
            "prefer"
            in command_lower
            or "favorite"
            in command_lower
            or "favourite"
            in command_lower
            or "like"
            in command_lower
        )
    ):

        if re.search(
            r"\bpython\b",
            memory_text,
            re.IGNORECASE,
        ):

            return (
                "Your preferred programming "
                "language is Python."
            )

    # --------------------------------------------------------
    # Generic memory response
    # --------------------------------------------------------

    lines = []

    for line in memory_text.splitlines():

        line = line.strip()

        if line.startswith(
            "-"
        ):

            line = line[
                1:
            ].strip()

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
# CLEAN RESPONSE
# ============================================================

def clean_response(text):

    text = str(
        text or ""
    ).strip()

    # --------------------------------------------------------
    # Remove common assistant prefixes
    # --------------------------------------------------------

    prefixes = [
        "assistant:",
        "jarvis:",
    ]

    changed = True

    while changed:

        changed = False

        for prefix in prefixes:

            if text.lower().startswith(
                prefix
            ):

                text = text[
                    len(prefix):
                ].strip()

                changed = True

    # --------------------------------------------------------
    # Remove surrounding quotes
    # --------------------------------------------------------

    if (
        len(text) >= 2
        and text[0] in "\"'"
        and text[-1] == text[0]
    ):

        text = text[
            1:-1
        ].strip()

    # --------------------------------------------------------
    # Remove accidental code fences
    # --------------------------------------------------------

    if text.startswith(
        "```"
    ):

        text = text.replace(
            "```",
            "",
        ).strip()

    return text


# ============================================================
# BUILD FALLBACK RESPONSE
# ============================================================

def build_fallback_response(
    results
):

    responses = []

    for item in results:

        tool = item.get(
            "tool"
        )

        result = item.get(
            "result"
        )

        if result is None:
            continue

        # ====================================================
        # WEATHER
        # ====================================================

        if tool == "get_weather":

            arguments = item.get(
                "arguments",
                {}
            )

            days = arguments.get(
                "days",
                0
            )

            responses.append(
                format_weather_result(
                    result,
                    days,
                )
            )

        # ====================================================
        # TIME
        # ====================================================

        elif tool == "get_time":

            if isinstance(
                result,
                dict
            ):

                time = result.get(
                    "time"
                )

                if time:

                    responses.append(
                        f"The current time is {time}."
                    )

                elif result.get(
                    "message"
                ):

                    responses.append(
                        str(
                            result["message"]
                        )
                    )

        # ====================================================
        # DATE
        # ====================================================

        elif tool == "get_date":

            if isinstance(
                result,
                dict
            ):

                date = result.get(
                    "date"
                )

                if date:

                    responses.append(
                        f"Today is {date}."
                    )

                elif result.get(
                    "message"
                ):

                    responses.append(
                        str(
                            result["message"]
                        )
                    )

        # ====================================================
        # WEBSITE
        # ====================================================

        elif tool == "open_website":

            if isinstance(
                result,
                dict
            ):

                message = result.get(
                    "message"
                )

                if message:

                    responses.append(
                        str(
                            message
                        )
                    )

        # ====================================================
        # MUSIC
        # ====================================================

        elif tool == "play_music":

            if isinstance(
                result,
                dict
            ):

                message = result.get(
                    "message"
                )

                if message:

                    responses.append(
                        str(
                            message
                        )
                    )

        # ====================================================
        # SYSTEM APP / FOLDER / FILE
        # ====================================================

        elif tool in {
            "open_app",
            "open_folder",
            "open_file",
        }:
            if isinstance(result, dict):
                message = result.get("message")
                if message:
                    responses.append(str(message))

        # ====================================================
        # OPEN URL
        # ====================================================

        elif tool == "open_url":
            if isinstance(result, dict):
                message = result.get("message")
                if message:
                    responses.append(str(message))

        # ====================================================
        # WEB SEARCH
        # ====================================================

        elif tool == "search_web":
            if isinstance(result, dict):
                search_results = result.get("results", [])
                query = result.get("query", "")
                items = []

                for search_result in search_results[:5]:
                    if not isinstance(search_result, dict):
                        continue

                    title = search_result.get("title")
                    url = search_result.get("url")
                    snippet = search_result.get("snippet")

                    if not title:
                        continue

                    text = str(title)
                    if snippet:
                        text += f": {snippet}"
                    if url:
                        text += f" ({url})"
                    items.append(text)

                if items:
                    responses.append(
                        f"Here are the web results for '{query}': "
                        + " ".join(items)
                    )
                elif result.get("message"):
                    responses.append(str(result["message"]))

        # ====================================================
        # NEWS
        # ====================================================

        elif tool == "get_news":

            if isinstance(
                result,
                dict
            ):

                articles = result.get(
                    "articles",
                    []
                )

                headlines = []

                for article in articles[:3]:

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

                        headlines.append(
                            f"{title} ({source})"
                        )

                    else:

                        headlines.append(
                            str(
                                title
                            )
                        )

                if headlines:

                    responses.append(
                        "Here are the latest headlines: "
                        + " ".join(
                            headlines
                        )
                    )

                elif result.get(
                    "message"
                ):

                    responses.append(
                        str(
                            result["message"]
                        )
                    )

        # ====================================================
        # ERROR
        # ====================================================

        if isinstance(
            result,
            dict
        ):

            success = result.get(
                "success"
            )

            error = result.get(
                "error"
            )

            if (
                success is False
                and error
            ):

                responses.append(
                    str(error)
                )

    if responses:

        return clean_response(
            " ".join(
                responses
            )
        )

    return (
        "The requested action was completed."
    )


# ============================================================
# GENERATE FINAL RESPONSE
# ============================================================

def generate_final_response(
    command,
    results,
    memory_text="",
):

    """
    Generate a deterministic response from actual
    tool results.

    Weather is intentionally formatted without an LLM
    to prevent hallucinated dates, cities, weekdays,
    or forecast values.
    """

    if not results:

        if (
            memory_text
            and NO_MEMORY_TEXT not in memory_text
        ):

            return answer_from_memory(
                command,
                memory_text,
            )

        return (
            "I couldn't find an action "
            "to perform for that request."
        )

    # --------------------------------------------------------
    # Weather
    # --------------------------------------------------------

    weather_items = [
        item
        for item in results
        if item.get("tool")
        == "get_weather"
    ]

    # --------------------------------------------------------
    # Non-weather
    # --------------------------------------------------------

    other_items = [
        item
        for item in results
        if item.get("tool")
        != "get_weather"
    ]

    parts = []

    # --------------------------------------------------------
    # Format every weather result directly
    # --------------------------------------------------------

    for item in weather_items:

        arguments = item.get(
            "arguments",
            {}
        )

        days = arguments.get(
            "days",
            0
        )

        parts.append(
            format_weather_result(
                item.get(
                    "result"
                ),
                days,
            )
        )

    # --------------------------------------------------------
    # Format other results
    # --------------------------------------------------------

    if other_items:

        other_text = build_fallback_response(
            other_items
        )

        if (
            other_text
            and other_text
            != "The requested action was completed."
        ):

            parts.append(
                other_text
            )

    if parts:

        return clean_response(
            " ".join(
                parts
            )
        )

    return build_fallback_response(
        results
    )


# ============================================================
# RUN AGENT
# ============================================================

def run_agent(command):
    """
    Main Jarvis pipeline.

    Production-safe order:

        User input
          ↓
        Memory-question detection FIRST
          ↓
        Context resolution
          ↓
        Long-term memory
          ↓
        Planner
          ↓
        Tool execution
          ↓
        Deterministic final response
          ↓
        Short-term context update

    Important reliability guarantees:
      - Memory questions never reach the context resolver/planner.
      - Context-resolution failures fall back to the original command.
      - Planner failures fail closed instead of crashing Jarvis.
      - Final-response failures fall back to actual tool results.
      - Context-update failures never crash the user request.
    """

    print("\n================================")
    print("Agent request:", command)

    # ========================================================
    # STEP 0 — INPUT VALIDATION
    # ========================================================

    original_command = str(command or "").strip()

    if not original_command:
        return "Please tell me what you'd like me to do."

    # ========================================================
    # STEP 1 — MEMORY QUESTION FIRST
    # ========================================================
    #
    # This MUST happen before resolve_command().
    #
    # Example:
    #   "What programming language do I prefer?"
    #
    # must go directly to long-term memory. Otherwise the context
    # resolver/LLM can incorrectly rewrite it into something like:
    #   "play programming language again"
    # and the planner may call play_music.
    # ========================================================

    if is_memory_question(original_command):

        print("Memory question detected.")

        memory_text = _memory_text_for(
            original_command
        )

        print(
            "Relevant long-term memories:",
            memory_text,
        )

        try:
            final_response = answer_from_memory(
                original_command,
                memory_text,
            )
        except Exception as e:
            print("Memory answer error:", e)
            final_response = "I don't remember that yet."

        final_response = clean_response(
            final_response
        ) or "I don't remember that yet."

        print("Agent plan: []")
        print(
            "Agent final response:",
            final_response,
        )

        return final_response

    # ========================================================
    # STEP 2 — CONTEXT RESOLUTION
    # ========================================================

    try:
        resolved_command = resolve_command(
            original_command
        )
    except Exception as e:
        print("Context resolution error:", e)
        resolved_command = original_command

    resolved_command = clean_response(
        resolved_command
    ) or original_command

    if resolved_command.lower() != original_command.lower():
        print(
            "Context resolved:",
            resolved_command,
        )

    # ========================================================
    # STEP 3 — LONG-TERM MEMORY
    # ========================================================

    memory_text = _memory_text_for(
        resolved_command
    )

    print(
        "Relevant long-term memories:",
        memory_text,
    )

    # A context resolver should never turn a normal request into a
    # memory question. Keep this second guard for safety.
    if is_memory_question(resolved_command):

        print("Memory question detected after resolution.")

        try:
            final_response = answer_from_memory(
                resolved_command,
                memory_text,
            )
        except Exception as e:
            print("Memory answer error:", e)
            final_response = "I don't remember that yet."

        final_response = clean_response(
            final_response
        ) or "I don't remember that yet."

        print("Agent plan: []")
        print(
            "Agent final response:",
            final_response,
        )

        return final_response

    # ========================================================
    # STEP 4 — PLAN
    # ========================================================

    try:
        plan = plan_command(
            resolved_command
        )
    except Exception as e:
        # Phase-5 reliability: planner failures fail closed.
        print("Planner pipeline error:", e)
        plan = []

    print(
        "Agent plan:",
        plan,
    )

    # ========================================================
    # STEP 5 — NO TOOL PLAN
    # ========================================================

    if not plan:

        try:
            final_response = generate_final_response(
                resolved_command,
                [],
                memory_text,
            )
            final_response = clean_response(
                final_response
            )
        except Exception as e:
            print("Final response error:", e)
            final_response = (
                "I couldn't determine an action for that request."
            )

        print(
            "Agent final response:",
            final_response,
        )

        return final_response

    # ========================================================
    # STEP 6 — EXECUTE TOOLS
    # ========================================================

    try:
        results = execute_plan(
            plan
        )
    except Exception as e:
        # execute_plan is already defensive, but keep the agent
        # boundary safe if its implementation itself fails.
        print("Tool execution pipeline error:", e)
        results = []

    print(
        "Agent results:",
        results,
    )

    # ========================================================
    # STEP 7 — FINAL RESPONSE
    # ========================================================

    try:
        final_response = generate_final_response(
            resolved_command,
            results,
            memory_text,
        )

        final_response = clean_response(
            final_response
        )

    except Exception as e:
        # Phase-5 reliability: if the response formatter fails,
        # use the actual structured tool results instead of losing
        # the successful operation.
        print("Final response error:", e)

        try:
            final_response = build_fallback_response(
                results
            )
        except Exception as fallback_error:
            print(
                "Fallback response error:",
                fallback_error,
            )
            final_response = (
                "The request was processed, "
                "but I couldn't generate the final response."
            )

        final_response = clean_response(
            final_response
        ) or "The request was processed successfully."

    print(
        "Agent final response:",
        final_response,
    )

    # ========================================================
    # STEP 8 — UPDATE SHORT-TERM CONTEXT
    # ========================================================

    for item in results:

        if not isinstance(item, dict):
            continue

        try:
            update_context(
                command=original_command,
                tool=item.get("tool"),
                arguments=item.get(
                    "arguments",
                    {},
                ),
                response=final_response,
            )

        except Exception as e:
            # Context persistence is secondary. Never let it crash
            # an otherwise successful user request.
            print(
                "Context update error:",
                e,
            )

    return final_response


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    test_commands = [

        "What time is it?",

        "What's today's date?",

        "Open YouTube",

        "Play Believer",

        "Open YouTube and play Believer",

        "Play Believer and open YouTube",

        "Tell me the latest news",

        "What's the weather in Delhi?",

        "What is the weather in Delhi tomorrow?",

        "What is the weather in Delhi day after tomorrow?",

        "What is the weather in Kolkata tomorrow and the day after tomorrow?",

        "What time is it and what's today's date?",

        "Check the weather in Delhi and tell me the latest news",

        "Search the web for React tutorials",
        "Open https://github.com",
        "What programming language do I prefer?",
    ]

    for command in test_commands:

        print(
            "\n================================"
        )

        print(
            "USER:",
            command,
        )

        plan = plan_command(
            command
        )

        print(
            "PLAN:"
        )

        print(
            json.dumps(
                plan,
                indent=4,
                ensure_ascii=False,
                default=str,
            )
        )

        if plan:

            results = execute_plan(
                plan
            )

            print(
                "RESULTS:"
            )

            print(
                json.dumps(
                    results,
                    indent=4,
                    ensure_ascii=False,
                    default=str,
                )
            )