import json
import re
import shutil
from pathlib import Path
from datetime import datetime

BUNDLED_MEMORY_FILE = Path(__file__).parent / "memories.json"


def get_memory_file():
    try:
        from kivy.app import App

        app = App.get_running_app()

        if app is not None:
            android_memory_file = (
                Path(app.user_data_dir) / "memories.json"
            )

            if not android_memory_file.exists():
                android_memory_file.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                if BUNDLED_MEMORY_FILE.exists():
                    shutil.copy2(
                        BUNDLED_MEMORY_FILE,
                        android_memory_file
                    )

            return android_memory_file

    except Exception:
        pass

    return BUNDLED_MEMORY_FILE


def load_memories():
    memory_file = get_memory_file()

    if not memory_file.exists():
        return []

    try:
        with open(memory_file, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, OSError):
        return []


def save_all_memories(memories):
    memory_file = get_memory_file()
    memory_file.parent.mkdir(parents=True, exist_ok=True)

    temp_file = memory_file.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(
            memories,
            file,
            indent=4,
            ensure_ascii=False
        )

    temp_file.replace(memory_file)


def normalize(text):
    return " ".join(re.findall(r"\w+", text.lower()))


def save_memory(content, category="general"):
    content = content.strip()

    if not content:
        return False

    memories = load_memories()
    normalized = normalize(content)

    for memory in memories:
        if normalize(memory.get("content", "")) == normalized:
            return False

    memories.append({
        "content": content,
        "category": category,
        "created_at": datetime.now().isoformat()
    })

    save_all_memories(memories)
    return True


def update_memory(index, new_content, category=None):
    memories = load_memories()
    new_content = new_content.strip()

    if not new_content:
        return False

    if not 0 <= index < len(memories):
        return False

    normalized = normalize(new_content)

    for i, memory in enumerate(memories):
        if i != index and normalize(
            memory.get("content", "")
        ) == normalized:
            return False

    old_memory = memories[index]

    memories[index] = {
        "content": new_content,
        "category": category or old_memory.get(
            "category",
            "general"
        ),
        "created_at": datetime.now().isoformat()
    }

    save_all_memories(memories)
    return True


def get_memories():
    return load_memories()


def search_memories(query):
    memories = load_memories()
    query_words = set(normalize(query).split())

    if not query_words:
        return []

    results = []

    for memory in memories:
        content_words = set(
            normalize(memory.get("content", "")).split()
        )

        if len(query_words.intersection(content_words)) >= 2:
            results.append(memory)

    return results


def delete_memory(index):
    memories = load_memories()

    if 0 <= index < len(memories):
        memories.pop(index)
        save_all_memories(memories)
        return True

    return False
