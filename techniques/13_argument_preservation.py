"""
Technique 13: Variable Argument Preservation

CLI commands contain two kinds of tokens: keywords (fixed words like
'show', 'interface', 'bgp') and arguments (user-supplied values like
IP addresses, AS numbers, interface names).

The suggestion engine should only correct keywords. Arguments are data
and must be preserved verbatim — the engine has no basis for deciding
whether '10.0.0.1' is right or wrong.

No external libraries needed.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_tree import COMMAND_TREE, get_keywords, is_variable


def damerau_levenshtein(s, t):
    """Damerau-Levenshtein distance (self-contained copy)."""
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


def suggest_preserving_args(user_input, tree=None, threshold=3):
    """Walk the command tree correcting keywords but preserving arguments.

    At each tree level:
      - If the position expects a variable (<IP>, <ASN>, etc.), accept the
        user's token as-is without scoring or correcting it.
      - If the position expects a keyword, use fuzzy matching to find the
        closest keyword.

    Returns a list of (corrected_command, total_distance) tuples.
    """
    if tree is None:
        tree = COMMAND_TREE

    tokens = user_input.strip().split()
    return _walk(tokens, 0, tree, [], 0, threshold)


def _walk(tokens, idx, node, corrected, total_dist, threshold):
    """Recursive tree walk with argument preservation."""
    if idx >= len(tokens):
        return [(" ".join(corrected), total_dist)]

    token = tokens[idx]
    keywords = get_keywords(node)
    variables = [k for k in node if is_variable(k)]
    results = []

    # Try keyword matches first
    best_kw = []
    for kw in keywords:
        if kw == token:
            best_kw.append((kw, 0))
        else:
            dist = damerau_levenshtein(token, kw)
            if dist <= threshold:
                best_kw.append((kw, dist))

    best_kw.sort(key=lambda x: x[1])

    for kw, dist in best_kw[:3]:  # limit branching
        sub_results = _walk(
            tokens, idx + 1, node[kw],
            corrected + [kw], total_dist + dist, threshold,
        )
        results.extend(sub_results)

    # If this position accepts a variable argument, preserve the token as-is
    if variables:
        var_key = variables[0]
        sub_results = _walk(
            tokens, idx + 1, node[var_key],
            corrected + [token],  # preserve original argument
            total_dist, threshold,
        )
        results.extend(sub_results)

    # Deduplicate and sort
    seen = set()
    unique = []
    for cmd, dist in sorted(results, key=lambda x: x[1]):
        if cmd not in seen:
            seen.add(cmd)
            unique.append((cmd, dist))

    return unique


def demo():
    print("=" * 60)
    print("Technique 13: Variable Argument Preservation")
    print("=" * 60)

    tests = [
        (
            "neigbor 10.0.0.1 remote-as 65200",
            "keyword 'neigbor' corrected, IP and ASN preserved",
        ),
        (
            "show bgp neigbors 10.0.0.1 received-routes",
            "keyword 'neigbors' corrected, IP preserved",
        ),
        (
            "pnig 192.168.1.1",
            "keyword 'pnig' corrected, IP preserved",
        ),
        (
            "router bpg 65001",
            "keyword 'bpg' corrected, ASN preserved",
        ),
        (
            "show ip rout",
            "keyword 'rout' corrected (prefix match won't fire here, but DL catches it)",
        ),
    ]

    for user_input, note in tests:
        results = suggest_preserving_args(user_input)
        print(f"\n  Input: '{user_input}'")
        print(f"  Note:  {note}")
        if results:
            for cmd, dist in results[:3]:
                print(f"    → {cmd}  (total distance {dist})")
        else:
            print("    No suggestions found")

    # --- Shortcomings ---
    print("\n  Shortcomings:")
    print("  ─────────────")
    print("  1) Cannot detect malformed arguments — they pass through as-is:\n")
    results = suggest_preserving_args("ping 10.0.0.999")
    for cmd, dist in results[:1]:
        print(f"     Input: 'ping 10.0.0.999'")
        print(f"     → {cmd}  (total distance {dist})")
    print("     '10.0.0.999' is an invalid IP but the engine preserves it")
    print("     without complaint. Argument validation is a separate concern.\n")

    print("  2) Requires accurate tree metadata:")
    print("     If a tree position is mislabeled as a keyword instead of a")
    print("     variable, the engine will try to 'correct' the user's argument.")
    print("     If it is mislabeled as a variable instead of a keyword, the")
    print("     engine will skip a misspelled keyword without correcting it.\n")

    # --- Pros / Cons Summary ---
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  PROS vs CONS SUMMARY                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ✅ PROS:                                               │")
    print("  │    • User data (IPs, ASNs) never 'corrected' to junk    │")
    print("  │    • Keywords still get fuzzy-matched and fixed         │")
    print("  │    • Combines tree structure with argument awareness    │")
    print("  │    • Produces usable commands (not mangled arguments)    │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ❌ CONS:                                               │")
    print("  │    • Cannot validate argument format (bad IPs pass)     │")
    print("  │    • Requires correct tree metadata (keyword vs var)    │")
    print("  │    • Mislabeled tree nodes cause silent errors          │")
    print("  │    • Only preserves — does not suggest valid arguments  │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  → NEXT: Technique 14 (Positional Swap) handles tokens │")
    print("  │          typed in the wrong order                       │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    demo()
