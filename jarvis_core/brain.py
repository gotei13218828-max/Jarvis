import json
import re
import urllib.request
import urllib.error

from .personality import SYSTEM_PROMPT
from .memory.manager import get_memories
from .memory.auto_memory import extract_memory
from .cloud.session import session_manager

LOCAL_API_URL = "http://127.0.0.1:8080/v1/chat/completions"
CLOUD_API_URL = "https://little-rain-cada.gotei13218828.workers.dev/chat"

STOP_WORDS = {
    "what", "is", "my", "the", "a", "an", "do", "i", "you", "your", "me",
    "and", "of", "to", "in", "tell", "about", "please", "can", "are", "was",
    "how", "does", "did", "it", "this", "that", "remember", "preference", "preferences"
}


def normalize_words(text):
    return {word for word in re.findall(r"\w+", text.lower()) if word not in STOP_WORDS}


def find_relevant_memory(message):
    query_words = normalize_words(message)
    if not query_words:
        return None
    scored = []
    for memory in get_memories():
        content_words = normalize_words(memory.get("content", ""))
        if content_words:
            overlap = query_words.intersection(content_words)
            scored.append((len(overlap) / len(query_words), memory))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored:
        return None
    best_score, best_memory = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0
    return best_memory if best_score >= 0.6 and best_score > second_score else None


def format_memory_response(memory):
    content = memory.get("content", "").strip()
    content = re.sub(r"^(remember that|from now on|going forward)\s+", "", content, flags=re.IGNORECASE)
    match = re.match(r"my favou?rite (.+?) is (.+)[.!]?$", content, flags=re.IGNORECASE)
    if match:
        return f"Your favourite {match.group(1).strip()} is {match.group(2).strip().rstrip('.!?')}."
    return f"I remember that {content}"


def _build_messages(message, history=None):
    memory_context = ""
    memories = get_memories()
    if memories:
        memory_context = "\n\nSAVED USER FACTS:\n" + "".join(f"- {item.get('content', '')}\n" for item in memories)
    system = SYSTEM_PROMPT + memory_context + "\nUse saved facts when relevant. Do not invent personal information."
    messages = [{"role": "system", "content": system}]
    if isinstance(history, list):
        for item in history[-12:]:
            if isinstance(item, dict) and item.get("role") in ("user", "assistant") and isinstance(item.get("content"), str):
                messages.append({"role": item["role"], "content": item["content"][:4000]})
    messages.append({"role": "user", "content": message})
    return messages


def _extract_text(result):
    if isinstance(result, dict):
        choices = result.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {})
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"].strip()
        for key in ("response", "output", "content"):
            if isinstance(result.get(key), str):
                return result[key].strip()
    raise ValueError("Unexpected AI response format")


def _post_json(url, payload, headers=None, timeout=30):
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=request_headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _ask_cloud(messages):
    token = session_manager.get_access_token()
    if not token:
        raise PermissionError("Sign in is required for Cloud AI")
    payload = {"messages": messages, "max_tokens": 512}
    return _extract_text(_post_json(CLOUD_API_URL, payload, {"Authorization": "Bearer " + token}, timeout=30))


def _ask_local(messages):
    payload = {"messages": messages, "temperature": 0.2, "max_tokens": 180}
    return _extract_text(_post_json(LOCAL_API_URL, payload, timeout=60))


def ask_jarvis(message, history=None):
    normalized = re.sub(r"[^a-z0-9\s]", "", message.lower()).strip()
    if re.search(r"\bwho are (you|u)\b", normalized) or normalized in {"introduce yourself", "tell me about yourself"}:
        return "I'm Jarvis, your personal AI assistant. I can use available cloud AI when you're signed in, with your phone's local model as a fallback. How can I help?"

    try:
        if extract_memory(message):
            return "Your memory has been updated successfully."
    except Exception:
        pass

    memory = find_relevant_memory(message)
    if memory:
        return format_memory_response(memory)

    messages = _build_messages(message, history)
    cloud_error = None
    if session_manager.is_authenticated:
        try:
            return _ask_cloud(messages)
        except Exception as error:
            cloud_error = error
            # Refresh the stored Supabase session once after an authorization failure.
            if isinstance(error, urllib.error.HTTPError) and error.code == 401:
                try:
                    session_manager.restore_session(saved_session=session_manager.session)
                    return _ask_cloud(messages)
                except Exception as retry_error:
                    cloud_error = retry_error

    try:
        return _ask_local(messages)
    except urllib.error.URLError:
        if cloud_error:
            return "Cloud AI is unavailable and the local AI server isn't reachable. Please check your connection and local Jarvis server."
        return "The local AI server isn't reachable. Start the Jarvis local model server and try again."
    except TimeoutError:
        return "The local AI is taking too long to respond. Please try again."
    except (KeyError, IndexError, ValueError):
        return "I couldn't process that response."
