from jarvis.memory import semantic_search


# ==========================================
# MEMORY SETTINGS
# ==========================================

MEMORY_LIMIT = 5

MEMORY_THRESHOLD = 0.55


# ==========================================
# SEARCH RELEVANT LONG-TERM MEMORIES
# ==========================================

def get_relevant_memories(
    query,
    limit=MEMORY_LIMIT,
    threshold=MEMORY_THRESHOLD
):

    if not query:
        return []


    try:

        results = semantic_search(
            query,
            limit=limit,
            threshold=threshold
        )


        memories = []


        for result in results:

            memories.append({

                "id": result.get(
                    "id"
                ),

                "content": result.get(
                    "content"
                ),

                "category": result.get(
                    "category"
                ),

                "similarity": result.get(
                    "similarity"
                )
            })


        return memories


    except Exception as e:

        print(
            "Memory search error:",
            e
        )

        return []


# ==========================================
# FORMAT MEMORIES FOR LLM
# ==========================================

def format_memories(
    memories
):

    if not memories:

        return (
            "No relevant long-term "
            "memories were found."
        )


    lines = []


    for memory in memories:

        content = memory.get(
            "content"
        )

        category = memory.get(
            "category"
        )


        if not content:

            continue


        if category:

            lines.append(
                f"- {content} "
                f"(category: {category})"
            )

        else:

            lines.append(
                f"- {content}"
            )


    if not lines:

        return (
            "No relevant long-term "
            "memories were found."
        )


    return "\n".join(
        lines
    )


# ==========================================
# BUILD MEMORY CONTEXT
# ==========================================

def build_memory_context(
    query
):

    memories = get_relevant_memories(
        query
    )


    return {
        "memories": memories,

        "formatted": format_memories(
            memories
        )
    }


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print(
        "================================"
    )

    print(
        "JARVIS MEMORY CONTEXT TEST"
    )

    print(
        "================================"
    )


    query = input(
        "Query: "
    )


    result = build_memory_context(
        query
    )


    print()

    print(
        "Relevant memories:"
    )

    print(
        result["formatted"]
    )