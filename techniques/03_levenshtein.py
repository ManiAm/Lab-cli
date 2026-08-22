"""
Technique 3: Levenshtein Distance

The minimum number of single-character edits (insertions, deletions,
substitutions) needed to transform one string into another.

Uses a dynamic programming matrix of size (m+1) x (n+1).

Library comparison: rapidfuzz.distance.Levenshtein
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_tree import SHOW_CANDIDATES


def levenshtein(s, t):
    """Compute Levenshtein distance between strings s and t.

    Returns the minimum number of insertions, deletions, and substitutions
    needed to transform s into t.
    """
    m, n = len(s), len(t)

    # dp[i][j] = distance between s[:i] and t[:j]
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i  # deleting all characters from s[:i]
    for j in range(n + 1):
        dp[0][j] = j  # inserting all characters of t[:j]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s[i - 1] == t[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,       # deletion
                dp[i][j - 1] + 1,       # insertion
                dp[i - 1][j - 1] + cost  # substitution (0 if chars match)
            )

    return dp[m][n]


def print_matrix(s, t):
    """Print the full DP matrix for educational visualization."""
    m, n = len(s), len(t)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s[i - 1] == t[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )

    header = ['""'] + list(t)
    print("        " + "  ".join(f"{c:>2}" for c in header))
    for i in range(m + 1):
        label = '""' if i == 0 else s[i - 1]
        row = "  ".join(f"{dp[i][j]:>2}" for j in range(n + 1))
        print(f"    {label:>2}  {row}")


def suggest(user_input, candidates, threshold=3):
    """Rank candidates by Levenshtein distance, return those within threshold."""
    scored = [(c, levenshtein(user_input, c)) for c in candidates]
    scored.sort(key=lambda x: x[1])
    return [(c, d) for c, d in scored if d <= threshold]


def demo():
    print("=" * 60)
    print("Technique 3: Levenshtein Distance")
    print("=" * 60)

    # --- DP matrix visualization ---
    print("\n  DP matrix for 'interfce' vs 'interface':\n")
    print_matrix("interfce", "interface")
    print(f"\n  → Distance = {levenshtein('interfce', 'interface')}  "
          "(one insertion: add 'a' between 'f' and 'c')\n")

    # --- Score all candidates ---
    print("  Scoring 'interfce' against show-level candidates:\n")
    for c in SHOW_CANDIDATES:
        d = levenshtein("interfce", c)
        marker = " ← best" if d <= 2 else ""
        print(f"    vs '{c}': {d}{marker}")

    # --- Suggestion examples ---
    print("\n  Suggestion examples (threshold ≤ 3):\n")
    tests = [
        ("interfce", SHOW_CANDIDATES),
        ("vrsion", SHOW_CANDIDATES),
        ("termnial", SHOW_CANDIDATES),
        ("xyz", SHOW_CANDIDATES),
    ]
    for user_input, cands in tests:
        results = suggest(user_input, cands)
        print(f"    Input: '{user_input}'")
        if results:
            for c, d in results:
                print(f"      → {c}  (distance {d})")
        else:
            print("      No suggestions within threshold")
        print()

    # --- Shortcomings ---
    print("  Shortcomings:")
    print("  ─────────────")
    print("  1) Transpositions are overpenalized (cost 2 instead of 1):\n")
    d = levenshtein("shwo", "show")
    print(f"     'shwo' → 'show': distance = {d}  (delete 'w' + insert 'w' = 2)")
    print("     But the user just swapped two adjacent keys — should be 1.\n")

    print("  2) All edit types cost the same:")
    d1 = levenshtein("interfacs", "interface")
    d2 = levenshtein("xnterfacz", "interface")
    print(f"     'interfacs' → 'interface': {d1}  (likely fat-finger on 's')")
    print(f"     'xnterfacz' → 'interface': {d2}  (two unrelated characters)")
    print("     Both cost the same, but the first is far more likely a typo.\n")

    # --- Library comparison ---
    try:
        from rapidfuzz.distance import Levenshtein as rf_lev

        print("  --- Comparison with rapidfuzz ---\n")
        pairs = [
            ("interfce", "interface"),
            ("shwo", "show"),
            ("bpg", "bgp"),
            ("vrsion", "version"),
            ("termnial", "terminal"),
        ]
        all_match = True
        for s, t in pairs:
            ours = levenshtein(s, t)
            theirs = rf_lev.distance(s, t)
            match = "✓" if ours == theirs else "✗"
            if ours != theirs:
                all_match = False
            print(f"    '{s}' vs '{t}':  ours={ours}  rapidfuzz={theirs}  {match}")
        status = "All results match!" if all_match else "Some results differ."
        print(f"\n    {status}\n")
    except ImportError:
        print("  (install rapidfuzz for library comparison: "
              "pip install rapidfuzz)\n")

    # --- Pros / Cons Summary ---
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  PROS vs CONS SUMMARY                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ✅ PROS:                                               │")
    print("  │    • Tolerates typos — finds 'interface' from 'interfce'│")
    print("  │    • Well-understood algorithm with proven correctness   │")
    print("  │    • Works regardless of error position (start/mid/end) │")
    print("  │    • Numeric score enables ranking by confidence        │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ❌ CONS:                                               │")
    print("  │    • Transpositions cost 2 (should be 1 for fat-finger) │")
    print("  │    • All edits weighted equally (sub = ins = del)       │")
    print("  │    • O(m×n) per candidate — slower than prefix matching │")
    print("  │    • Fixed threshold doesn't scale with word length     │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  → NEXT: Technique 4 (Damerau-Levenshtein) fixes       │")
    print("  │          the transposition penalty                      │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    demo()
