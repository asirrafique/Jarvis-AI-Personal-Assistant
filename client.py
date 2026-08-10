import ollama
import json
import os

from jarvis.context import update_context, get_context

from jarvis.memory import (
    initialize_database,
    save_memory,
    semantic_search
)


# ==========================================
# CONFIGURATION
# ==========================================

MEMORY_FILE = "jarvis_memory.json"
MODEL = "llama3.2"

# Maximum number of previous conversation messages
MAX_CONVERSATION_MESSAGES = 20

# Minimum semantic similarity required
MEMORY_SEARCH_THRESHOLD = 0.60

# Similarity required to consider a memory a duplicate
MEMORY_DUPLICATE_THRESHOLD = 0.90


# ==========================================
# INITIALIZE DATABASE
# ==========================================

initialize_database()


# ==========================================
# SYSTEM MESSAGE
# ==========================================

SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "You are Jarvis, a helpful personal AI assistant. "

        "Give short, natural and useful answers because "
        "your responses may be spoken aloud. "

        "Use relevant long-term memories when provided. "

        "Never invent personal information. "

        "Never claim something is a memory unless it appears "
        "in the provided memory context. "

        "Do not ask unnecessary follow-up questions. "

        "Never output role names such as 'assistant' or 'user'. "

        "Do not claim to have real-time information unless "
        "a tool provides it. "

        "When answering from a remembered personal fact, "
        "state the fact directly and naturally. "

        "Do not repeatedly mention that you remembered it. "

        "Avoid phrases like 'you mentioned it earlier', "
        "'Python again', 'I remember', or 'as you said before' "
        "unless the user specifically asks about memory. "
    )
}


# ==========================================
# LOAD CONVERSATION MEMORY
# ==========================================

def load_memory():

    if not os.path.exists(MEMORY_FILE):

        return [
            SYSTEM_MESSAGE.copy()
        ]

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)


        if not isinstance(data, list):

            return [
                SYSTEM_MESSAGE.copy()
            ]


        cleaned = []


        for message in data:

            if not isinstance(
                message,
                dict
            ):
                continue


            role = message.get("role")
            content = message.get("content")


            if role not in [
                "system",
                "user",
                "assistant"
            ]:
                continue


            if not isinstance(
                content,
                str
            ):
                continue


            content = content.strip()


            if not content:
                continue


            cleaned.append({
                "role": role,
                "content": content
            })


        # ----------------------------------
        # Make sure system message exists
        # ----------------------------------

        if (
            not cleaned
            or cleaned[0]["role"] != "system"
        ):

            cleaned.insert(
                0,
                SYSTEM_MESSAGE.copy()
            )


        return cleaned


    except (
        json.JSONDecodeError,
        OSError
    ) as e:

        print(
            "Conversation memory load error:",
            e
        )

        return [
            SYSTEM_MESSAGE.copy()
        ]


# ==========================================
# CONVERSATION
# ==========================================

conversation = load_memory()


# ==========================================
# SAVE CONVERSATION
# ==========================================

def save_conversation():

    try:

        with open(
            MEMORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                conversation,
                file,
                indent=4,
                ensure_ascii=False
            )


    except OSError as e:

        print(
            "Conversation save error:",
            e
        )


# ==========================================
# QUESTION DETECTION
# ==========================================

def is_question(command):

    command_lower = (
        command
        .lower()
        .strip()
    )


    # --------------------------------------
    # Question mark
    # --------------------------------------

    if command_lower.endswith("?"):

        return True


    # --------------------------------------
    # Common question starters
    # --------------------------------------

    question_starters = (
        "what ",
        "what's ",
        "who ",
        "where ",
        "when ",
        "why ",
        "how ",
        "which ",
        "do i ",
        "does ",
        "did ",
        "can you ",
        "could you ",
        "would you ",
        "tell me ",
        "is ",
        "are ",
        "am i ",
        "have i ",
        "will i "
    )


    if command_lower.startswith(
        question_starters
    ):

        return True


    return False


# ==========================================
# MEMORY CONTENT VALIDATION
# ==========================================

def is_valid_memory_content(content):

    if not isinstance(
        content,
        str
    ):

        return False


    content = content.strip()


    if not content:

        return False


    # --------------------------------------
    # Reject extremely short memories
    # --------------------------------------

    words = content.split()


    if len(words) < 3:

        print(
            "Memory skipped: "
            "extracted memory is too short."
        )

        return False


    # --------------------------------------
    # Reject obvious placeholders
    # --------------------------------------

    invalid_values = {
        "python",
        "javascript",
        "java",
        "c++",
        "jarvis",
        "dark mode",
        "yes",
        "no",
        "coding",
        "programming"
    }


    if content.lower() in invalid_values:

        print(
            "Memory skipped: "
            "extracted value is not a complete fact."
        )

        return False


    return True


# ==========================================
# EXTRACT LONG-TERM MEMORY
# ==========================================

def extract_memory(command):

    try:

        # ----------------------------------
        # Never store questions
        # ----------------------------------

        if is_question(command):

            print(
                "Memory skipped: user asked a question."
            )

            return None


        # ----------------------------------
        # Memory extraction prompt
        # ----------------------------------

        prompt = f"""
You are Jarvis's long-term memory manager.

Analyze ONLY the user's message.

USER MESSAGE:
{command}

Your task is to determine whether the user explicitly
provided a useful personal fact that should be remembered.

IMPORTANT RULES:

1. A question is NOT a memory.

2. Do NOT guess.

3. Do NOT infer.

4. Do NOT answer the user's question.

5. Only save information explicitly stated by the user.

6. The memory must be a COMPLETE self-contained sentence.

7. NEVER reduce a personal fact to only a name,
   word, technology, language, place, or object.

8. Never return only:
   "Python"
   "Jarvis"
   "Dark mode"
   "India"
   "Coding"

GOOD EXAMPLES:

User:
"My favorite programming language is Python."

Correct:
"My favorite programming language is Python."

User:
"I am building a personal AI assistant called Jarvis."

Correct:
"I am building a personal AI assistant called Jarvis."

User:
"I know Python and JavaScript."

Correct:
"I know Python and JavaScript."

User:
"I want to become an AI engineer."

Correct:
"I want to become an AI engineer."

User:
"I prefer dark mode."

Correct:
"I prefer dark mode."

BAD EXAMPLES:

User:
"What programming language do I prefer?"

Do NOT save it.

User:
"What is my name?"

Do NOT save it.

User:
"What is artificial intelligence?"

Do NOT save it.

User:
"Tell me about Python."

Do NOT save it.

User:
"What's the latest news?"

Do NOT save it.

Return ONLY valid JSON.

If the user explicitly provided a useful personal fact:

{{
    "remember": true,
    "content": "complete self-contained factual statement",
    "category": "preference"
}}

Otherwise:

{{
    "remember": false,
    "content": "",
    "category": ""
}}

Never invent information.
Never answer the user.
Never use markdown.
"""


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


        raw_response = response[
            "message"
        ][
            "content"
        ].strip()


        print(
            "Memory AI response:",
            raw_response
        )


        # ----------------------------------
        # Parse JSON
        # ----------------------------------

        data = json.loads(
            raw_response
        )


        # ----------------------------------
        # Reject empty response
        # ----------------------------------

        if not data:

            print(
                "Memory skipped: "
                "empty AI response."
            )

            return None


        # ----------------------------------
        # Check remember flag
        # ----------------------------------

        if data.get(
            "remember"
        ) is not True:

            return None


        # ----------------------------------
        # Get memory content
        # ----------------------------------

        content = data.get(
            "content"
        )


        category = data.get(
            "category"
        )


        # ----------------------------------
        # Validate content
        # ----------------------------------

        if not is_valid_memory_content(
            content
        ):

            return None


        content = content.strip()


        # ----------------------------------
        # Validate category
        # ----------------------------------

        if not isinstance(
            category,
            str
        ):

            category = "general"


        category = category.strip()


        if not category:

            category = "general"


        # ----------------------------------
        # Check for duplicate semantic memory
        # ----------------------------------

        existing = semantic_search(
            content,
            limit=1,
            threshold=MEMORY_DUPLICATE_THRESHOLD
        )


        if existing:

            existing_content = existing[0].get(
                "content"
            )


            print(
                "Memory skipped: "
                "similar memory already exists."
            )


            if existing_content:

                return existing_content


            return None


        # ----------------------------------
        # Save memory
        # ----------------------------------

        memory_id = save_memory(
            content,
            category
        )


        if memory_id is not None:

            print(
                f"Memory saved [{memory_id}]: "
                f"{content}"
            )

            return content


        return None


    except json.JSONDecodeError as e:

        print(
            "Memory JSON error:",
            e
        )

        return None


    except Exception as e:

        print(
            "Memory extraction error:",
            e
        )

        return None


# ==========================================
# SEMANTIC MEMORY RETRIEVAL
# ==========================================

def get_relevant_memories(command):

    try:

        results = semantic_search(
            command,
            limit=5,
            threshold=MEMORY_SEARCH_THRESHOLD
        )


        memories = []


        for result in results:

            content = result.get(
                "content"
            )


            similarity = result.get(
                "similarity",
                0
            )


            if not content:

                continue


            # ----------------------------------
            # Avoid duplicate results
            # ----------------------------------

            if content in memories:

                continue


            memories.append(
                content
            )


            print(
                f"Memory match "
                f"({similarity:.3f}): "
                f"{content}"
            )


        return memories


    except Exception as e:

        print(
            "Semantic memory error:",
            e
        )

        return []


# ==========================================
# BUILD MEMORY CONTEXT
# ==========================================

def build_memory_context(
    memories
):

    if not memories:

        return (
            "No relevant long-term memories "
            "were found."
        )


    return (
        "Relevant long-term memories:\n"
        +
        "\n".join(
            f"- {memory}"
            for memory in memories
        )
    )


# ==========================================
# BUILD CURRENT CONTEXT
# ==========================================

def build_context_text(
    current_context
):

    return f"""
Current Jarvis context:

Last city:
{current_context.get("last_city")}

Last topic:
{current_context.get("last_topic")}

Last song:
{current_context.get("last_song")}

Last website:
{current_context.get("last_website")}
"""


# ==========================================
# LIMIT CONVERSATION HISTORY
# ==========================================

def limit_conversation():

    global conversation


    if len(conversation) <= (
        MAX_CONVERSATION_MESSAGES + 1
    ):

        return


    system_message = conversation[0]


    recent_messages = conversation[
        -MAX_CONVERSATION_MESSAGES:
    ]


    conversation = [
        system_message
    ] + recent_messages


# ==========================================
# AI PROCESS
# ==========================================

def aiProcess(command):

    try:

        # ==================================
        # 1. UPDATE SHORT-TERM CONTEXT
        # ==================================

        update_context(
            command
        )


        current_context = get_context()


        print(
            "Current context:",
            current_context
        )


        # ==================================
        # 2. EXTRACT LONG-TERM MEMORY
        # ==================================

        extract_memory(
            command
        )


        # ==================================
        # 3. SEARCH SEMANTIC MEMORY
        # ==================================

        relevant_memories = (
            get_relevant_memories(
                command
            )
        )


        if relevant_memories:

            print(
                "Relevant memories:",
                relevant_memories
            )


        # ==================================
        # 4. ADD USER MESSAGE
        # ==================================

        conversation.append({
            "role": "user",
            "content": command
        })


        # ==================================
        # 5. BUILD CONTEXT
        # ==================================

        context_text = (
            build_context_text(
                current_context
            )
        )


        memory_text = (
            build_memory_context(
                relevant_memories
            )
        )


        # ==================================
        # 6. BUILD OLLAMA MESSAGES
        # ==================================

        messages = [

            SYSTEM_MESSAGE,

            {
                "role": "system",
                "content": (
                    context_text
                    +
                    "\n"
                    +
                    memory_text
                    +
                    "\n\n"
                    +
                    "Use long-term memories only when "
                    "they are relevant to the current "
                    "user request. "
                    +
                    "Do not invent or modify memories."
                )
            }

        ]


        # ----------------------------------
        # Add conversation history
        # ----------------------------------

        if len(conversation) > 1:

            messages.extend(
                conversation[1:]
            )


        # ==================================
        # 7. ASK LOCAL AI
        # ==================================

        response = ollama.chat(
            model=MODEL,
            messages=messages
        )


        # ==================================
        # 8. EXTRACT RESPONSE
        # ==================================

        answer = response[
            "message"
        ][
            "content"
        ].strip()


        # ==================================
        # 9. CLEAN RESPONSE
        # ==================================

        # Remove "assistant"
        if answer.lower().startswith(
            "assistant"
        ):

            answer = answer[
                len("assistant"):
            ].strip()


        # Remove "assistant:"
        if answer.lower().startswith(
            "assistant:"
        ):

            answer = answer[
                len("assistant:"):
            ].strip()


        # Remove "Jarvis:"
        if answer.lower().startswith(
            "jarvis:"
        ):

            answer = answer[
                len("jarvis:"):
            ].strip()


        # ----------------------------------
        # Remove accidental role labels
        # ----------------------------------

        answer = answer.replace(
            "\nassistant\n",
            "\n"
        )

        answer = answer.replace(
            "\nAssistant:\n",
            "\n"
        )

        answer = answer.replace(
            "\nJarvis:\n",
            "\n"
        )


        # ==================================
        # 10. FALLBACK
        # ==================================

        if not answer:

            answer = (
                "Sorry, I couldn't generate "
                "a response."
            )


        # ==================================
        # 11. SAVE ASSISTANT RESPONSE
        # ==================================

        conversation.append({
            "role": "assistant",
            "content": answer
        })


        # ==================================
        # 12. LIMIT HISTORY
        # ==================================

        limit_conversation()


        # ==================================
        # 13. SAVE CONVERSATION
        # ==================================

        save_conversation()


        return answer


    except Exception as e:

        print(
            "Ollama Error:",
            e
        )


        return (
            "Sorry, I could not connect "
            "to my local AI."
        )


# ==========================================
# CLEAR CONVERSATION MEMORY
# ==========================================

def clear_memory():

    global conversation


    conversation = [
        SYSTEM_MESSAGE.copy()
    ]


    save_conversation()


    print(
        "Conversation memory cleared."
    )


# ==========================================
# STANDALONE TEST
# ==========================================

if __name__ == "__main__":

    print(
        "==================================="
    )

    print(
        "       JARVIS AI IS READY"
    )

    print(
        "==================================="
    )

    print(
        f"Model: {MODEL}"
    )

    print(
        f"Memory: {MEMORY_FILE}"
    )

    print()


    while True:

        try:

            command = input(
                "You: "
            ).strip()


            # ----------------------------------
            # Ignore empty input
            # ----------------------------------

            if not command:

                continue


            # ----------------------------------
            # Exit
            # ----------------------------------

            if command.lower() in [
                "exit",
                "quit",
                "stop"
            ]:

                print(
                    "Jarvis: Goodbye."
                )

                break


            # ----------------------------------
            # Clear conversation
            # ----------------------------------

            if command.lower() in [
                "clear memory",
                "reset memory"
            ]:

                clear_memory()

                continue


            # ----------------------------------
            # Process command
            # ----------------------------------

            response = aiProcess(
                command
            )


            print(
                "Jarvis:",
                response
            )

            print()


        except KeyboardInterrupt:

            print(
                "\nJarvis: Goodbye."
            )

            break


        except Exception as e:

            print(
                "Error:",
                e
            )