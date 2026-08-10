import sqlite3
import json
from datetime import datetime

import ollama


# ==========================================
# Configuration
# ==========================================

DATABASE_FILE = "jarvis_memory.db"

EMBEDDING_MODEL = "nomic-embed-text"


# ==========================================
# Database Connection
# ==========================================

def get_connection():

    return sqlite3.connect(
        DATABASE_FILE
    )


# ==========================================
# Initialize Database
# ==========================================

def initialize_database():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT,
            embedding TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # --------------------------------------
    # Upgrade old database
    # --------------------------------------

    cursor.execute(
        "PRAGMA table_info(memories)"
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    if "embedding" not in columns:

        cursor.execute(
            """
            ALTER TABLE memories
            ADD COLUMN embedding TEXT
            """
        )

    connection.commit()

    connection.close()


# ==========================================
# Generate Embedding
# ==========================================

def generate_embedding(text):

    try:

        response = ollama.embed(
            model=EMBEDDING_MODEL,
            input=text
        )

        embeddings = response.get(
            "embeddings"
        )

        if not embeddings:

            print(
                "Embedding API returned no embeddings."
            )

            return None

        return embeddings[0]

    except Exception as e:

        print(
            "Embedding error:",
            e
        )

        return None


# ==========================================
# Save Memory
# ==========================================

def save_memory(
    content,
    category="general"
):

    if not content:
        return None

    embedding = generate_embedding(
        content
    )

    if embedding is None:

        print(
            "Memory not saved because "
            "embedding generation failed."
        )

        return None

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO memories
        (content, category, embedding, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            content,
            category,
            json.dumps(embedding),
            datetime.now().isoformat()
        )
    )

    memory_id = cursor.lastrowid

    connection.commit()

    connection.close()

    return memory_id


# ==========================================
# Get Recent Memories
# ==========================================

def get_recent_memories(
    limit=10
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, content, category, embedding, created_at
        FROM memories
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = cursor.fetchall()

    connection.close()

    return rows


# ==========================================
# Keyword Search
# ==========================================

def search_memories(
    keyword,
    limit=10
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, content, category, embedding, created_at
        FROM memories
        WHERE content LIKE ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            f"%{keyword}%",
            limit
        )
    )

    rows = cursor.fetchall()

    connection.close()

    return rows


# ==========================================
# Cosine Similarity
# ==========================================

def cosine_similarity(
    vector_a,
    vector_b
):

    if not vector_a or not vector_b:
        return 0.0

    dot_product = sum(
        a * b
        for a, b in zip(
            vector_a,
            vector_b
        )
    )

    magnitude_a = sum(
        a * a
        for a in vector_a
    ) ** 0.5

    magnitude_b = sum(
        b * b
        for b in vector_b
    ) ** 0.5

    if (
        magnitude_a == 0
        or magnitude_b == 0
    ):
        return 0.0

    return (
        dot_product
        / (magnitude_a * magnitude_b)
    )


# ==========================================
# Semantic Memory Search
# ==========================================

def semantic_search(
    query,
    limit=5,
    threshold=0.40
):

    query_embedding = generate_embedding(
        query
    )

    if query_embedding is None:

        return []

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            content,
            category,
            embedding,
            created_at
        FROM memories
        WHERE embedding IS NOT NULL
        """
    )

    rows = cursor.fetchall()

    connection.close()

    results = []

    for row in rows:

        memory_id = row[0]

        content = row[1]

        category = row[2]

        embedding_json = row[3]

        created_at = row[4]

        try:

            memory_embedding = json.loads(
                embedding_json
            )

            similarity = cosine_similarity(
                query_embedding,
                memory_embedding
            )

            if similarity >= threshold:

                results.append({
                    "id": memory_id,
                    "content": content,
                    "category": category,
                    "similarity": similarity,
                    "created_at": created_at
                })

        except Exception as e:

            print(
                "Invalid memory embedding:",
                e
            )


    # --------------------------------------
    # Highest similarity first
    # --------------------------------------

    results.sort(
        key=lambda item: item["similarity"],
        reverse=True
    )


    return results[:limit]


# ==========================================
# Delete Memory
# ==========================================

def delete_memory(
    memory_id
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM memories
        WHERE id = ?
        """,
        (memory_id,)
    )

    deleted = cursor.rowcount

    connection.commit()

    connection.close()

    return deleted > 0


# ==========================================
# Clear All Memories
# ==========================================

def clear_all_memories():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM memories"
    )

    connection.commit()

    connection.close()


# ==========================================
# Rebuild Missing Embeddings
# ==========================================

def rebuild_embeddings():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, content
        FROM memories
        """
    )

    rows = cursor.fetchall()

    print(
        f"Memories found: {len(rows)}"
    )

    successful = 0

    for memory_id, content in rows:

        print(
            f"Generating embedding for memory {memory_id}..."
        )

        embedding = generate_embedding(
            content
        )

        if embedding:

            cursor.execute(
                """
                UPDATE memories
                SET embedding = ?
                WHERE id = ?
                """,
                (
                    json.dumps(embedding),
                    memory_id
                )
            )

            successful += 1

    connection.commit()

    connection.close()

    print(
        f"Embeddings rebuilt: {successful}/{len(rows)}"
    )


# ==========================================
# Test
# ==========================================

if __name__ == "__main__":

    initialize_database()

    print(
        "================================"
    )

    print(
        "JARVIS SEMANTIC MEMORY TEST"
    )

    print(
        "================================"
    )

    print()

    print(
        "Embedding model:",
        EMBEDDING_MODEL
    )

    print()

    rebuild_embeddings()

    print()

    query = input(
        "Search memory: "
    )

    results = semantic_search(
        query
    )

    print()

    if not results:

        print(
            "No relevant memories found."
        )

    else:

        print(
            "Relevant memories:"
        )

        for result in results:

            print()

            print(
                "Memory:",
                result["content"]
            )

            print(
                "Category:",
                result["category"]
            )

            print(
                "Similarity:",
                round(
                    result["similarity"],
                    3
                )
            )