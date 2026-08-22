"""
Technique 14: Positional Swap Detection

Catches errors where the user typed the correct tokens but in the wrong
order. For example:
    'router 65001 bgp'  instead of  'router bgp 65001'

Standard fuzzy matching cannot detect this because every token is spelled
correctly — they are just in the wrong position. This technique tries
permutations of the unmatched tokens to find a valid arrangement.

No external libraries needed.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from itertools import permutations
from command_tree import COMMAND_TREE, get_keywords, is_variable


def detect_swap(user_input, tree=None):
    """Try to match user tokens against command templates by reordering.

    Walks the tree to find where matching breaks down, then tries
    permutations of the remaining tokens to find a valid fit.

    Returns a list of (reordered_command, swap_description) tuples.
    """
    if tree is None:
        tree = COMMAND_TREE

    tokens = user_input.strip().split()
    return _try_reorder(tokens, tree, [])


def _try_reorder(tokens, node, matched):
    """Recursively try to fit tokens into the command tree, allowing reordering."""
    if not tokens:
        return [(" ".join(matched), "exact match" if not matched else "reordered")]

    results = []
    keywords = get_keywords(node)
    variables = [k for k in node if is_variable(k)]

    # Try each token in the remaining set at the current position
    for i, token in enumerate(tokens):
        remaining = tokens[:i] + tokens[i + 1:]

        # Does this token match a keyword at the current level?
        if token in keywords:
            sub = _try_reorder(remaining, node[token], matched + [token])
            results.extend(sub)

        # Does this token fit a variable slot?
        if variables and token not in keywords:
            var_key = variables[0]
            sub = _try_reorder(remaining, node[var_key], matched + [token])
            results.extend(sub)

    return results


def suggest_swaps(user_input, tree=None, max_results=5):
    """Find valid commands by reordering the user's tokens.

    Only returns results where a complete, valid command is formed
    (all tokens consumed, all positions filled).
    """
    if tree is None:
        tree = COMMAND_TREE

    tokens = user_input.strip().split()
    original = " ".join(tokens)

    results = detect_swap(user_input, tree)

    # Filter to valid reorderings that differ from the original
    unique = []
    seen = set()
    for cmd, desc in results:
        if cmd not in seen:
            seen.add(cmd)
            is_swap = cmd != original
            unique.append((cmd, is_swap))

    # Prioritize actual swaps, then exact matches
    unique.sort(key=lambda x: (not x[1],))
    return unique[:max_results]


def demo():
    print("=" * 60)
    print("Technique 14: Positional Swap Detection")
    print("=" * 60)

    tests = [
        (
            "router 65001 bgp",
            "keyword 'bgp' and argument '65001' are swapped",
        ),
        (
            "neighbor remote-as 10.0.0.1 65200",
            "IP and keyword 'remote-as' are swapped",
        ),
        (
            "show version",
            "already correct — no swap needed",
        ),
        (
            "65001 bgp router",
            "all three tokens out of order",
        ),
        (
            "ping 10.0.0.1",
            "already correct — argument in right position",
        ),
    ]

    for user_input, note in tests:
        results = suggest_swaps(user_input)
        print(f"\n  Input: '{user_input}'")
        print(f"  Note:  {note}")
        if results:
            for cmd, is_swap in results:
                label = "SWAP" if is_swap else "exact"
                print(f"    → {cmd}  [{label}]")
        else:
            print("    No valid reordering found")

    # --- Shortcomings ---
    print("\n  Shortcomings:")
    print("  ─────────────")
    print("  1) Combinatorial complexity — O(N!) permutations:")
    print("     Manageable for CLI commands (rarely >6 tokens), but")
    print("     the tree structure must prune aggressively.\n")

    print("  2) Cannot distinguish swaps from different valid commands:")
    cmd = "neighbor remote-as 10.0.0.1 65200"
    results = suggest_swaps(cmd)
    print(f"     Input: '{cmd}'")
    for c, is_swap in results:
        label = "correct reorder" if c == "neighbor 10.0.0.1 remote-as 65200" else "false match"
        print(f"     → {c}  [{label}]")
    print("     Both orderings are valid because the tree treats <IP> and")
    print("     <ASN> as interchangeable variable slots.\n")

    print("  3) Does not help with misspelled tokens — only reorders:")
    results2 = suggest_swaps("rotuer bgp 65001")
    print(f"     Input: 'rotuer bgp 65001'")
    print(f"     Results: {len(results2)} matches")
    if not results2:
        print("     'rotuer' is not a valid keyword in any position, so no")
        print("     reordering can produce a valid command.\n")
    else:
        for c, _ in results2:
            print(f"     → {c}")
        print()

    # --- Pros / Cons Summary ---
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  PROS vs CONS SUMMARY                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ✅ PROS:                                               │")
    print("  │    • Catches correctly-spelled but wrong-order tokens   │")
    print("  │    • Uses tree to prune invalid permutations quickly    │")
    print("  │    • Handles full reversal ('65001 bgp router')         │")
    print("  │    • Complements fuzzy matching (different error class) │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ❌ CONS:                                               │")
    print("  │    • O(N!) worst case — only practical for short inputs │")
    print("  │    • Cannot fix misspelled tokens (only reorders)       │")
    print("  │    • Variable slots create ambiguous reorderings        │")
    print("  │    • No way to prefer 'more natural' ordering           │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  → NEXT: Technique 15 (AI Semantic) handles cross-vendor│")
    print("  │          syntax that no string algorithm can match      │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    demo()
