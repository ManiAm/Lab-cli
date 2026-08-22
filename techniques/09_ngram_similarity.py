"""
Technique 9: N-gram Similarity

Break strings into overlapping chunks of N characters (n-grams) and
measure how many chunks they share using the Dice coefficient:

    similarity = 2 × |shared| / (|ngrams_a| + |ngrams_b|)

Robust to insertions and deletions in the middle of a word because
only the immediately surrounding n-grams are affected.

No external libraries needed.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_tree import SHOW_CANDIDATES


def ngrams(s, n=2):
    """Generate the set of n-grams for string s.

    For s='interface' and n=2 (bigrams):
        {'in', 'nt', 'te', 'er', 'rf', 'fa', 'ac', 'ce'}
    """
    if len(s) < n:
        return {s}
    return {s[i:i + n] for i in range(len(s) - n + 1)}


def ngram_similarity(a, b, n=2):
    """Compute Dice coefficient over n-grams of a and b.

    Returns a float between 0 (no shared n-grams) and 1 (identical n-gram sets).
    """
    grams_a = ngrams(a, n)
    grams_b = ngrams(b, n)

    if not grams_a and not grams_b:
        return 1.0
    if not grams_a or not grams_b:
        return 0.0

    shared = grams_a & grams_b
    return 2 * len(shared) / (len(grams_a) + len(grams_b))


def suggest(user_input, candidates, n=2, threshold=0.5):
    """Rank candidates by n-gram similarity, return those above threshold."""
    scored = [(c, ngram_similarity(user_input, c, n)) for c in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [(c, score) for c, score in scored if score >= threshold]


def demo():
    print("=" * 60)
    print("Technique 9: N-gram Similarity")
    print("=" * 60)

    # --- Step-by-step bigram comparison ---
    a, b = "interface", "interfce"
    ga, gb = ngrams(a), ngrams(b)
    shared = ga & gb
    sim = ngram_similarity(a, b)

    print(f"\n  Bigrams of '{a}': {sorted(ga)}")
    print(f"  Bigrams of '{b}': {sorted(gb)}")
    print(f"  Shared:           {sorted(shared)}")
    print(f"  Dice coefficient: 2 × {len(shared)} / ({len(ga)} + {len(gb)}) "
          f"= {sim:.4f}")

    # --- Bigrams vs trigrams ---
    print(f"\n  Bigrams (n=2) vs Trigrams (n=3) for '{b}' vs '{a}':")
    for n in [2, 3]:
        score = ngram_similarity(a, b, n)
        print(f"    n={n}: similarity = {score:.4f}")

    # --- Score all candidates ---
    print(f"\n  Scoring 'interfce' against show-level candidates (bigrams):\n")
    for c in SHOW_CANDIDATES:
        score = ngram_similarity("interfce", c)
        marker = " ← best" if score > 0.6 else ""
        print(f"    vs '{c}': {score:.4f}{marker}")

    # --- Suggestion examples ---
    print("\n  Suggestions (bigram, threshold ≥ 0.50):\n")
    tests = ["interfce", "vrsion", "termnial", "xyz"]
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
    print("  1) Loses character-order information:\n")
    for a, b in [("abc", "cab"), ("abc", "xyz")]:
        score = ngram_similarity(a, b)
        print(f"     '{a}' vs '{b}': {score:.4f}")
    print("     'cab' shares bigrams with 'abc' despite different ordering,")
    print("     scoring higher than you might expect.\n")

    print("  2) Sensitive to the choice of N:\n")
    a, b = "interfce", "interface"
    for n in [2, 3, 4]:
        score = ngram_similarity(a, b, n)
        print(f"     n={n}: '{a}' vs '{b}' = {score:.4f}")
    print("     Larger N means each chunk covers more context but becomes")
    print("     more sensitive to small changes.\n")

    # --- Pros / Cons Summary ---
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  PROS vs CONS SUMMARY                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ✅ PROS:                                               │")
    print("  │    • Robust to mid-word insertions/deletions            │")
    print("  │    • Normalized 0–1 score (Dice coefficient)            │")
    print("  │    • No dependency on character position                │")
    print("  │    • Works well for longer keywords (more bigrams)      │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ❌ CONS:                                               │")
    print("  │    • Loses character order ('abc' ≈ 'cab')              │")
    print("  │    • Choice of N heavily affects results                │")
    print("  │    • Poor on very short strings (too few n-grams)       │")
    print("  │    • Cannot detect transpositions specifically          │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  → NEXT: Technique 10 (Tree Matching) scopes fuzzy     │")
    print("  │          search to the relevant tree level only         │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    demo()
