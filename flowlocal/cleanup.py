"""Transcript cleanup: local LLM via Ollama when available, regex fallback otherwise."""

import json
import re
import urllib.error
import urllib.request

_FILLERS = re.compile(
    r"\b(um+|uh+|uhm+|erm+|hmm+|you know,?|i mean,?|like,)\s*", re.IGNORECASE
)

# App name -> tone hint for the LLM
_APP_TONES = {
    "slack": "casual and friendly",
    "discord": "casual and friendly",
    "messages": "casual, texting style",
    "mail": "professional email tone",
    "outlook": "professional email tone",
    "code": "technical; keep identifiers, commands, and code terms verbatim",
    "cursor": "technical; keep identifiers, commands, and code terms verbatim",
    "terminal": "technical; keep identifiers, commands, and code terms verbatim",
    "iterm": "technical; keep identifiers, commands, and code terms verbatim",
    "xcode": "technical; keep identifiers, commands, and code terms verbatim",
    "visual studio": "technical; keep identifiers, commands, and code terms verbatim",
    "powershell": "technical; keep identifiers, commands, and code terms verbatim",
    "teams": "professional but conversational",
}

_SYSTEM_PROMPT = """You clean up voice-dictation transcripts. Rules:
- Remove filler words (um, uh, like, you know) and false starts.
- Fix punctuation and capitalization.
- If the speaker corrects themselves ("no wait, actually X"), keep only the correction.
- Keep every other word exactly as spoken. Never reword, reorder, swap pronouns, answer questions, or add anything.
- Output ONLY the cleaned text."""

# Few-shot pairs keep small local models on-script.
_EXAMPLES = [
    ("um so I think we should uh meet on Monday no wait actually Tuesday",
     "I think we should meet on Tuesday."),
    ("hey can you um send me the the report when you get a chance",
     "Hey, can you send me the report when you get a chance?"),
    ("what time is it",
     "What time is it?"),
]


def fallback_clean(text: str) -> str:
    """Cheap regex cleanup used when no LLM is reachable."""
    text = _FILLERS.sub("", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


def _tone_for_app(app_name: str | None) -> str | None:
    if not app_name:
        return None
    lowered = app_name.lower()
    for key, tone in _APP_TONES.items():
        if key in lowered:
            return tone
    return None


def llm_clean(text: str, cfg: dict, app_name: str | None = None) -> str:
    """Clean via local Ollama. Falls back to regex cleanup on any failure."""
    system = _SYSTEM_PROMPT
    if cfg.get("per_app_tone"):
        tone = _tone_for_app(app_name)
        if tone:
            system += f"\n- The text is being written in {app_name}; lean {tone}."

    messages = [{"role": "system", "content": system}]
    for raw, cleaned in _EXAMPLES:
        messages.append({"role": "user", "content": raw})
        messages.append({"role": "assistant", "content": cleaned})
    messages.append({"role": "user", "content": text})

    payload = json.dumps({
        "model": cfg["ollama_model"],
        "messages": messages,
        "stream": False,
        "keep_alive": "30m",
        "options": {"temperature": 0.0},
    }).encode()

    req = urllib.request.Request(
        cfg["ollama_url"].rstrip("/") + "/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.get("timeout_s", 15)) as resp:
            body = json.loads(resp.read())
        cleaned = body["message"]["content"].strip()
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, OSError):
        return fallback_clean(text)
    # Guard against the model going off-script (empty output or an essay).
    if not cleaned or len(cleaned) > max(80, len(text) * 2):
        return fallback_clean(text)
    return cleaned


def warm_up(cfg: dict) -> None:
    """Ask Ollama to load the model into memory so the first dictation is fast."""
    payload = json.dumps({
        "model": cfg["ollama_model"], "keep_alive": "30m",
    }).encode()
    req = urllib.request.Request(
        cfg["ollama_url"].rstrip("/") + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=60).read()
    except (urllib.error.URLError, TimeoutError, OSError):
        pass  # Ollama not running; fallback cleanup will be used


def clean(text: str, cleanup_cfg: dict, app_name: str | None = None) -> str:
    if not text:
        return text
    if cleanup_cfg.get("enabled"):
        return llm_clean(text, cleanup_cfg, app_name)
    return fallback_clean(text)
