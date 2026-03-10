"""
Multi-label content classifier.

Two-tier approach:
1. **Fast regex/keyword tier** — catches obvious violations in < 1 ms.
   Uses curated pattern banks per category with word-boundary matching
   so that benign words like "assassin's creed" don't false-positive.
2. **LLM tier (optional)** — for nuanced / borderline content.  Disabled
   by default; enabled via ``GuardrailConfig.llm_classification``.

The classifier is stateless and thread-safe.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from versaai.safety.types import ContentCategory, SafetyVerdict, ThreatLevel, SafetyAction

logger = logging.getLogger(__name__)


# ============================================================================
# Pattern bank — curated per category
# ============================================================================

# Each entry is (compiled_regex, weight).  Weight ∈ [0.0, 1.0] controls how
# much a single match contributes to the score.  The accumulated per-category
# score is clamped to [0, 1] and compared against the threshold.

@dataclass(frozen=True)
class _PatternEntry:
    pattern: re.Pattern[str]
    weight: float


def _compile(raw: str, weight: float = 0.5) -> _PatternEntry:
    return _PatternEntry(re.compile(raw, re.IGNORECASE), weight)


# Maps ContentCategory → list of (regex, weight).
# Patterns use word boundaries (\b) to avoid false positives.
_PATTERN_BANKS: Dict[ContentCategory, List[_PatternEntry]] = {
    ContentCategory.TOXIC: [
        _compile(r"\b(?:fuck\s*(?:you|off|ing)?|shit|bitch|asshole|cunt|dick(?:head)?)\b", 0.6),
        _compile(r"\b(?:stfu|gtfo|pos|mofo)\b", 0.4),
        _compile(r"\b(?:go\s+die|kill\s+yourself|kys)\b", 0.9),
    ],
    ContentCategory.HATE_SPEECH: [
        _compile(
            r"\b(?:n[i1]gg(?:er|a)|k[i1]ke|sp[i1]c|ch[i1]nk|wet\s*back|"
            r"f[a@]gg?(?:ot)?|tr[a@]nn(?:y|ie)|ret[a@]rd)\b",
            0.9,
        ),
        _compile(r"\b(?:white\s+supremacy|ethnic\s+cleansing|race\s+war)\b", 0.7),
        _compile(r"\b(?:gas\s+the|exterminate\s+(?:all|the))\b", 0.95),
    ],
    ContentCategory.VIOLENCE: [
        _compile(r"\b(?:how\s+to\s+(?:make\s+a\s+)?(?:bomb|explosive|weapon|poison))\b", 0.85),
        _compile(r"\b(?:kill\s+(?:all|every|them)|mass\s+shooting|school\s+shoot)\b", 0.9),
        _compile(r"\b(?:torture|mutilat|dismember|behead)\b", 0.6),
    ],
    ContentCategory.SELF_HARM: [
        _compile(r"\b(?:how\s+to\s+(?:kill|harm|hurt)\s+(?:my|your)?self)\b", 0.9),
        _compile(r"\b(?:suicide\s+method|painless\s+(?:death|way\s+to\s+die))\b", 0.9),
        _compile(r"\b(?:cut(?:ting)?\s+(?:my|your)\s+wrist|self[\s\-]?harm)\b", 0.7),
    ],
    ContentCategory.SEXUAL: [
        _compile(r"\b(?:explicit\s+sex(?:ual)?|porn(?:ograph)?|hentai)\b", 0.5),
        _compile(r"\b(?:write\s+(?:me\s+)?(?:erotic|sexual|porn))\b", 0.7),
    ],
    ContentCategory.CHILD_SAFETY: [
        _compile(
            r"\b(?:child\s+(?:porn|sex|abuse|exploit)|cp\b|"
            r"minor\s+(?:sex|nude|naked)|pedo(?:phil)?)",
            0.99,
        ),
        _compile(r"\b(?:underage\s+(?:sex|nude|girl|boy))\b", 0.99),
    ],
    ContentCategory.ILLEGAL_ACTIVITY: [
        _compile(r"\b(?:how\s+to\s+(?:hack|ddos|phish|crack\s+password))\b", 0.7),
        _compile(r"\b(?:how\s+to\s+(?:cook|make|synthesiz)\s+(?:meth|cocaine|heroin|fentanyl))\b", 0.9),
        _compile(r"\b(?:bypass\s+security|exploit\s+vulnerability)\b", 0.5),
        _compile(r"\b(?:credit\s+card\s+fraud|money\s+launder|identity\s+theft)\b", 0.7),
    ],
    ContentCategory.MALWARE: [
        _compile(r"\b(?:write\s+(?:me\s+)?(?:a\s+)?(?:ransomware|virus|trojan|keylogger|rootkit))\b", 0.9),
        _compile(r"\b(?:create\s+(?:a\s+)?(?:botnet|rat|backdoor|exploit))\b", 0.8),
        _compile(r"\b(?:reverse\s+shell|bind\s+shell|payload\s+generator)\b", 0.6),
    ],
    ContentCategory.DANGEROUS_CAPABILITY: [
        _compile(r"\b(?:bioweapon|biological\s+weapon|nerve\s+agent|chemical\s+weapon)\b", 0.95),
        _compile(r"\b(?:nuclear\s+(?:bomb|weapon)\s+(?:build|make|design))\b", 0.95),
        _compile(r"\b(?:autonomous\s+(?:cyber[\s\-]?attack|weapon))\b", 0.85),
    ],
    ContentCategory.DECEPTION: [
        _compile(r"\b(?:deepfake|generate\s+fake\s+(?:news|identity|document))\b", 0.7),
        _compile(r"\b(?:impersonat\w+|social\s+engineer(?:ing)?)\b", 0.5),
        _compile(r"\b(?:forge\s+(?:document|signature|passport|id))\b", 0.7),
    ],
}

# Words that, when present in context, reduce the score (academic, reporting).
_MITIGATION_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"\b(?:research|academic|study|paper|journal|thesis)\b", re.IGNORECASE),
    re.compile(r"\b(?:report(?:ing)?|news|article|documentary)\b", re.IGNORECASE),
    re.compile(r"\b(?:education|teach|learn|awareness|prevent)\b", re.IGNORECASE),
    re.compile(r"\b(?:fiction|novel|screenplay|story|narrative)\b", re.IGNORECASE),
]


# ============================================================================
# Classifier
# ============================================================================

@dataclass
class ClassifierConfig:
    """Per-category thresholds.  Score ≥ threshold → flagged."""
    thresholds: Dict[ContentCategory, float] = field(default_factory=lambda: {
        ContentCategory.TOXIC: 0.5,
        ContentCategory.HATE_SPEECH: 0.3,
        ContentCategory.VIOLENCE: 0.5,
        ContentCategory.SELF_HARM: 0.4,
        ContentCategory.SEXUAL: 0.5,
        ContentCategory.CHILD_SAFETY: 0.2,
        ContentCategory.ILLEGAL_ACTIVITY: 0.5,
        ContentCategory.MALWARE: 0.5,
        ContentCategory.DANGEROUS_CAPABILITY: 0.3,
        ContentCategory.DECEPTION: 0.6,
    })
    mitigation_discount: float = 0.3  # Score reduction for academic context


class ContentClassifier:
    """
    Stateless, thread-safe content classifier.

    Usage::

        cls = ContentClassifier()
        verdict = cls.classify("some user input")
        if not verdict.allowed:
            ...
    """

    def __init__(self, config: Optional[ClassifierConfig] = None):
        self._config = config or ClassifierConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, text: str) -> SafetyVerdict:
        """
        Classify *text* and return a ``SafetyVerdict``.

        Fast path: if the text is empty or very short (< 3 chars), it is
        always ``SAFE``.
        """
        if not text or len(text.strip()) < 3:
            return SafetyVerdict.safe()

        scores = self._score(text)
        flagged = self._apply_thresholds(scores)

        if not flagged:
            return SafetyVerdict.safe()

        # Determine worst threat level
        threat = self._threat_level(flagged, scores)
        action = self._action_for(threat)
        explanation = self._explain(flagged, scores)

        return SafetyVerdict(
            allowed=(action != SafetyAction.BLOCK),
            categories=flagged,
            threat_level=threat,
            action=action,
            explanation=explanation,
            metadata={"scores": {c.value: round(s, 3) for c, s in scores.items() if s > 0}},
        )

    def score_categories(self, text: str) -> Dict[ContentCategory, float]:
        """Return raw per-category scores (useful for debugging / dashboards)."""
        return self._score(text)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _score(self, text: str) -> Dict[ContentCategory, float]:
        scores: Dict[ContentCategory, float] = {}
        mitigation = self._mitigation_factor(text)

        for category, patterns in _PATTERN_BANKS.items():
            total = 0.0
            for entry in patterns:
                matches = entry.pattern.findall(text)
                if matches:
                    # Accumulate weight per match, but cap contribution per pattern
                    total += min(entry.weight * len(matches), entry.weight * 2)
            # Apply mitigation discount
            total = max(0.0, total - mitigation)
            scores[category] = min(total, 1.0)

        return scores

    def _mitigation_factor(self, text: str) -> float:
        """Returns a discount ∈ [0, config.mitigation_discount] for academic context."""
        hits = sum(1 for p in _MITIGATION_PATTERNS if p.search(text))
        if hits == 0:
            return 0.0
        # 1 hit → half discount, 2+ → full discount
        frac = min(hits / 2.0, 1.0)
        return frac * self._config.mitigation_discount

    def _apply_thresholds(
        self, scores: Dict[ContentCategory, float]
    ) -> List[ContentCategory]:
        flagged: List[ContentCategory] = []
        for cat, score in scores.items():
            thresh = self._config.thresholds.get(cat, 0.5)
            if score >= thresh:
                flagged.append(cat)
        return flagged

    def _threat_level(
        self,
        flagged: List[ContentCategory],
        scores: Dict[ContentCategory, float],
    ) -> ThreatLevel:
        # Critical categories always escalate
        critical = {
            ContentCategory.CHILD_SAFETY,
            ContentCategory.DANGEROUS_CAPABILITY,
        }
        if critical & set(flagged):
            return ThreatLevel.CRITICAL

        high = {
            ContentCategory.HATE_SPEECH,
            ContentCategory.SELF_HARM,
            ContentCategory.MALWARE,
        }
        if high & set(flagged):
            return ThreatLevel.HIGH

        max_score = max((scores.get(c, 0) for c in flagged), default=0)
        if max_score >= 0.8:
            return ThreatLevel.HIGH
        if max_score >= 0.5:
            return ThreatLevel.MEDIUM
        return ThreatLevel.LOW

    def _action_for(self, threat: ThreatLevel) -> SafetyAction:
        return {
            ThreatLevel.CRITICAL: SafetyAction.BLOCK,
            ThreatLevel.HIGH: SafetyAction.BLOCK,
            ThreatLevel.MEDIUM: SafetyAction.WARN,
            ThreatLevel.LOW: SafetyAction.AUDIT,
            ThreatLevel.NONE: SafetyAction.ALLOW,
        }[threat]

    def _explain(
        self,
        flagged: List[ContentCategory],
        scores: Dict[ContentCategory, float],
    ) -> str:
        parts = [
            f"{c.value} ({scores.get(c, 0):.2f})" for c in flagged
        ]
        return f"Content flagged: {', '.join(parts)}"
