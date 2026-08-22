"""
Technique 1: Exact Prefix Matching

The simplest approach. Check whether the user's input is an exact prefix
of any valid command token. If one or more commands share that prefix,
suggest them all.

No external libraries needed.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_tree import COMMAND_TREE, get_keywords, SHOW_CANDIDATES


def prefix_match(user_input, candidates):
    """Return all candidates where user_input is an exact prefix."""
    return [c for c in candidates if c.startswith(user_input)]


def suggest(user_input, candidates):
    """Find prefix matches and format as numbered suggestions."""
    matches = prefix_match(user_input, candidates)
    return matches


def demo():
    print("=" * 60)
    print("Technique 1: Exact Prefix Matching")
    print("=" * 60)

    candidates = SHOW_CANDIDATES
    print(f"\nCandidate keywords under 'show': {candidates}\n")

    tests = [
        ("inter", "matches 'interface' and 'interfaces'"),
        ("v", "matches 'version'"),
        ("i", "matches 'interface', 'interfaces', 'ip'"),
        ("gre", "matches 'greeting'"),
        ("te", "matches 'terminal'"),
        ("xyz", "no valid prefix — no match"),
        ("interfce", "typo, not a valid prefix — no match"),
    ]

    for user_input, note in tests:
        matches = suggest(user_input, candidates)
        print(f"  Input: '{user_input}'  ({note})")
        if matches:
            for i, m in enumerate(matches, 1):
                print(f"    {i}) show {m}")
        else:
            print("    No suggestions")
        print()


    # --- Shortcomings ---
    print("  Shortcomings:")
    print("  ─────────────")
    print("  Prefix matching ONLY works when the typed text is a correct")
    print("  but incomplete beginning. Any mistake anywhere defeats it:\n")

    failures = [
        ("interfce", "typo in the middle"),
        ("shwo", "transposed characters"),
        ("intarface", "wrong character substitution"),
        ("nterface", "missing first character"),
    ]
    for user_input, note in failures:
        matches = suggest(user_input, candidates)
        status = "MISS" if not matches else "match"
        print(f"    '{user_input}' ({note}) → {status}")

    print("\n  All four are clearly 'interface', but prefix matching")
    print("  returns nothing. Fuzzy techniques (Technique 3+) fix this.\n")

    # --- Pros / Cons Summary ---
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  PROS vs CONS SUMMARY                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ✅ PROS:                                               │")
    print("  │    • Zero dependencies — pure string comparison         │")
    print("  │    • O(n) per candidate — fastest possible              │")
    print("  │    • Zero false positives — only exact beginnings match │")
    print("  │    • Trivial to implement (1 line of logic)             │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ❌ CONS:                                               │")
    print("  │    • Any typo anywhere → complete miss                  │")
    print("  │    • Transpositions → miss ('shwo' for 'show')          │")
    print("  │    • Missing first char → miss ('nterface')             │")
    print("  │    • Only useful when the user types carefully           │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  → NEXT: Technique 2 handles multi-token abbreviation   │")
    print("  │          Technique 3+ adds fuzzy matching for typos     │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    demo()
