"""Security layer: prompt sanitization, PII redaction, and the Policy Server.

These modules implement the course's Day-4 security concepts (7-pillar architecture,
Context Hygiene, Zero-Trust gating, the Vibe Diff). They are plain, deterministic
Python so they can be unit-tested without an LLM in the loop.
"""

from app.security.sanitize import (
    RedactionResult,
    SanitizationResult,
    redact_pii,
    sanitize_receipt_text,
)

__all__ = [
    "RedactionResult",
    "SanitizationResult",
    "redact_pii",
    "sanitize_receipt_text",
]
