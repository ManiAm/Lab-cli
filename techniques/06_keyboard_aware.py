"""
Technique 6: Keyboard-Aware Weighted Distance

Assigns lower substitution cost to keys that are physically adjacent
on the keyboard. Hitting 'f' instead of 'g' (neighbors) is a more
likely fat-finger mistake than hitting 'f' instead of 'p' (distant).

Uses QWERTY key positions to compute physical distance between keys.

No external libraries needed.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_tree import SHOW_CANDIDATES
import math

# QWERTY keyboard layout — (row, column) positions for each key.
# Row 0 = top row, Row 1 = home row, Row 2 = bottom row.
# Column positions account for the stagger between rows.
QWERTY_POSITIONS = {
    "q": (0, 0),   "w": (0, 1),   "e": (0, 2),   "r": (0, 3),
    "t": (0, 4),   "y": (0, 5),   "u": (0, 6),   "i": (0, 7),
    "o": (0, 8),   "p": (0, 9),
    "a": (1, 0.5), "s": (1, 1.5), "d": (1, 2.5), "f": (1, 3.5),
    "g": (1, 4.5), "h": (1, 5.5), "j": (1, 6.5), "k": (1, 7.5),
    "l": (1, 8.5),
    "z": (2, 1),   "x": (2, 2),   "c": (2, 3),   "v": (2, 4),
    "b": (2, 5),   "n": (2, 6),   "m": (2, 7),
}


def key_distance(c1, c2):
    """Euclidean distance between two keys on QWERTY.

    Returns 0.0 if same key, small value if adjacent, up to ~10 for
    opposite corners. Returns None if either key has no known position.
    """
    c1, c2 = c1.lower(), c2.lower()
    if c1 == c2:
        return 0.0
    pos1 = QWERTY_POSITIONS.get(c1)
    pos2 = QWERTY_POSITIONS.get(c2)
    if pos1 is None or pos2 is None:
        return None
    return math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)


def substitution_cost(c1, c2, max_cost=1.0):
    """Variable substitution cost based on keyboard distance.

    Adjacent keys (dist ≈ 1.0): cost ≈ 0.33
    Distant keys (dist ≥ 3):    cost = 1.0
    """
    if c1 == c2:
        return 0.0
    dist = key_distance(c1, c2)
    if dist is None:
        return max_cost
    return min(dist / 3.0, max_cost)


def keyboard_aware_levenshtein(s, t):
    """Levenshtein distance with keyboard-aware substitution costs.

    Insertions and deletions still cost 1.0 each. Substitutions cost
    between 0.0 and 1.0 depending on key proximity.
    """
    m, n = len(s), len(t)

    dp = [[0.0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = float(i)
    for j in range(n + 1):
        dp[0][j] = float(j)

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = substitution_cost(s[i - 1], t[j - 1])
            dp[i][j] = min(
                dp[i - 1][j] + 1.0,       # deletion
                dp[i][j - 1] + 1.0,       # insertion
                dp[i - 1][j - 1] + cost,   # substitution
            )

    return dp[m][n]


def suggest(user_input, candidates, threshold=2.5):
    """Rank candidates by keyboard-aware distance."""
    scored = [(c, keyboard_aware_levenshtein(user_input, c)) for c in candidates]
    scored.sort(key=lambda x: x[1])
    return [(c, d) for c, d in scored if d <= threshold]


def demo():
    print("=" * 60)
    print("Technique 6: Keyboard-Aware Weighted Distance")
    print("=" * 60)

    # --- Show key distances ---
    print("\n  Key distances on QWERTY:\n")
    pairs = [
        ("f", "g", "adjacent"),
        ("f", "d", "adjacent"),
        ("s", "e", "close (diagonal)"),
        ("f", "p", "distant"),
        ("a", "z", "moderate"),
    ]
    for c1, c2, note in pairs:
        dist = key_distance(c1, c2)
        cost = substitution_cost(c1, c2)
        print(f"    '{c1}' ↔ '{c2}':  distance={dist:.2f}  "
              f"sub_cost={cost:.2f}  ({note})")

    # --- Compare standard vs keyboard-aware ---
    print("\n  Standard Levenshtein vs Keyboard-Aware:\n")
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

    test_pairs = [
        ("interfacs", "interface", "'s' and 'e' are close on QWERTY"),
        ("intarface", "interface", "'a' and 'e' are not adjacent"),
        ("intwrface", "interface", "'w' and 'e' are adjacent"),
        ("intqrface", "interface", "'q' and 'e' are two keys apart"),
    ]
    for typo, correct, note in test_pairs:
        std = lev(typo, correct)
        kba = keyboard_aware_levenshtein(typo, correct)
        print(f"    '{typo}' vs '{correct}':  standard={std}  "
              f"keyboard-aware={kba:.2f}  ({note})")

    # --- Suggestion example ---
    print("\n  Suggestions for 'interfacs' (threshold ≤ 2.5):\n")
    results = suggest("interfacs", SHOW_CANDIDATES)
    for c, d in results:
        print(f"    → {c}  (distance {d:.2f})")

    # --- Shortcomings ---
    print("  Shortcomings:")
    print("  ─────────────")
    print("  1) Assumes QWERTY layout — costs are wrong for other keyboards:\n")
    print("     On AZERTY: 'a' and 'q' are swapped, 'z' and 'w' are swapped.")
    print("     On Dvorak: the entire layout is different.")
    print("     A user on a non-QWERTY keyboard gets incorrect distance scores.\n")

    print("  2) Marginal benefit when the command set is small:")
    d_std = lev("interfacs", "interface")
    d_kba = keyboard_aware_levenshtein("interfacs", "interface")
    d_std2 = lev("interfacs", "interfaces")
    d_kba2 = keyboard_aware_levenshtein("interfacs", "interfaces")
    print(f"     Standard:       'interfacs' → interface={d_std}, interfaces={d_std2}")
    print(f"     Keyboard-aware: 'interfacs' → interface={d_kba:.2f}, interfaces={d_kba2:.2f}")
    print("     Both approaches rank 'interface' first — the keyboard-aware")
    print("     refinement does not change the winner in this case.\n")

    # --- Pros / Cons Summary ---
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  PROS vs CONS SUMMARY                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ✅ PROS:                                               │")
    print("  │    • Adjacent-key typos penalized less (realistic)      │")
    print("  │    • 'interfacs' scores lower than 'intqrface' (correct)│")
    print("  │    • Models physical typing mistakes accurately         │")
    print("  │    • Still O(m×n) — no extra complexity class           │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ❌ CONS:                                               │")
    print("  │    • Assumes QWERTY — wrong for AZERTY/Dvorak/etc.     │")
    print("  │    • Marginal benefit when candidate set is small       │")
    print("  │    • Does not help with insertions or deletions         │")
    print("  │    • Fractional scores harder to reason about           │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  → NEXT: Technique 7 (Threshold Scaling) adjusts the   │")
    print("  │          acceptance threshold based on word length      │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    demo()
