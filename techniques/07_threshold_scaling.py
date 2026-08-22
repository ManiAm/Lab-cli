"""
Technique 7: Threshold Scaling by Token Length

A fixed distance threshold creates problems: short tokens accept too many
false positives, long tokens reject valid corrections. Threshold scaling
adjusts the maximum allowed distance based on the candidate's length.

    1–4 characters  →  max distance 2
    5–8 characters  →  max distance 4
    9+  characters  →  max distance 6

No external libraries needed.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_tree import SHOW_CANDIDATES


def get_threshold(token_length):
    """Return the maximum edit distance allowed for a token of this length."""
    if token_length <= 4:
        return 2
    elif token_length <= 8:
        return 4
    else:
        return 6


def damerau_levenshtein(s, t):
    """Damerau-Levenshtein distance (reproduced here for self-containedness)."""
    len_s, len_t = len(s), len(t)
    char_map = {}
    max_dist = len_s + len_t
    d = [[0] * (len_t + 2) for _ in range(len_s + 2)]
    d[0][0] = max_dist
    for i in range(len_s + 1):
        d[i + 1][0] = max_dist
        d[i + 1][1] = i
    for j in range(len_t + 1):
        d[0][j + 1] = max_dist
        d[1][j + 1] = j
    for i in range(1, len_s + 1):
        db = 0
        for j in range(1, len_t + 1):
            i1 = char_map.get(t[j - 1], 0)
            j1 = db
            cost = 0 if s[i - 1] == t[j - 1] else 1
            if s[i - 1] == t[j - 1]:
                db = j
            d[i + 1][j + 1] = min(
                d[i][j] + cost,
                d[i + 1][j] + 1,
                d[i][j + 1] + 1,
                d[i1][j1] + (i - i1 - 1) + 1 + (j - j1 - 1),
            )
        char_map[s[i - 1]] = i
    return d[len_s + 1][len_t + 1]


def suggest_with_threshold(user_input, candidates):
    """Score candidates and apply length-based threshold filtering."""
    results = []
    for candidate in candidates:
        dist = damerau_levenshtein(user_input, candidate)
        threshold = get_threshold(len(candidate))
        if dist <= threshold:
            results.append((candidate, dist, threshold))
    results.sort(key=lambda x: x[1])
    return results


def demo():
    print("=" * 60)
    print("Technique 7: Threshold Scaling by Token Length")
    print("=" * 60)

    print("\n  Threshold table:")
    print("    1–4 chars → max distance 2")
    print("    5–8 chars → max distance 4")
    print("    9+  chars → max distance 6\n")

    tests = [
        ("bpg", "bgp (3 chars → threshold 2)"),
        ("rning", "running (7 chars → threshold 4)"),
        ("xyz", "no close match for any short candidate"),
        ("rnning-confg", "running-config (14 chars → threshold 6)"),
        ("interfce", "interface (9 chars → threshold 6)"),
    ]

    # Build a wider candidate list for more interesting results
    candidates = list(dict.fromkeys(
        list(SHOW_CANDIDATES) + ["bgp", "running-config", "running"]
    ))

    for user_input, note in tests:
        print(f"  Input: '{user_input}'  ({note})")
        results = suggest_with_threshold(user_input, candidates)
        if results:
            for c, d, t in results:
                print(f"    → '{c}' (len={len(c)}, distance={d}, "
                      f"threshold={t}, {'accepted' if d <= t else 'rejected'})")
        else:
            print("    No suggestions (all candidates exceed their thresholds)")
        print()


    # --- Shortcomings ---
    print("  Shortcomings:")
    print("  ─────────────")
    print("  1) Does not distinguish edit types — only counts:\n")
    user_input = "runnign"
    for candidate, note in [("running", "transposition"), ("xunning", "substitution")]:
        dist = damerau_levenshtein(user_input, candidate)
        threshold = get_threshold(len(candidate))
        status = "accepted" if dist <= threshold else "rejected"
        print(f"     '{user_input}' vs '{candidate}' ({note}): "
              f"distance={dist}, threshold={threshold} → {status}")
    print("     Both pass the same threshold, even though a transposition")
    print("     is far more likely to be accidental.\n")

    print("  2) Breakpoints (4, 8) are heuristic — no optimal values:")
    print("     A 5-character token gets threshold 4, but a 4-character")
    print("     token gets threshold 2. This jump at the boundary may")
    print("     be too aggressive or too lenient depending on the command set.\n")

    # --- Pros / Cons Summary ---
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  PROS vs CONS SUMMARY                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ✅ PROS:                                               │")
    print("  │    • Short words reject garbage ('xyz'≠'ip' at dist 3)  │")
    print("  │    • Long words accept more edits (lenient for typos)   │")
    print("  │    • Reduces false positives on short keywords          │")
    print("  │    • Simple to implement — just a lookup table          │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ❌ CONS:                                               │")
    print("  │    • Breakpoints (4, 8) are arbitrary heuristics        │")
    print("  │    • Does not distinguish edit types (all cost 1)       │")
    print("  │    • Discontinuous jumps at boundaries (4→5 chars)      │")
    print("  │    • Cannot rank transposition above substitution       │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  → NEXT: Technique 8 (Jaro-Winkler) uses a normalized  │")
    print("  │          similarity score with prefix bonus             │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    demo()
