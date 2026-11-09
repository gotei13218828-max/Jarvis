import re

from .manager import (
    save_memory,
    update_memory,
    get_memories,
)


SENSITIVE_PATTERNS = [
    r"\bpassword\b",
    r"\bpasscode\b",
    r"\botp\b",
    r"\bapi[_ -]?key\b",
    r"\bsecret key\b",
    r"\bcredit card\b",
    r"\bbank account\b",
    r"\bhome address\b",
    r"\bphone number\b",
]

MEMORY_PATTERNS = [
    r"\bmy favourite\b",
    r"\bmy favorite\b",
    r"\bi prefer\b",
    r"\bi like\b",
    r"\bi love\b",
    r"\bmy name is\b",
    r"\bi am working on\b",
    r"\bi am building\b",
    r"\bmy project is\b",
    r"\bremember that\b",
    r"\bfrom now on\b",
    r"\bgoing forward\b",
]


def is_sensitive(text):
    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in SENSITIVE_PATTERNS
    )


def normalize(text):
    return " ".join(re.findall(r"\w+", text.lower()))


def extract_memory(message):
    message = message.strip()

    if not message or len(message) > 300:
        return False

    if is_sensitive(message):
        return False

    # Detect explicit preference changes.
    match = re.fullmatch(
        r"i now prefer (.+?) instead of (.+)",
        message,
        re.IGNORECASE,
    )

    if match:
        new_preference = match.group(1).strip()
        old_preference = match.group(2).strip()

        memories = get_memories()

        old_content = normalize(
            f"I prefer {old_preference}."
        )

        candidates = [
            (index, memory)
            for index, memory in enumerate(memories)
            if normalize(memory.get("content", "")) == old_content
        ]

        # Update only when exactly one old memory matches.
        if len(candidates) != 1:
            return False

        index, old_memory = candidates[0]

        new_content = f"I prefer {new_preference}."

        # Don't create a duplicate if the new preference exists.
        for i, memory in enumerate(memories):
            if i != index and normalize(
                memory.get("content", "")
            ) == normalize(new_content):
                return False

        return update_memory(
            index,
            new_content,
            old_memory.get("category", "automatic"),
        )

    # Save new information without overwriting existing memories.
    if any(
        re.search(pattern, message, re.IGNORECASE)
        for pattern in MEMORY_PATTERNS
    ):
        return save_memory(message, category="automatic")

    return False
