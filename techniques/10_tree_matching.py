"""
Technique 10: Context-Aware Tree Matching

Instead of comparing against every command in the system, walk the
command tree token by token. At the first token that fails to match,
collect only the valid sibling keywords at that tree level and run
fuzzy matching against that small set.

This prevents nonsensical cross-branch suggestions and is much faster
than a flat scan.

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


def tree_walk_suggest(user_input, tree=None, threshold=3, distance_fn=None):
    """Walk the command tree token by token. On the first mismatch,
    suggest close matches from the valid siblings at that level.

    distance_fn(s, t) defaults to unit-cost Damerau-Levenshtein.

    Returns:
        matched_prefix: tokens that matched exactly
        suggestions: list of (corrected_token, distance) for the failing token
        remaining_tokens: tokens after the failing one (unchecked)
    """
    if tree is None:
        tree = COMMAND_TREE
    if distance_fn is None:
        distance_fn = damerau_levenshtein

    tokens = user_input.strip().split()
    node = tree
    matched = []

    for idx, token in enumerate(tokens):
        keywords = get_keywords(node)
        variables = [k for k in node if is_variable(k)]

        # Exact match — advance into the subtree
        if token in node:
            matched.append(token)
            node = node[token]
            continue

        # Check if it matches a variable placeholder
        if variables:
            matched.append(token)
            node = node[variables[0]]
            continue

        # No match — fuzzy search against siblings at that level
        scored = []
        for kw in keywords:
            dist = distance_fn(token, kw)
            if dist <= threshold:
                scored.append((kw, dist))
        scored.sort(key=lambda x: x[1])

        remaining = tokens[idx + 1:]
        return matched, scored, remaining

    return matched, [], []


def demo():
    print("=" * 60)
    print("Technique 10: Context-Aware Tree Matching")
    print("=" * 60)

    print("\n  Command tree (partial):")
    print("    root")
    print("    ├── configure  →  terminal")
    print("    ├── ping  →  <IP>")
    print("    └── show")
    print("        ├── bgp →  neighbors, summary")
    print("        ├── greeting")
    print("        ├── interface")
    print("        ├── interfaces")
    print("        ├── ip  →  interface, route")
    print("        ├── running-config")
    print("        ├── terminal")
    print("        └── version")

    tests = [
        "show interfce",
        "show ip inerface",
        "show bpg summary",
        "confgure terminal",
        "shwo version",
    ]

    for cmd in tests:
        matched, suggestions, remaining = tree_walk_suggest(cmd)
        print(f"\n  Input: '{cmd}'")
        if matched:
            print(f"    Matched so far: {' '.join(matched)}")
        if suggestions:
            failing_token = cmd.split()[len(matched)]
            candidates = get_keywords(
                COMMAND_TREE
                if not matched
                else _walk_tree(COMMAND_TREE, matched)
            )
            print(f"    Failing token: '{failing_token}'")
            print(f"    Candidates at this level: {candidates}")
            print(f"    Suggestions:")
            for kw, dist in suggestions:
                full_cmd = " ".join(matched + [kw] + remaining)
                print(f"      → {full_cmd}  (distance {dist})")
        elif not matched:
            print("    No match at root level")
        else:
            print("    All tokens matched exactly")

    # --- Shortcomings ---
    print("\n  Shortcomings:")
    print("  ─────────────")
    print("  1) Only the first failing token is corrected — later tokens are unchecked:\n")
    cmd = "shwo interfce"
    matched, suggestions, remaining = tree_walk_suggest(cmd)
    print(f"     Input: '{cmd}'")
    if suggestions:
        for kw, dist in suggestions:
            full = " ".join(matched + [kw] + remaining)
            print(f"     Suggestion: '{full}'  (distance {dist})")
    print("     → 'shwo' is corrected to 'show', but 'interfce' passes")
    print("       through unchecked because the tree-walk stopped.\n")

    print("  2) No fallback — if no sibling matches, the search stops:\n")
    cmd2 = "show debugg"
    matched2, suggestions2, remaining2 = tree_walk_suggest(cmd2, threshold=1)
    print(f"     Input: '{cmd2}' (threshold=1)")
    print(f"     Suggestions: {suggestions2 if suggestions2 else 'none'}")
    print("     'debugg' is close to 'debug', but 'debug' lives at the root")
    print("     level, not under 'show'. The tree-walk cannot cross branches.")
    print("     Technique 11 (Flat-Corpus Scan) handles this.\n")

    # --- Pros / Cons Summary ---
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  PROS vs CONS SUMMARY                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ✅ PROS:                                               │")
    print("  │    • Scopes search to valid siblings only (fewer false+)│")
    print("  │    • Much faster than scanning all commands              │")
    print("  │    • Prevents nonsensical cross-branch suggestions      │")
    print("  │    • Shows which tokens already matched correctly       │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ❌ CONS:                                               │")
    print("  │    • Only corrects the FIRST failing token              │")
    print("  │    • Cannot cross branches (wrong parent = no results)  │")
    print("  │    • Requires a structured command tree                 │")
    print("  │    • Unchecked tokens after the error pass through      │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  → NEXT: Technique 11 (Flat-Corpus Scan) provides a    │")
    print("  │          fallback when tree-walk fails                  │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


def _walk_tree(tree, path):
    """Walk the tree along a list of tokens, return the final node."""
    node = tree
    for token in path:
        if token in node:
            node = node[token]
        else:
            for k in node:
                if is_variable(k):
                    node = node[k]
                    break
    return node


if __name__ == "__main__":
    demo()
