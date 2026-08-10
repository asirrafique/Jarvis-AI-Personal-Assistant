import json
import re
import ollama

from jarvis.context import update_context, get_context


# ==========================================
# JARVIS AI ROUTER
# ==========================================

SYSTEM_PROMPT = """
You are Jarvis's AI command router.

Your job is to understand the user's request and decide
which tool or tools should handle it.

You MUST return ONLY a valid JSON ARRAY.

Never return normal text.
Never use markdown.
Never explain your decision.


AVAILABLE TOOLS
================

1. open_website

Arguments:
{
    "name": "google|youtube|facebook|linkedin|github"
}


2. play_music

Arguments:
{
    "song": "song name"
}


3. get_news

Arguments:
{}


4. get_weather

Arguments:
{
    "city": "city name",
    "days": 0
}

Weather days:
0 = today
1 = tomorrow
2 = two days from now
3 = three days from now


5. get_time

Arguments:
{}


6. get_date

Arguments:
{}


7. ai

Arguments:
{
    "command": "original user request"
}


IMPORTANT RULES
================

RULE 1:
A request can require multiple tools.


RULE 2:
Use the conversation context when the user
does not explicitly provide all information.


RULE 3:
If the user says:

"What about tomorrow?"

and the previous context contains:

last_city = Delhi
last_topic = weather

then return:

[
    {
        "tool": "get_weather",
        "arguments": {
            "city": "Delhi",
            "days": 1
        }
    }
]


RULE 4:
If the user says:

"What about the day after tomorrow?"

use:

days = 2


RULE 5:
If the user says:

"What about in three days?"

use:

days = 3


RULE 6:
If the user explicitly gives a city,
always prefer that city over the previous context.


RULE 7:
If the user asks about weather without
giving a city, use last_city if available.


RULE 8:
If no city is available for a weather request,
use the AI tool instead of inventing a city.


RULE 9:
For general questions that don't require
a specific tool, use the ai tool.


EXAMPLES
================


User:
Open YouTube

Return:

[
    {
        "tool": "open_website",
        "arguments": {
            "name": "youtube"
        }
    }
]


User:
Play Believer

Return:

[
    {
        "tool": "play_music",
        "arguments": {
            "song": "Believer"
        }
    }
]


User:
Tell me the news

Return:

[
    {
        "tool": "get_news",
        "arguments": {}
    }
]


User:
What's the weather in Kolkata?

Return:

[
    {
        "tool": "get_weather",
        "arguments": {
            "city": "Kolkata",
            "days": 0
        }
    }
]


User:
What time is it?

Return:

[
    {
        "tool": "get_time",
        "arguments": {}
    }
]


User:
What's today's date?

Return:

[
    {
        "tool": "get_date",
        "arguments": {}
    }
]


User:
Explain artificial intelligence

Return:

[
    {
        "tool": "ai",
        "arguments": {
            "command": "Explain artificial intelligence"
        }
    }
]


CONTEXT EXAMPLE
================


Previous context:

last_city = Delhi
last_topic = weather

User:
What about tomorrow?

Return:

[
    {
        "tool": "get_weather",
        "arguments": {
            "city": "Delhi",
            "days": 1
        }
    }
]


Previous context:

last_city = Mumbai
last_topic = weather

User:
What about the day after tomorrow?

Return:

[
    {
        "tool": "get_weather",
        "arguments": {
            "city": "Mumbai",
            "days": 2
        }
    }
]


MULTI-TOOL EXAMPLE
================


User:
Check the weather in Delhi and tell me the latest news.

Return:

[
    {
        "tool": "get_weather",
        "arguments": {
            "city": "Delhi",
            "days": 0
        }
    },
    {
        "tool": "get_news",
        "arguments": {}
    }
]
"""


# ==========================================
# AI ROUTER FUNCTION
# ==========================================

def ai_route(command):

    try:

        # ----------------------------------
        # Update shared context
        # ----------------------------------

        update_context(command)

        current_context = get_context()

        print("Router context:", current_context)


        # ----------------------------------
        # Send command + context to Llama
        # ----------------------------------

        user_message = f"""
Current user request:

{command}


Current Jarvis context:

last_city: {current_context.get("last_city")}
last_topic: {current_context.get("last_topic")}
last_song: {current_context.get("last_song")}
last_website: {current_context.get("last_website")}


Use this context when necessary.
"""


        response = ollama.chat(
            model="llama3.2",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )


        # ----------------------------------
        # Extract Llama response
        # ----------------------------------

        content = response["message"]["content"].strip()

        print("Router response:", content)


        # ----------------------------------
        # Remove markdown fences
        # ----------------------------------

        content = re.sub(
            r"```json\s*",
            "",
            content,
            flags=re.IGNORECASE
        )

        content = re.sub(
            r"```\s*",
            "",
            content
        )

        content = content.strip()


        # ----------------------------------
        # Parse JSON
        # ----------------------------------

        result = json.loads(content)


        # ----------------------------------
        # Make sure result is a list
        # ----------------------------------

        if not isinstance(result, list):

            result = [result]


        # ----------------------------------
        # Valid tools
        # ----------------------------------

        valid_tools = {
            "open_website",
            "play_music",
            "get_news",
            "get_weather",
            "get_time",
            "get_date",
            "ai"
        }


        # ----------------------------------
        # Validate results
        # ----------------------------------

        validated_results = []


        for item in result:

            if not isinstance(item, dict):
                continue


            tool = item.get("tool")


            if tool not in valid_tools:
                continue


            arguments = item.get(
                "arguments",
                {}
            )


            if not isinstance(arguments, dict):

                arguments = {}


            # ------------------------------
            # Weather validation
            # ------------------------------

            if tool == "get_weather":

                city = arguments.get("city")

                days = arguments.get(
                    "days",
                    0
                )


                # If Llama forgot the city,
                # use the previous city.

                if not city:

                    city = current_context.get(
                        "last_city"
                    )


                # Make sure days is an integer

                try:

                    days = int(days)

                except (
                    TypeError,
                    ValueError
                ):

                    days = 0


                # Prevent unreasonable values

                days = max(
                    0,
                    min(days, 7)
                )


                # If we still don't have
                # a city, fall back to AI.

                if not city:

                    validated_results.append({
                        "tool": "ai",
                        "arguments": {
                            "command": command
                        }
                    })

                    continue


                arguments = {
                    "city": city,
                    "days": days
                }


            item["arguments"] = arguments

            validated_results.append(item)


        # ----------------------------------
        # No valid tools
        # ----------------------------------

        if not validated_results:

            raise ValueError(
                "No valid tools returned by router."
            )


        return validated_results


    except Exception as e:

        print("Router Error:", e)


        # Safe fallback

        return [
            {
                "tool": "ai",
                "arguments": {
                    "command": command
                }
            }
        ]