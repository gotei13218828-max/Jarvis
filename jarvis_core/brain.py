import json
import re
import urllib.request
import urllib.error

from .personality import SYSTEM_PROMPT
from .memory.manager import get_memories
from .memory.auto_memory import extract_memory

API_URL = "http://127.0.0.1:8080/v1/chat/completions"

STOP_WORDS = {
    "what", "is", "my", "the", "a", "an", "do", "i",
    "you", "your", "me", "and", "of", "to", "in",
    "tell", "about", "please", "can", "are", "was",
    "how", "does", "did", "it", "this", "that",
    "remember", "preference", "preferences"
}


def normalize_words(text):
    return {
        word for word in re.findall(r"\w+", text.lower())
        if word not in STOP_WORDS
    }


def find_relevant_memory(message):
    query_words = normalize_words(message)

    if not query_words:
        return None

    memories = get_memories()
    scored_memories = []

    for memory in memories:
        content_words = normalize_words(
            memory.get("content", "")
        )

        if not content_words:
            continue

        overlap = query_words.intersection(content_words)
        score = len(overlap) / len(query_words)

        scored_memories.append((score, memory))

    scored_memories.sort(
        key=lambda item: item[0],
        reverse=True
    )

    if not scored_memories:
        return None

    best_score, best_memory = scored_memories[0]

    second_score = (
        scored_memories[1][0]
        if len(scored_memories) > 1
        else 0
    )

    if best_score >= 0.6 and best_score > second_score:
        return best_memory

    return None


def ask_jarvis(message):

    # 1. Process explicit memory instructions first.
    try:
        memory_updated = extract_memory(message)

        if memory_updated:
            return "Your memory has been updated successfully."
    except Exception:
        pass

    # 2. Recall relevant information.
    memory = find_relevant_memory(message)

    if memory:
        return f"I remember: {memory['content']}"

    # 3. Load saved information.
    memories = get_memories()
    memory_context = ""

    if memories:
        memory_context = "\n\nSAVED USER FACTS:\n"

        for memory in memories:
            memory_context += f"- {memory['content']}\n"

    full_system_prompt = (
        SYSTEM_PROMPT
        + memory_context
        + "\nUse saved facts when relevant. "
          "Do not invent personal information."
    )

    # 4. Prepare local AI request.
    payload = {
        "messages": [
            {
                "role": "system",
                "content": full_system_prompt
            },
            {
                "role": "user",
                "content": message
            }
        ],
        "temperature": 0.1,
        "max_tokens": 120
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    # 5. Contact local Qwen server.
    try:
        with urllib.request.urlopen(
            request,
            timeout=60
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

        return result["choices"][0]["message"]["content"].strip()

    except urllib.error.URLError as error:
        return f"Connection error: {error}"

    except (KeyError, IndexError, ValueError):
        return "I couldn't process that response."

    except TimeoutError:
        return "I'm taking too long to respond. Please try again."
