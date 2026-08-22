"""
Technique 12: Hyphenated Keyword Handling

Users often type hyphenated keywords as separate words:
    'running config'  instead of  'running-config'
    'port channel'    instead of  'port-channel'

Standard edit distance treats the full hyphenated keyword as one token,
making the distance artificially large. This technique splits hyphenated
candidates on the hyphen and matches each segment independently.

No external libraries needed.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_tree import COMMAND_TREE, get_keywords


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


def match_hyphenated(user_tokens, start_idx, candidate):
    """Try to match user tokens starting at start_idx against a hyphenated candidate.

    Splits the candidate on hyphens and tries to match each segment against
    consecutive user tokens, using fuzzy matching on each segment.

    Returns:
        (total_distance, tokens_consumed)  if match succeeds
        None                               if match fails
    """
    if "-" not in candidate:
        return None

    segments = candidate.split("-")
    total_dist = 0
    consumed = 0

    for seg_idx, segment in enumerate(segments):
        token_idx = start_idx + consumed

        if token_idx >= len(user_tokens):
            # Ran out of user tokens — remaining segments unmatched
            total_dist += sum(len(s) for s in segments[seg_idx:])
            break

        user_tok = user_tokens[token_idx]
        dist = damerau_levenshtein(user_tok, segment)
        threshold = 2 if len(segment) <= 4 else 4

        if dist <= threshold:
            total_dist += dist
            consumed += 1
        elif seg_idx == 0:
            return None  # first segment must match
        else:
            total_dist += len(segment)

    return (total_dist, consumed)


def suggest_with_hyphen_handling(user_input, candidates, threshold=4):
    """Try each candidate with standard matching and hyphenated matching.

    For hyphenated candidates, also try matching user tokens as separate
    words corresponding to hyphen-separated segments.
    """
    user_tokens = user_input.strip().split()
    results = []

    for start_idx, token in enumerate(user_tokens):
        for candidate in candidates:
            if "-" in candidate:
                # Try hyphenated segment matching
                result = match_hyphenated(user_tokens, start_idx, candidate)
                if result is not None:
                    dist, consumed = result
                    if dist <= threshold:
                        results.append((candidate, dist, consumed))

            # Standard single-token matching
            dist = damerau_levenshtein(token, candidate)
            if dist <= threshold:
                results.append((candidate, dist, 1))

    # Deduplicate and sort by distance
    seen = set()
    unique = []
    for candidate, dist, consumed in sorted(results, key=lambda x: x[1]):
        if candidate not in seen:
            seen.add(candidate)
            unique.append((candidate, dist, consumed))

    return unique


def demo():
    print("=" * 60)
    print("Technique 12: Hyphenated Keyword Handling")
    print("=" * 60)

    # --- The problem ---
    print("\n  The problem with standard distance:\n")
    dist = damerau_levenshtein("rning", "running-config")
    print(f"    'rning' vs 'running-config' (whole): distance = {dist}")
    dist_seg = damerau_levenshtein("rning", "running")
    print(f"    'rning' vs 'running' (first segment): distance = {dist_seg}")
    print(f"    → Splitting on hyphen makes the match feasible\n")

    # --- Segment matching ---
    print("  Hyphenated segment matching examples:\n")
    candidates = get_keywords(COMMAND_TREE["show"])

    tests = [
        ("rning config", "show running-config"),
        ("running config", "show running-config"),
        ("rnning confg", "show running-config (typos in both segments)"),
    ]

    for user_input, note in tests:
        result = suggest_with_hyphen_handling(user_input, candidates)
        print(f"    Input: '{user_input}'  ({note})")
        if result:
            for candidate, dist, consumed in result[:3]:
                print(f"      → {candidate}  (distance={dist}, "
                      f"tokens_consumed={consumed})")
        else:
            print("      No match")
        print()

    # --- More examples with other hyphenated keywords ---
    print("  Other hyphenated keywords:\n")
    other_candidates = ["port-channel", "channel-group", "snmp-server"]

    other_tests = [
        ("port channel", "space instead of hyphen"),
        ("prot channel", "typo + space"),
        ("hannel grup", "typo in both segments"),
    ]

    for user_input, note in other_tests:
        result = suggest_with_hyphen_handling(user_input, other_candidates)
        print(f"    Input: '{user_input}'  ({note})")
        if result:
            for candidate, dist, consumed in result[:3]:
                print(f"      → {candidate}  (distance={dist}, "
                      f"tokens_consumed={consumed})")
        else:
            print("      No match")
    # --- Shortcomings ---
    print("  Shortcomings:")
    print("  ─────────────")
    print("  1) Cannot handle reversed segment order:\n")
    result = suggest_with_hyphen_handling("config running", ["running-config"])
    has_match = any(c == "running-config" for c, _, _ in result)
    print(f"     Input: 'config running'  (segments reversed)")
    if has_match:
        for c, d, consumed in result:
            print(f"     → {c}  (distance={d})")
    else:
        print("     No match — the engine expects segments in order.")
        print("     Technique 14 (Positional Swap) can handle this.\n")

    print("  2) Adds complexity — must detect hyphens, split, absorb tokens:")
    print("     Each hyphenated candidate requires multi-token lookahead,")
    print("     and false absorptions are possible if a user token")
    print("     coincidentally matches a post-hyphen segment of an")
    print("     unrelated command.\n")

    # --- Pros / Cons Summary ---
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  PROS vs CONS SUMMARY                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ✅ PROS:                                               │")
    print("  │    • 'running config' matches 'running-config' (natural)│")
    print("  │    • Tolerates typos in individual segments             │")
    print("  │    • Correctly consumes multiple user tokens as one     │")
    print("  │    • Works with any hyphenated keyword automatically    │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ❌ CONS:                                               │")
    print("  │    • Cannot handle reversed segments ('config running') │")
    print("  │    • Multi-token lookahead adds implementation cost     │")
    print("  │    • Possible false absorptions with unrelated tokens   │")
    print("  │    • Only handles hyphen delimiter (not underscore etc.)│")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  → NEXT: Technique 13 (Argument Preservation) ensures   │")
    print("  │          user data like IPs is never 'corrected'        │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    demo()
