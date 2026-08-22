"""
Technique 8: Jaro-Winkler Similarity

Returns a score between 0 (completely different) and 1 (identical).
Jaro similarity considers matching characters, string lengths, and
transpositions. Winkler adds a prefix bonus — strings that share a
common beginning score higher.

Good for CLI commands where users typically get the prefix right and
make mistakes toward the end.

Library comparison: rapidfuzz.distance.JaroWinkler
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_tree import SHOW_CANDIDATES


def jaro_similarity(s, t):
    """Compute Jaro similarity between strings s and t.

    Three factors contribute to the score:
      1. Matching characters within a distance window
      2. Each string's length (normalizes match count)
      3. Transpositions among matched characters
    """
    if s == t:
        return 1.0

    len_s, len_t = len(s), len(t)
    if len_s == 0 or len_t == 0:
        return 0.0

    # Characters can only match if they are within this window
    match_window = max(len_s, len_t) // 2 - 1
    if match_window < 0:
        match_window = 0

    s_matched = [False] * len_s
    t_matched = [False] * len_t

    matches = 0
    transpositions = 0

    # Find matching characters
    for i in range(len_s):
        start = max(0, i - match_window)
        end = min(i + match_window + 1, len_t)
        for j in range(start, end):
            if t_matched[j] or s[i] != t[j]:
                continue
            s_matched[i] = True
            t_matched[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    # Count transpositions among matched characters
    k = 0
    for i in range(len_s):
        if not s_matched[i]:
            continue
        while not t_matched[k]:
            k += 1
        if s[i] != t[k]:
            transpositions += 1
        k += 1

    jaro = (
        matches / len_s
        + matches / len_t
        + (matches - transpositions / 2) / matches
    ) / 3

    return jaro


def jaro_winkler_similarity(s, t, prefix_weight=0.1, boost_threshold=0.7):
    """Compute Jaro-Winkler similarity.

    Adds a bonus for matching prefixes (up to 4 characters), but only
    when the base Jaro score already exceeds boost_threshold (default 0.7).
    This prevents the prefix bonus from inflating scores for unrelated strings.
    """
    jaro = jaro_similarity(s, t)

    if jaro < boost_threshold:
        return jaro

    # Count common prefix (up to 4 characters)
    prefix_len = 0
    for i in range(min(len(s), len(t), 4)):
        if s[i] == t[i]:
            prefix_len += 1
        else:
            break

    return jaro + prefix_len * prefix_weight * (1 - jaro)


def suggest(user_input, candidates, threshold=0.8):
    """Rank candidates by Jaro-Winkler similarity, return those above threshold."""
    scored = [(c, jaro_winkler_similarity(user_input, c)) for c in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [(c, score) for c, score in scored if score >= threshold]


def demo():
    print("=" * 60)
    print("Technique 8: Jaro-Winkler Similarity")
    print("=" * 60)

    # --- Step-by-step for one pair ---
    s, t = "interfce", "interface"
    jaro = jaro_similarity(s, t)
    jw = jaro_winkler_similarity(s, t)
    print(f"\n  Step-by-step for '{s}' vs '{t}':")
    print(f"    Jaro similarity:          {jaro:.4f}")
    print(f"    Common prefix:            'interf' (6 chars, capped to 4)")
    print(f"    Jaro-Winkler similarity:  {jw:.4f}")

    # --- Score all candidates ---
    print(f"\n  Scoring 'interfce' against show-level candidates:\n")
    for c in SHOW_CANDIDATES:
        jw_score = jaro_winkler_similarity("interfce", c)
        marker = " ← best" if jw_score > 0.85 else ""
        print(f"    vs '{c}': {jw_score:.4f}{marker}")

    # --- Suggestion examples ---
    print("\n  Suggestions (threshold ≥ 0.80):\n")
    tests = ["interfce", "vrsion", "termnial", "shwo", "xyz"]
    for user_input in tests:
        results = suggest(user_input, SHOW_CANDIDATES)
        print(f"    Input: '{user_input}'")
        if results:
            for c, score in results:
                print(f"      → {c}  ({score:.4f})")
        else:
            print("      No suggestions above threshold")
        print()

    # --- Shortcomings ---
    print("  Shortcomings:")
    print("  ─────────────")
    print("  1) Mistake at the start negates the prefix bonus:\n")
    for typo, note in [("gersion", "wrong first char"), ("version", "correct")]:
        score = jaro_winkler_similarity(typo, "version")
        print(f"     '{typo}' vs 'version': {score:.4f}  ({note})")
    print("     'gersion' has only 1 wrong character but scores much lower")
    print("     because the prefix bonus cannot apply.\n")

    print("  2) Short strings can produce misleading scores:\n")
    for s, t in [("ip", "up"), ("ip", "interface")]:
        score = jaro_winkler_similarity(s, t)
        print(f"     '{s}' vs '{t}': {score:.4f}")
    print("     'ip' vs 'up' scores high despite being unrelated commands.\n")

    # --- Library comparison ---
    try:
        from rapidfuzz.distance import JaroWinkler as rf_jw

        print("  --- Comparison with rapidfuzz ---\n")
        pairs = [
            ("interfce", "interface"),
            ("shwo", "show"),
            ("bpg", "bgp"),
            ("vrsion", "version"),
        ]
        for s, t in pairs:
            ours = jaro_winkler_similarity(s, t)
            theirs = rf_jw.similarity(s, t)
            diff = abs(ours - theirs)
            match = "✓" if diff < 0.001 else f"Δ={diff:.4f}"
            print(f"    '{s}' vs '{t}':  ours={ours:.4f}  "
                  f"rapidfuzz={theirs:.4f}  {match}")
        print()
    except ImportError:
        print("  (install rapidfuzz for library comparison: "
              "pip install rapidfuzz)\n")

    # --- Pros / Cons Summary ---
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  PROS vs CONS SUMMARY                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ✅ PROS:                                               │")
    print("  │    • Normalized 0–1 score (no threshold tuning needed)  │")
    print("  │    • Prefix bonus rewards 'almost right' beginnings     │")
    print("  │    • Naturally handles different-length strings          │")
    print("  │    • Well-suited to CLI where prefixes are typed first  │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ❌ CONS:                                               │")
    print("  │    • Error at position 1 kills the prefix bonus         │")
    print("  │    • Short strings produce misleadingly high scores     │")
    print("  │    • No concept of keyboard proximity or edit type      │")
    print("  │    • Prefix cap at 4 chars limits bonus for long words  │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  → NEXT: Technique 9 (N-grams) uses chunk overlap for  │")
    print("  │          robustness to mid-word insertions/deletions    │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    demo()
