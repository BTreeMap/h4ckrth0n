import re
from h4ckath0n.obs.redaction import redact_headers, redact_value, make_redactor

def test_redact_headers():
    headers = {
        "Authorization": "Bearer secret",
        "X-API-Key": "sk-12345678901234567890",
        "Cookie": "session=abc",
        "Set-Cookie": "session=abc",
        "Content-Type": "application/json",
        "User-Agent": "test-agent"
    }
    redacted = redact_headers(headers)

    assert redacted["Authorization"] == "[REDACTED]"
    assert redacted["X-API-Key"] == "[REDACTED]"
    assert redacted["Cookie"] == "[REDACTED]"
    assert redacted["Set-Cookie"] == "[REDACTED]"
    assert redacted["Content-Type"] == "application/json"
    assert redacted["User-Agent"] == "test-agent"

    # Test case insensitivity
    headers_lower = {
        "authorization": "Bearer secret",
        "x-api-key": "sk-12345678901234567890"
    }
    redacted_lower = redact_headers(headers_lower)
    assert redacted_lower["authorization"] == "[REDACTED]"
    assert redacted_lower["x-api-key"] == "[REDACTED]"

def test_redact_headers_empty():
    assert redact_headers({}) == {}

def test_redact_value():
    # JWT-like (short version that matches current pattern)
    jwt_short = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
    assert redact_value(jwt_short) == "[REDACTED]"

    # OpenAI key
    openai_key = "sk-abcdefghijklmnopqrstuvwxyz"
    assert redact_value(openai_key) == "[REDACTED]"

    # LangSmith key
    langsmith_key = "lsv2_pt_abcdefghijklmnopqrstuvwxyz"
    assert redact_value(langsmith_key) == "[REDACTED]"

    # Non-sensitive
    assert redact_value("hello world") == "hello world"

    # Multiple secrets
    mixed = f"Here is a JWT: {jwt_short} and an OpenAI key: {openai_key}"
    assert redact_value(mixed) == "Here is a JWT: [REDACTED] and an OpenAI key: [REDACTED]"

def test_make_redactor():
    redact = make_redactor()
    openai_key = "sk-abcdefghijklmnopqrstuvwxyz"
    assert redact(openai_key) == "[REDACTED]"

    # Extra patterns
    custom_pattern = re.compile(r"CUSTOM-[0-9]+")
    redact_custom = make_redactor(extra_patterns=[custom_pattern])
    assert redact_custom("CUSTOM-123") == "[REDACTED]"
    assert redact_custom(openai_key) == "[REDACTED]" # Should still have defaults
