"""Rules based triage: turn a report into a priority.

This is the deterministic baseline. It exists for three reasons.

It is honest. Every decision here can be explained to an operator in one
sentence, and the reason travels with the incident. `severity_probability`
stays null throughout, because a rule is not a calibrated probability and
printing one would repeat the mistake the earlier build made when a blank
photograph scored 95 per cent.

It is a floor to beat. When a trained classifier arrives it has to do better
than this, measured on the same held out reports, or it is not worth shipping.

It is safe in one direction only. A rule may raise urgency and may never lower
it below the baseline for its category. A wrongly raised incident costs a
wasted walk. A wrongly lowered one costs the thing the system exists for.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.models import Category

# Baseline by category, before anything in the text is read.
# 1 is most urgent, 4 is least.
BASELINE: dict[Category, int] = {
    Category.fire: 1,        # fire in a crowd is immediately life threatening
    Category.medical: 2,     # anything from a faint to a cardiac arrest
    Category.crowd: 2,       # crush risk, and it grows fast
    Category.violence: 2,
    # A personal safety report needs a responder quickly, but it is not the
    # same class of emergency as a fire. The discreet handling that makes this
    # category usable is Increment V.
    Category.harassment: 2,
    Category.accident: 3,
    Category.other: 3,
}

DEFAULT_PRIORITY = 3


@dataclass(frozen=True)
class Rule:
    """One phrase, the priority it implies, and why."""
    pattern: re.Pattern[str]
    priority: int
    reason: str


def _rule(priority: int, reason: str, *phrases: str) -> Rule:
    # \b on each side so "fire" does not match "fireworks stall" and "gun" does
    # not match "gunny sack".
    body = "|".join(re.escape(p) for p in phrases)
    return Rule(re.compile(rf"(?<!\w)(?:{body})(?!\w)", re.I), priority, reason)


# Reports at Indian venues are routinely code mixed, so the phrases below carry
# the common Romanised Hindi alongside the English. This list is deliberately
# short: every entry has to be defensible, and a long list of weak keywords is
# how a rules engine quietly becomes noise.
RULES: tuple[Rule, ...] = (
    # --- life threatening -------------------------------------------------
    _rule(1, "breathing reported to have stopped",
          "not breathing", "cant breathe", "can not breathe", "cannot breathe",
          "no breathing", "stopped breathing",
          "saans nahi", "saans nahin", "saans ruk"),
    _rule(1, "person reported unconscious",
          "unconscious", "unresponsive", "not responding", "passed out",
          "behosh", "behoshi"),
    _rule(1, "cardiac symptoms reported",
          "cardiac", "heart attack", "chest pain", "cpr",
          "dil ka daura"),
    _rule(1, "crush or stampede reported",
          "stampede", "crush", "crushed", "trampled", "being trampled",
          "bhagdad", "bhagdar", "bhagdarh", "dab gaya", "dab gaye",
          "kuchla", "kuchal"),
    _rule(1, "severe bleeding reported",
          "bleeding heavily", "heavy bleeding", "lot of blood", "blood loss",
          "khoon bah", "bahut khoon"),
    _rule(1, "person trapped",
          "trapped", "stuck under", "pinned", "phans gaya", "phas gaya"),
    _rule(1, "fire or smoke reported",
          "fire", "smoke", "burning", "flames", "aag", "dhuan", "dhuaan"),
    _rule(1, "weapon reported",
          "knife", "gun", "weapon", "chaku", "bandook", "pistol"),
    _rule(1, "child reported missing",
          "lost child", "missing child", "child missing", "lost kid",
          "bachcha kho", "bacha kho", "bachcha gum"),

    # --- urgent, not immediately life threatening -------------------------
    _rule(2, "injury reported",
          "injured", "injury", "bleeding", "broken", "fracture", "burn",
          "ghayal", "chot", "haddi"),
    _rule(2, "collapse or fainting reported",
          "collapsed", "fainted", "fainting", "dizzy", "seizure", "fit",
          "gir gaya", "gir gayi", "chakkar"),
    _rule(2, "fight reported",
          "fight", "fighting", "assault", "attacked", "beaten",
          "ladai", "jhagda", "maar"),
    _rule(2, "crowd pressure reported",
          "pushing", "surge", "too many people", "cannot move", "squeeze",
          "dhakka", "bheed", "nikal nahi"),
    _rule(2, "person reported in distress",
          "help me", "unsafe", "following me", "harassing", "harassment",
          "molest", "chhed", "cheda", "peecha"),
)

# Independent witnesses are evidence about the event, not about any model. When
# several arrive for one incident the urgency rises by one step.
CORROBORATION_THRESHOLD = 3


@dataclass(frozen=True)
class Triage:
    priority: int
    reason: str
    headline: str


def assess(category: Category, text: str | None,
           report_count: int = 1) -> Triage:
    """Decide a priority for one incident.

    Returns the priority, the reason a human can read, and a headline for the
    control room list.
    """
    baseline = BASELINE.get(category, DEFAULT_PRIORITY)
    priority = baseline
    reasons: list[str] = []

    if text:
        for rule in RULES:
            if rule.priority < priority and rule.pattern.search(text):
                priority = rule.priority
                reasons = [rule.reason]
            elif rule.priority == priority and rule.pattern.search(text):
                if rule.reason not in reasons:
                    reasons.append(rule.reason)

    if report_count >= CORROBORATION_THRESHOLD and priority > 1:
        priority -= 1
        reasons.append(f"{report_count} independent reports")

    if not reasons:
        reasons = [f"{category.value} reported, no further detail"]

    reason = "; ".join(reasons)
    headline = f"{category.value.title()}: {reasons[0]}"
    return Triage(priority=priority, reason=reason, headline=headline[:200])
