"""Reputation / risk assessment.

assess() is an OFFLINE HEURISTIC. It does not know whether a specific number
belongs to a scammer; it flags structural risk signals (premium rate, invalid,
VoIP/disposable patterns) the way a spam filter weighs features. Clearly a
heuristic, never a definitive verdict, and it reveals nothing about an owner.

Optional live integrations (carrier enrichment + fraud-database scoring) are
provided by a private module that is NOT part of this public repository. When it
is absent, live_lookup()/spam_lookup() are offline no-ops returning None, so the
tool runs fully from the bundled libphonenumber dataset.
"""
from __future__ import annotations

from typing import Optional


RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "UNKNOWN": 3}


def assess(intel) -> dict:
    """Heuristic structural-risk assessment for an Intel result.

    Returns {level, score (0-100), reasons[], source}. Higher score = more
    caution warranted. This is advisory, not a spam-database verdict.
    """
    reasons = []
    score = 0

    if not intel.ok:
        return {"level": "UNKNOWN", "score": 0,
                "reasons": ["Number could not be parsed."], "source": "heuristic"}

    if not intel.valid:
        score += 40
        reasons.append("Fails validation for its country numbering plan.")

    code = intel.line_type_code or "UNKNOWN"
    if code == "PREMIUM_RATE":
        score += 70
        reasons.append("Premium-rate line — frequently abused for billing scams.")
    elif code == "SHARED_COST":
        score += 30
        reasons.append("Shared-cost line — treat unsolicited contact with caution.")
    elif code == "VOIP":
        score += 25
        reasons.append("VoIP line — cheap/disposable, common for spam & spoofing.")
    elif code == "PERSONAL":
        score += 15
        reasons.append("Personal-number service — can mask the real line.")
    elif code in ("TOLL_FREE",):
        reasons.append("Toll-free line — typically a business/support number.")

    if code in ("MOBILE", "FIXED_OR_MOBILE") and not intel.carrier:
        score += 10
        reasons.append("No carrier resolved — number may be ported or very new.")

    if not reasons:
        reasons.append("No structural risk signals detected.")

    score = max(0, min(100, score))
    if score >= 60:
        level = "HIGH"
    elif score >= 25:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {"level": level, "score": score, "reasons": reasons, "source": "heuristic"}


# Optional live integrations live in a private, git-ignored module so the
# paid-API wiring stays out of the public repo. Absent -> offline no-ops.
try:
    from ._live_private import live_lookup, spam_lookup  # type: ignore
except ImportError:  # public/offline build
    def live_lookup(e164: str) -> Optional[dict]:
        """Offline build — live carrier enrichment is unavailable."""
        return None

    def spam_lookup(e164: str) -> Optional[dict]:
        """Offline build — live fraud lookup is unavailable."""
        return None
