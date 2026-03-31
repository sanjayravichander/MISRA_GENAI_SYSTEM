# app/retrieval/retrieval_postprocessor.py

from typing import List, Dict


def postprocess_retrieved_rules(
    rules: List[Dict],
    min_score: float | None = None,
) -> List[Dict]:
    """
    Clean and filter retrieved rules before generation.

    Args:
        rules:     raw list from retrieve_rules()
        min_score: override threshold; if None reads from settings.
                   Pass 0.0 to skip score filtering entirely (useful for debugging).
    """
    if not rules:
        return []

    # Read threshold from settings so it is never hardcoded here
    if min_score is None:
        try:
            from app.config.settings import RETRIEVAL_MIN_SCORE
            min_score = RETRIEVAL_MIN_SCORE
        except ImportError:
            min_score = 0.70   # safe fallback if settings not importable

    # 1. Score filter
    filtered = [r for r in rules if r.get("score", 0) >= min_score]

    # 2. If score filter rejected everything, fall back to the single best match
    #    rather than returning empty — generation needs at least one rule to work with.
    if not filtered and rules:
        best = max(rules, key=lambda r: r.get("score", 0))
        filtered = [best]

    # 3. Deduplicate by rule_id (keep highest score per rule)
    best_by_rule: Dict[str, Dict] = {}
    for r in filtered:
        rid = r.get("rule_id")
        if not rid:
            continue
        if rid not in best_by_rule or r["score"] > best_by_rule[rid]["score"]:
            best_by_rule[rid] = r

    # 4. Sort by score descending
    final_rules = sorted(
        best_by_rule.values(),
        key=lambda x: x["score"],
        reverse=True,
    )

    # 5. Keep top 4 (deterministic)
    return final_rules[:4]