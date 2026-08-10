import ollama


def generate_response(user_command, tool_results):

    try:

        results_text = "\n\n".join(
            f"Tool: {result['tool']}\n"
            f"Result: {result['result']}"
            for result in tool_results
        )

        prompt = f"""
You are Jarvis, a helpful personal AI assistant.

The user asked:

{user_command}

The tools produced these results:

{results_text}

Create one natural, concise response for the user.

Rules:
- Use the information from the tool results.
- Do not invent information.
- Do not mention internal tools, JSON, APIs, or routing.
- Do not say that you are a text-based AI.
- Keep the response concise because it will be spoken aloud.
"""

        response = ollama.chat(
            model="llama3.2",
            messages=[
                {
                    "role": "system",
                    "content": prompt
                }
            ]
        )

        return response["message"]["content"].strip()

    except Exception as e:

        print("Response generation error:", e)

        # Safe fallback
        if tool_results:
            return " ".join(
                result["result"]
                for result in tool_results
            )

        return "Sorry, I could not generate a response."