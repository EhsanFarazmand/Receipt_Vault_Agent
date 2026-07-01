"""Context hygiene: PII redaction + prompt-injection sanitization.

Receipts are BOTH untrusted input and financial PII, so two independent controls
run before OCR text ever reaches a hosted model (course: *Context Hygiene & Prompt
Sanitization*, Day 5; *7-Pillar Security*, Day 4):

1. ``redact_pii``            — masks card numbers / full street addresses (Data pillar).
2. ``sanitize_receipt_text`` — neutralizes instruction-like content so a malicious
                               "receipt" cannot hijack the agent (the *Confused
                               Deputy* problem). Receipt text is treated as DATA,
                               never as instructions.

Both are pure functions returning a result object with the cleaned text plus a list
of events, which the audit log records (Observability pillar).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# 1. PII redaction
# ---------------------------------------------------------------------------

# 13–16 digit card numbers, optionally split by spaces/dashes. We keep only the
# last 4 (the ledger stores "last4" for matching, never the full PAN).
_CARD_RE = re.compile(r"\b(?:\d[ -]?){12,15}\d\b")

# US-style street address lines: "1234 Main Street", "22 Oak Ave, Apt 5".
_STREET_RE = re.compile(
    r"\b\d{1,6}\s+(?:[A-Za-z0-9.'-]+\s){0,3}"
    r"(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Lane|Ln|Drive|Dr|Court|Ct|Way|"
    r"Place|Pl|Terrace|Ter|Circle|Cir)\b\.?",
    re.IGNORECASE,
)

# Bare email addresses (redacted from the model's view; the merchant domain the
# Policy Server needs is derived from structured fields, not from free text).
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


@dataclass
class RedactionResult:
    """Outcome of a PII redaction pass."""

    text: str
    events: list[str] = field(default_factory=list)

    @property
    def redacted(self) -> bool:
        return bool(self.events)


def _mask_card(match: re.Match[str]) -> str:
    digits = re.sub(r"\D", "", match.group(0))
    last4 = digits[-4:]
    return f"[CARD ****{last4}]"


def redact_pii(text: str) -> RedactionResult:
    """Mask card numbers, street addresses, and emails in raw receipt text.

    Card numbers collapse to ``[CARD ****1234]`` so the ledger can still key on the
    last four without ever seeing the full number. Returns the masked text and a
    list of human-readable events for the audit log.
    """
    events: list[str] = []

    def _card_sub(m: re.Match[str]) -> str:
        events.append("redacted_card_number")
        return _mask_card(m)

    def _street_sub(m: re.Match[str]) -> str:
        events.append("redacted_street_address")
        return "[ADDRESS REDACTED]"

    def _email_sub(m: re.Match[str]) -> str:
        events.append("redacted_email")
        return "[EMAIL REDACTED]"

    out = _CARD_RE.sub(_card_sub, text)
    out = _STREET_RE.sub(_street_sub, out)
    out = _EMAIL_RE.sub(_email_sub, out)
    return RedactionResult(text=out, events=events)


# ---------------------------------------------------------------------------
# 2. Prompt-injection sanitization
# ---------------------------------------------------------------------------

# Phrases that only make sense as *instructions to an agent* — they have no place
# in a genuine receipt. We flag and defang them rather than delete silently, so the
# audit log can record the attempted injection.
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(?:all\s+)?(?:prior|previous|above|earlier)\s+instructions", re.I),
    re.compile(r"disregard\s+(?:all\s+)?(?:prior|previous|above)\s+(?:instructions|context)", re.I),
    re.compile(r"forget\s+(?:everything|all)\s+(?:above|before|prior)", re.I),
    re.compile(r"you\s+are\s+now\s+(?:a|an)\b", re.I),
    re.compile(r"new\s+(?:system\s+)?(?:instructions?|prompt)\s*:", re.I),
    re.compile(r"\bsystem\s+prompt\b", re.I),
    re.compile(r"(?:send|email|forward|export|upload|leak)\s+(?:the\s+)?(?:ledger|database|"
               r"all\s+data|everything|receipts?)\b", re.I),
    re.compile(r"</?(?:system|assistant|instructions?)>", re.I),
]


@dataclass
class SanitizationResult:
    """Outcome of the combined redaction + injection-defense pass."""

    text: str
    pii_events: list[str] = field(default_factory=list)
    injection_events: list[str] = field(default_factory=list)

    @property
    def flagged(self) -> bool:
        """True if anything was redacted or an injection attempt was neutralized."""
        return bool(self.pii_events or self.injection_events)

    def audit_events(self) -> list[str]:
        """Flat list of event tags for the append-only audit log."""
        return [*self.pii_events, *self.injection_events]


def sanitize_receipt_text(text: str) -> SanitizationResult:
    """Full context-hygiene pass over untrusted OCR text.

    Runs PII redaction, then neutralizes any instruction-like content by wrapping
    it so the model reads it as inert data. The extraction agent is additionally
    instructed to treat all receipt text as data — this is the defense-in-depth
    "belt and suspenders" the course recommends.

    Returns the cleaned text plus separated PII / injection event lists.
    """
    redaction = redact_pii(text)
    out = redaction.text
    injection_events: list[str] = []

    for pattern in _INJECTION_PATTERNS:
        def _sub(m: re.Match[str]) -> str:
            injection_events.append("neutralized_prompt_injection")
            # Defang, don't delete: keep the text visible (as data) but strip its
            # power to be read as an instruction.
            return f"[SANITIZED:{m.group(0)}]"

        out = pattern.sub(_sub, out)

    return SanitizationResult(
        text=out,
        pii_events=redaction.events,
        injection_events=injection_events,
    )
