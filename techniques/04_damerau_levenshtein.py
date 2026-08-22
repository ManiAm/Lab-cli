"""
Technique 4: Damerau-Levenshtein Distance

Extends Levenshtein by adding transposition of two adjacent characters as
a single operation (cost 1 instead of 2). Transpositions are among the
most common typing mistakes, so this gives more accurate distances.

This implements the *true* Damerau-Levenshtein (not the simpler Optimal
String Alignment variant, which forbids editing a substring more than once).

Library comparison: rapidfuzz.distance.DamerauLevenshtein
    Note: rapidfuzz implements the OSA variant, which may differ from
    true Damerau-Levenshtein in rare edge cases.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_tree import COMMAND_TREE, get_keywords, SHOW_CANDIDATES


def damerau_levenshtein(s, t):
    """Compute true Damerau-Levenshtein distance between s and t.

    Allowed operations (each costs 1):
        - insertion
        - deletion
        - substitution
        - transposition of two adjacent characters
    """
    len_s = len(s)
    len_t = len(t)

    # Map each character to its most recent position in s
    char_map = {}

    # d is indexed from -1 to len_s, -1 to len_t
    # Use offset of 1 to avoid negative indices
    d = [[0] * (len_t + 2) for _ in range(len_s + 2)]

    max_dist = len_s + len_t

    d[0][0] = max_dist
    for i in range(len_s + 1):
        d[i + 1][0] = max_dist
        d[i + 1][1] = i
    for j in range(len_t + 1):
        d[0][j + 1] = max_dist
        d[1][j + 1] = j

    for i in range(1, len_s + 1):
        db = 0  # last column in t where s[i] == t[j]

        for j in range(1, len_t + 1):
            i1 = char_map.get(t[j - 1], 0)  # last row in s where t[j] appeared
            j1 = db

            if s[i - 1] == t[j - 1]:
                cost = 0
                db = j
            else:
                cost = 1

            d[i + 1][j + 1] = min(
                d[i][j] + cost,                             # substitution
                d[i + 1][j] + 1,                            # insertion
                d[i][j + 1] + 1,                            # deletion
                d[i1][j1] + (i - i1 - 1) + 1 + (j - j1 - 1)  # transposition
            )

        char_map[s[i - 1]] = i

    return d[len_s + 1][len_t + 1]


def suggest(user_input, candidates, threshold=3):
    """Rank candidates by Damerau-Levenshtein distance."""
    scored = [(c, damerau_levenshtein(user_input, c)) for c in candidates]
    scored.sort(key=lambda x: x[1])
    return [(c, d) for c, d in scored if d <= threshold]


def demo():
    print("=" * 60)
    print("Technique 4: Damerau-Levenshtein Distance")
    print("=" * 60)

    # --- Show the key difference from plain Levenshtein ---
    from importlib import import_module
    try:
        t03 = import_module("03_levenshtein")
        lev = t03.levenshtein
    except Exception:
        def lev(a, b):
            m, n = len(a), len(b)
            dp = [[0]*(n+1) for _ in range(m+1)]
            for i in range(m+1): dp[i][0] = i
            for j in range(n+1): dp[0][j] = j
            for i in range(1,m+1):
                for j in range(1,n+1):
                    c = 0 if a[i-1]==b[j-1] else 1
                    dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+c)
            return dp[m][n]

    print("\n  Transposition examples (Levenshtein vs Damerau-Levenshtein):\n")
    pairs = [
        ("shwo", "show"),
        ("inteface", "interface"),
        ("bpg", "bgp"),
        ("vresion", "version"),
        ("temniral", "terminal"),
    ]
    for s, t in pairs:
        ld = lev(s, t)
        dl = damerau_levenshtein(s, t)
        note = "DL lower — transposition detected" if dl < ld else "same"
        print(f"    '{s}' vs '{t}':  Levenshtein={ld}  DL={dl}  ({note})")

    # --- Suggestion examples ---
    root_candidates = get_keywords(COMMAND_TREE)
    print("\n  Suggestions for 'shwo' against root-level candidates:\n")
    for c in root_candidates:
        d = damerau_levenshtein("shwo", c)
        print(f"    vs '{c}': {d}")

    results = suggest("shwo", root_candidates, threshold=2)
    if results:
        print(f"\n    Top suggestions (threshold ≤ 2):")
        for c, d in results:
            print(f"      → {c}  (distance {d})")

    # --- Shortcomings ---
    print("\n  Shortcomings:")
    print("  ─────────────")
    print("  All edit operations still cost exactly 1 — no distinction:\n")
    examples = [
        ("runnign", "running", "transposition (very common typo)"),
        ("wunning", "running", "substitution (less likely)"),
        ("rnning", "running", "deletion (information lost)"),
    ]
    for typo, target, note in examples:
        d = damerau_levenshtein(typo, target)
        print(f"    '{typo}' → '{target}': distance = {d}  ({note})")
    print("\n  All three score identically, so the engine cannot prefer")
    print("  the transposition (most plausible) over the others.")
    print("  Technique 5 (Weighted Edit Costs) addresses this.\n")

    # --- Library comparison ---
    print()
    try:
        from rapidfuzz.distance import DamerauLevenshtein as rf_dl

        print("  --- Comparison with rapidfuzz (OSA variant) ---\n")
        print("  Note: rapidfuzz implements Optimal String Alignment, not true")
        print("  Damerau-Levenshtein. Results match for most inputs but may")
        print("  differ when a substring would need to be edited twice.\n")
        for s, t in pairs:
            ours = damerau_levenshtein(s, t)
            theirs = rf_dl.distance(s, t)
            match = "✓" if ours == theirs else "≠ (OSA vs true DL)"
            print(f"    '{s}' vs '{t}':  ours={ours}  rapidfuzz={theirs}  {match}")
        print()
    except ImportError:
        print("  (install rapidfuzz for library comparison: "
              "pip install rapidfuzz)\n")

    # --- Pros / Cons Summary ---
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  PROS vs CONS SUMMARY                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ✅ PROS:                                               │")
    print("  │    • Transpositions cost 1 (not 2 as in Levenshtein)    │")
    print("  │    • Better models real typing errors (finger overlap)  │")
    print("  │    • 'shwo'→'show' is now distance 1 (correct!)        │")
    print("  │    • Widely available in libraries (rapidfuzz, etc.)    │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ❌ CONS:                                               │")
    print("  │    • All operations still cost the same (flat cost = 1) │")
    print("  │    • Cannot rank: transposition vs substitution vs del  │")
    print("  │    • Fixed threshold still doesn't scale with length    │")
    print("  │    • Slightly more complex implementation than plain Lev│")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  → NEXT: Technique 5 (Weighted Edit Costs) assigns      │")
    print("  │          different costs to each operation type         │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    demo()
