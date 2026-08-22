"""
Technique 2: Multi-token Prefix Abbreviation

Expand abbreviated tokens positionally against the command tree. Each
token in the user's input is matched as a prefix against the keywords
at the corresponding tree level. Experienced operators use this naturally:
    sh bgp sum  →  show bgp summary
    conf t      →  configure terminal

No external libraries needed.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_tree import COMMAND_TREE, get_keywords, is_variable


def expand_abbreviations(tokens, tree):
    """Recursively expand abbreviated tokens against the command tree.

    Each token is matched as a prefix against the keywords at the current
    tree level. Returns all possible fully-expanded command strings.
    """
    if not tokens:
        return [""]

    token = tokens[0]
    remaining = tokens[1:]
    results = []

    keywords = get_keywords(tree)
    matches = [kw for kw in keywords if kw.startswith(token)]

    if not matches:
        return []

    for match in matches:
        subtree = tree[match]
        if remaining and subtree:
            for expansion in expand_abbreviations(remaining, subtree):
                results.append(f"{match} {expansion}".strip())
        else:
            if remaining:
                results.append(match + " " + " ".join(remaining))
            else:
                results.append(match)

    return results


def suggest(user_input, tree=None):
    """Expand an abbreviated command string against the tree."""
    if tree is None:
        tree = COMMAND_TREE
    tokens = user_input.strip().split()
    return expand_abbreviations(tokens, tree)


def demo():
    print("=" * 60)
    print("Technique 2: Multi-token Prefix Abbreviation")
    print("=" * 60)

    tests = [
        ("sh bgp sum", "show bgp summary"),
        ("sh ip int", "show ip interface"),
        ("sh int", "ambiguous — interface or interfaces?"),
        ("conf t", "configure terminal"),
        ("sh ver", "show version"),
        ("sh v", "show version"),
        ("sh b n", "show bgp neighbors"),
        ("shw ver", "'shw' is not a valid prefix of 'show' — fails"),
        ("p", "single match — only 'ping' starts with 'p'"),
    ]

    for abbrev, note in tests:
        results = suggest(abbrev)
        print(f"\n  Input: '{abbrev}'  ({note})")
        if results:
            for i, r in enumerate(results, 1):
                print(f"    {i}) {r}")
        else:
            print("    No expansion found")

    # --- Shortcomings ---
    print("\n  Shortcomings:")
    print("  ─────────────")
    shortcomings = [
        ("sh sum", "skipped keyword — 'sum' is level 3 under 'show bgp', not level 2"),
        ("shw ver", "typo in abbreviation — 'shw' is not a valid prefix of any root keyword"),
        ("sh i", "short prefix — matches interface, interfaces, and ip"),
    ]
    for abbrev, note in shortcomings:
        results = suggest(abbrev)
        print(f"\n    Input: '{abbrev}'  ({note})")
        if results:
            for i, r in enumerate(results, 1):
                print(f"      {i}) {r}")
        else:
            print("      No expansion found")

    print("\n  Abbreviation requires positional alignment with the tree and")
    print("  does not tolerate typos within the abbreviated token.\n")

    # --- Pros / Cons Summary ---
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  PROS vs CONS SUMMARY                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ✅ PROS:                                               │")
    print("  │    • Matches expert shorthand ('sh bgp sum')            │")
    print("  │    • Tree-aware — expands each token at its level       │")
    print("  │    • No false positives when abbreviation is unambiguous │")
    print("  │    • No external dependencies                           │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ❌ CONS:                                               │")
    print("  │    • Any typo in abbreviated token → total failure      │")
    print("  │    • Cannot skip levels ('sh sum' ≠ 'show bgp summary') │")
    print("  │    • Short prefixes are ambiguous ('sh i' → 3 matches)  │")
    print("  │    • Requires strict positional alignment with tree     │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  → NEXT: Technique 3 (Levenshtein) tolerates typos     │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    demo()
