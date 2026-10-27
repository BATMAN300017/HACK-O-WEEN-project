import html
import re

# Prompt injection markers / attempts in transaction metadata
SUSPICIOUS_PATTERNS = [
    r"ignore previous instructions",
    r"system prompt",
    r"as an ai model",
    r"<script.*?>",
    r"javascript:",
    r"union select",
    r"--",
]

def sanitize_text(text: str) -> str:
    if not text:
        return ""
    clean = html.escape(text.strip())
    return clean

def detect_untrusted_prompt_injection(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return True
    return False

def sanitize_for_prompt(text: str) -> str:
    if not text:
        return ""
    # Strip dangerous tokens and wrap safely
    cleaned = re.sub(r"[\r\n\t]+", " ", text)
    cleaned = re.sub(r"[^\w\s\-\.\,\@\:\/]", "", cleaned)
    return cleaned[:500]
