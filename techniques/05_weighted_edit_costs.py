"""
Technique 5: Weighted Edit Costs

Extends Damerau-Levenshtein by assigning different costs to different
operation types, reflecting how likely each mistake is in practice:

    Transposition: 0   (most common — fingers overlap in timing)
    Insertion:     1   (extra key pressed)
    Substitution:  2   (wrong key entirely)
    Deletion:      3   (missing key — information lost)

No direct external library equivalent.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_tree import SHOW_CANDIDATES

DEFAULT_WEIGHTS = {
    "transposition": 0,
    "insertion": 1,
    "substitution": 2,
    "deletion": 3,
}


def weighted_damerau_levenshtein(s, t, weights=None):
    """Compute weighted Damerau-Levenshtein distance.

    Each edit operation has a configurable cost instead of a flat 1.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    w_trans = weights["transposition"]
    w_ins = weights["insertion"]
    w_sub = weights["substitution"]
    w_del = weights["deletion"]

    len_s = len(s)
    len_t = len(t)

    char_map = {}
    max_dist = (len_s + len_t) * max(w_ins, w_del, w_sub, w_trans + 1)

    d = [[0] * (len_t + 2) for _ in range(len_s + 2)]
    d[0][0] = max_dist
    for i in range(len_s + 1):
        d[i + 1][0] = max_dist
        d[i + 1][1] = i * w_del
    for j in range(len_t + 1):
        d[0][j + 1] = max_dist
        d[1][j + 1] = j * w_ins

    for i in range(1, len_s + 1):
        db = 0
        for j in range(1, len_t + 1):
            i1 = char_map.get(t[j - 1], 0)
            j1 = db

            if s[i - 1] == t[j - 1]:
                cost = 0
                db = j
            else:
                cost = w_sub

            trans_cost = (
                d[i1][j1]
                + (i - i1 - 1) * w_del
                + w_trans
                + (j - j1 - 1) * w_ins
            )

            d[i + 1][j + 1] = min(
                d[i][j] + cost,       # substitution / match
                d[i + 1][j] + w_ins,  # insertion
                d[i][j + 1] + w_del,  # deletion
                trans_cost,           # transposition
            )

        char_map[s[i - 1]] = i

    return d[len_s + 1][len_t + 1]


def suggest(user_input, candidates, threshold=4):
    """Rank candidates by weighted distance."""
    scored = [(c, weighted_damerau_levenshtein(user_input, c)) for c in candidates]
    scored.sort(key=lambda x: x[1])
    return [(c, d) for c, d in scored if d <= threshold]


def demo():
    print("=" * 60)
    print("Technique 5: Weighted Edit Costs")
    print("=" * 60)

    print(f"\n  Weights: {DEFAULT_WEIGHTS}\n")

    # --- Show how weights break ties ---
    print("  Comparing 'runnign' and 'wunning' against 'running':\n")

    from importlib import import_module
    try:
        t04 = import_module("04_damerau_levenshtein")
        dl = t04.damerau_levenshtein
    except Exception:
        dl = None

    for typo, note in [("runnign", "transposition"), ("wunning", "substitution")]:
        w = weighted_damerau_levenshtein(typo, "running")
        line = f"    '{typo}' vs 'running':  weighted={w}  ({note})"
        if dl:
            d = dl(typo, "running")
            line += f"  [standard DL={d}]"
        print(line)

    print("\n  With standard DL both have distance 1 — tied.")
    print("  With weights, the transposition (0) ranks above the substitution (2).\n")

    # --- Suggestion example ---
    print("  Suggestions for 'interfce' (threshold ≤ 4):\n")
    results = suggest("interfce", SHOW_CANDIDATES)
    for c, d in results:
        print(f"    → {c}  (weighted distance {d})")

    print("\n  Suggestions for 'vresion' (threshold ≤ 4):\n")
    results = suggest("vresion", SHOW_CANDIDATES)
    for c, d in results:
        print(f"    → {c}  (weighted distance {d})")

    # --- Shortcomings ---
    print("  Shortcomings:")
    print("  ─────────────")
    print("  1) Transposition weight of 0 treats any transposition as free:\n")
    d1 = weighted_damerau_levenshtein("abcde", "abced")
    d2 = weighted_damerau_levenshtein("abcde", "abcfe")
    print(f"     'abced' → 'abcde': weighted = {d1}  (transposition — free)")
    print(f"     'abcfe' → 'abcde': weighted = {d2}  (substitution — cost 2)")
    print("     The transposition always wins, even when the substituted")
    print("     character might be the intended one.\n")

    print("  2) Optimal weights are a judgment call — no universal values:")
    alt_weights = {"transposition": 1, "insertion": 1, "substitution": 1, "deletion": 2}
    d_default = weighted_damerau_levenshtein("runnign", "running")
    d_alt = weighted_damerau_levenshtein("runnign", "running", alt_weights)
    print(f"     'runnign' default weights: {d_default}")
    print(f"     'runnign' alt weights {alt_weights}: {d_alt}")
    print("     Different weights produce different rankings.\n")

    # --- Pros / Cons Summary ---
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  PROS vs CONS SUMMARY                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ✅ PROS:                                               │")
    print("  │    • Breaks ties between equally-distant candidates     │")
    print("  │    • Transpositions ranked as most likely (cost 0)      │")
    print("  │    • Substitution vs deletion now distinguishable       │")
    print("  │    • Configurable — tune weights per domain             │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ❌ CONS:                                               │")
    print("  │    • Weights are a judgment call — no universal optimum │")
    print("  │    • cost=0 for transposition may be too aggressive     │")
    print("  │    • No library provides this out-of-the-box            │")
    print("  │    • Still uses a fixed threshold for acceptance        │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  → NEXT: Technique 6 (Keyboard-Aware) weights          │")
    print("  │          substitutions by physical key proximity        │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    demo()
