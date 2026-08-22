"""
Technique 11: Flat-Corpus Scan

Fallback when tree-walk (Technique 10) finds no match. Instead of
searching one tree level, compare the user's input against every
complete command in the system as a flat list.

Each token in the user's input is compared against the corresponding
token in each candidate command using prefix matching and edit distance.

No external libraries needed.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_tree import ALL_COMMANDS, is_variable


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


def _default_token_threshold(token_len):
    return 2 if token_len <= 4 else 4


def score_command(user_tokens, cmd_template, distance_fn=None,
                  token_threshold_fn=None):
    """Score how well user_tokens match a command template.

    Returns (matched_count, total_distance) or None if clearly unrelated.
    Lower total_distance is better. Higher matched_count is better.
    """
    if distance_fn is None:
        distance_fn = damerau_levenshtein
    if token_threshold_fn is None:
        token_threshold_fn = _default_token_threshold

    cmd_tokens = cmd_template.split()

    matched = 0
    total_dist = 0

    # Compare token by token up to the shorter length
    compare_len = min(len(user_tokens), len(cmd_tokens))
    for i in range(compare_len):
        user_tok = user_tokens[i]
        cmd_tok = cmd_tokens[i]

        if is_variable(cmd_tok):
            matched += 1
            continue

        # Exact or prefix match
        if cmd_tok.startswith(user_tok) or user_tok == cmd_tok:
            matched += 1
            continue

        # Fuzzy match
        dist = distance_fn(user_tok, cmd_tok)
        threshold = token_threshold_fn(len(cmd_tok))
        if dist <= threshold:
            matched += 1
            total_dist += dist
        else:
            total_dist += dist * 2  # penalty for poor match

    # Penalty for length mismatch
    length_diff = abs(len(user_tokens) - len(cmd_tokens))
    total_dist += length_diff * 2

    if matched == 0:
        return None

    return (matched, total_dist)


def flat_corpus_suggest(user_input, commands=None, top_n=5, distance_fn=None,
                       token_threshold_fn=None):
    """Scan all commands and return the best matches.

    Scores each command template against the user's tokenized input.
    """
    if commands is None:
        commands = ALL_COMMANDS

    user_tokens = user_input.strip().split()
    results = []

    for cmd in commands:
        score = score_command(
            user_tokens, cmd,
            distance_fn=distance_fn,
            token_threshold_fn=token_threshold_fn,
        )
        if score is not None:
            matched, total_dist = score
            results.append((cmd, matched, total_dist))

    # Sort by: most tokens matched (desc), then lowest distance (asc)
    results.sort(key=lambda x: (-x[1], x[2]))
    return results[:top_n]


def demo():
    print("=" * 60)
    print("Technique 11: Flat-Corpus Scan")
    print("=" * 60)

    print(f"\n  Full command corpus ({len(ALL_COMMANDS)} commands):\n")
    for cmd in ALL_COMMANDS:
        print(f"    {cmd}")

    tests = [
        ("debug", "partial first token — finds nested debug commands"),
        ("show rning", "hyphenated target — flat scan misses it, Technique 12 handles this"),
        ("ping", "single-token match"),
        ("sh bgp sum", "abbreviated multi-token"),
        ("confgure termnial", "typos in both tokens"),
    ]

    for user_input, note in tests:
        print(f"\n  Input: '{user_input}'  ({note})")
        results = flat_corpus_suggest(user_input, top_n=3)
        if results:
            for cmd, matched, dist in results:
                print(f"    → {cmd}  (matched={matched}, distance={dist})")
        else:
            print("    No matches found")

    # --- Shortcomings ---
    print("  Shortcomings:")
    print("  ─────────────")
    print("  1) False positives — unrelated commands surface due to coincidental matches:\n")
    results = flat_corpus_suggest("ping", top_n=5)
    for cmd, matched, dist in results:
        tag = "✓ correct" if "ping" in cmd else "✗ false positive"
        print(f"     → {cmd}  ({tag})")
    print("     Without tree-level scoping, 'ping' fuzzy-matches 'debug' tokens.\n")

    print("  2) Tokens are compared by position — a skipped middle keyword is not recovered:\n")
    results_skip = flat_corpus_suggest("sh sum", top_n=4)
    print("     Input: 'sh sum'  (hoping for 'show bgp summary')")
    for cmd, matched, dist in results_skip:
        print(f"     → {cmd}  (matched={matched}, distance={dist})")
    print("     'sum' is scored against 'bgp', not against 'summary'.")
    print("     Prefix abbreviations that line up ('sh bgp sum') still work.\n")

    print("  3) Cannot split hyphenated keywords:\n")
    results2 = flat_corpus_suggest("show rning config", top_n=3)
    has_running = any("running" in cmd for cmd, _, _ in results2)
    print(f"     Input: 'show rning config'")
    for cmd, matched, dist in results2:
        print(f"     → {cmd}  (matched={matched}, distance={dist})")
    if not has_running:
        print("     'show running-config' is missing — the scan treats")
        print("     'running-config' as one token and cannot match 'rning config'.")
        print("     Technique 12 (Hyphenated Handling) solves this.\n")
    else:
        print()

    # --- Pros / Cons Summary ---
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  PROS vs CONS SUMMARY                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ✅ PROS:                                               │")
    print("  │    • Catches cross-branch mistakes (tree-walk can't)    │")
    print("  │    • Handles abbreviated multi-token input ('sh bgp')   │")
    print("  │    • Completes a lone first keyword ('debug' → nested)  │")
    print("  │    • Good fallback — finds something when tree fails    │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ❌ CONS:                                               │")
    print("  │    • False positives from coincidental token matches    │")
    print("  │    • Cannot split hyphenated keywords                   │")
    print("  │    • O(commands × tokens) — slower than tree-walk       │")
    print("  │    • Positional only — skipped middle keywords miss     │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  → NEXT: Technique 12 (Hyphenated Handling) splits      │")
    print("  │          compound keywords for better matching          │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    demo()
