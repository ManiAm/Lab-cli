"""
Technique 16: Combined Pipeline

Chains multiple techniques into a single suggestion engine. Each stage
handles a different class of mistake, and the pipeline is ordered so
that fast, high-confidence methods run first:

    1. Context-Aware Tree Walk with weighted Damerau-Levenshtein and
       hyphenated keyword splitting (Techniques 4, 5, 10, 12)
    2. Flat-Corpus Scan with prefix abbreviation and hyphenated
       matching (Techniques 1, 2, 11, 12)
    3. Positional Swap Detection (Technique 14)
    4. AI Semantic Backend (optional, Technique 15)

Argument values (IPs, ASNs, names) are preserved verbatim in all
stages (Technique 13).

The scorer is Technique 5 on Technique 4: Damerau-Levenshtein with
operation weights (transposition 0, insertion 1, substitution 2,
deletion 3).

No external libraries needed.
"""

import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib
from command_tree import COMMAND_TREE, ALL_COMMANDS, get_keywords, is_variable

_t5 = importlib.import_module("05_weighted_edit_costs")
_t14 = importlib.import_module("14_positional_swap")
_t15 = importlib.import_module("15_ai_semantic")

weighted_damerau_levenshtein = _t5.weighted_damerau_levenshtein
suggest_swaps = _t14.suggest_swaps
semantic_suggest = _t15.semantic_suggest

STAGE1_THRESHOLD = 3
STRONG_MATCH = 1
MAX_RESULTS = 3

W_INS = 1  # insertion weight (used for unmatched hyphen segments)


def _weighted_token_threshold(token_len):
    """Accept one deletion (cost 3) on short tokens; a bit more on long ones."""
    if token_len <= 4:
        return 3
    if token_len <= 8:
        return 4
    return 5


def _match_hyphenated(user_tokens, start_idx, candidate):
    """Hyphenated matching using the weighted scorer (Technique 12).

    Splits the candidate on hyphens and matches each segment against
    consecutive user tokens. Returns (total_cost, tokens_consumed) or None.
    """
    if "-" not in candidate:
        return None
    segments = candidate.split("-")
    total = 0
    consumed = 0
    for seg_idx, segment in enumerate(segments):
        token_idx = start_idx + consumed
        if token_idx >= len(user_tokens):
            if seg_idx == 0:
                return None
            total += len(segment) * W_INS
            break
        dist = weighted_damerau_levenshtein(user_tokens[token_idx], segment)
        thresh = _weighted_token_threshold(len(segment))
        if dist <= thresh:
            total += dist
            consumed += 1
        elif seg_idx == 0:
            return None
        else:
            total += len(segment) * W_INS
    if consumed == 0:
        return None
    return (total, consumed)


def _classify_edit(source, target, cost):
    """Identify the dominant edit operation for display purposes."""
    s, t = source.lower(), target.lower()
    ls, lt = len(s), len(t)

    if s == t:
        return "exact match"

    if cost == 0 and ls == lt:
        for i in range(ls - 1):
            if s[i] != t[i] and s[i] == t[i + 1] and s[i + 1] == t[i]:
                return f"transposition: '{s[i]}' \u2194 '{s[i+1]}'"
        return "transposition"

    if cost == 1 and lt == ls + 1:
        for i in range(lt):
            if s == t[:i] + t[i + 1:]:
                return f"insertion: add '{t[i]}'"
        return "insertion"

    if cost == 2 and ls == lt:
        diffs = [(i, s[i], t[i]) for i in range(ls) if s[i] != t[i]]
        if len(diffs) == 1:
            i, sc, tc = diffs[0]
            return f"substitution: '{sc}' \u2192 '{tc}'"
        return "substitution"

    if cost == 3 and ls == lt + 1:
        for i in range(ls):
            if t == s[:i] + s[i + 1:]:
                return f"deletion: remove '{s[i]}'"
        return "deletion"

    return f"multiple edits (cost {cost})"


# ---------------------------------------------------------------------------
# Stage 1: recursive tree walk (Techniques 4, 5, 10, 12, 13)
# ---------------------------------------------------------------------------

def _stage1_walk(tokens, idx, node, prefix, cost_so_far):
    """Walk from *node* starting at tokens[idx]. Returns list of (cmd, cost)."""
    if idx >= len(tokens):
        return [(" ".join(prefix), cost_so_far)] if prefix else []

    token = tokens[idx]
    keywords = get_keywords(node)
    variables = [k for k in node if is_variable(k)]

    for kw in keywords:
        if token.lower() == kw.lower():
            return _stage1_walk(tokens, idx + 1, node[kw],
                               prefix + [kw], cost_so_far)

    hits = []
    for kw in keywords:
        if "-" in kw:
            result = _match_hyphenated(tokens, idx, kw)
            if result is not None:
                cost, consumed = result
                if cost <= _weighted_token_threshold(len(kw)):
                    hits.append((kw, cost, consumed))
                continue
        dist = weighted_damerau_levenshtein(token, kw)
        if dist <= STAGE1_THRESHOLD:
            hits.append((kw, dist, 1))

    hits.sort(key=lambda x: x[1])

    if hits:
        results = []
        for kw, cost, consumed in hits[:MAX_RESULTS]:
            results.extend(
                _stage1_walk(tokens, idx + consumed, node[kw],
                             prefix + [kw], cost_so_far + cost)
            )
        return results

    if variables:
        return _stage1_walk(tokens, idx + 1, node[variables[0]],
                            prefix + [token], cost_so_far)

    leftover = prefix + tokens[idx:]
    return [(" ".join(leftover), cost_so_far + 99)] if leftover else []


def stage1(tokens, tree):
    """Run Stage 1 and filter out stuck paths."""
    original = " ".join(tokens)
    raw = _stage1_walk(tokens, 0, tree, [], 0)
    results = []
    for cmd, cost in raw:
        if cost >= 99 or (cmd == original and cost == 0):
            continue
        results.append((cmd, cost, "tree-walk"))
    results.sort(key=lambda x: x[1])
    return results


# ---------------------------------------------------------------------------
# Stage 2: flat-corpus scan (Techniques 1, 2, 11, 12, 13)
# ---------------------------------------------------------------------------

def _score_command(user_tokens, cmd_template):
    """Score user_tokens against a command template.

    Handles prefix abbreviation, hyphenated keywords, and variable slots.
    Returns (matched_count, total_cost, display_string) or None.
    """
    cmd_tokens = cmd_template.split()
    u = 0
    matched = 0
    total = 0
    display = []

    for cmd_tok in cmd_tokens:
        if u >= len(user_tokens):
            display.append(cmd_tok)
            continue

        if is_variable(cmd_tok):
            display.append(user_tokens[u])
            matched += 1
            u += 1
            continue

        token = user_tokens[u]

        if token.lower() == cmd_tok.lower():
            display.append(cmd_tok)
            matched += 1
            u += 1
            continue
        if cmd_tok.lower().startswith(token.lower()) and token:
            display.append(cmd_tok)
            matched += 1
            u += 1
            continue

        if "-" in cmd_tok:
            result = _match_hyphenated(user_tokens, u, cmd_tok)
            if result is not None:
                cost, consumed = result
                if cost <= _weighted_token_threshold(len(cmd_tok)):
                    display.append(cmd_tok)
                    matched += 1
                    total += cost
                    u += consumed
                    continue

        dist = weighted_damerau_levenshtein(token, cmd_tok)
        if len(token) <= 2 and dist > 1:
            return None
        if len(token) * 2 >= len(cmd_tok) and dist <= _weighted_token_threshold(len(cmd_tok)):
            display.append(cmd_tok)
            matched += 1
            total += dist
            u += 1
            continue

        return None

    if matched == 0:
        return None
    extra = max(0, len(user_tokens) - u)
    total += extra * 2
    return (matched, total, " ".join(display))


def stage2(tokens, commands):
    """Run Stage 2 across all commands."""
    results = []
    for cmd_template in commands:
        scored = _score_command(tokens, cmd_template)
        if scored is None:
            continue
        matched_count, total, display = scored
        results.append((display, total, "flat-scan", matched_count))
    results.sort(key=lambda x: (-x[3], x[1]))
    out = []
    seen = set()
    for display, total, src, _ in results:
        if display in seen:
            continue
        seen.add(display)
        out.append((display, total, src))
        if len(out) >= MAX_RESULTS * 3:
            break
    return out


# ---------------------------------------------------------------------------
# Combine
# ---------------------------------------------------------------------------

def combined_suggest(user_input, tree=None, enable_ai=False, max_results=3):
    """Run the full suggestion pipeline."""
    if tree is None:
        tree = COMMAND_TREE

    tokens = user_input.strip().split()
    candidates = []

    candidates.extend(stage1(tokens, tree))

    tree_strong = any(cost <= STRONG_MATCH for _, cost, _ in candidates)
    if not tree_strong:
        candidates.extend(stage2(tokens, ALL_COMMANDS))

    swap_results = suggest_swaps(user_input, tree)
    for cmd, is_swap in swap_results:
        if is_swap:
            candidates.append((cmd, 0, "swap"))

    if enable_ai and not any(d <= STRONG_MATCH for _, d, _ in candidates):
        ai_results = semantic_suggest(user_input)
        for cmd, vendor in ai_results:
            candidates.append((cmd, 0.5, f"ai-{vendor}"))

    seen = set()
    unique = []
    original = user_input.strip()
    for cmd, dist, source in sorted(candidates, key=lambda x: x[1]):
        if cmd == original:
            continue
        if cmd not in seen:
            seen.add(cmd)
            unique.append((cmd, dist, source))

    return unique[:max_results]


# ---------------------------------------------------------------------------
# Verbose demo helpers
# ---------------------------------------------------------------------------

P = "  \u2502  "  # vertical bar prefix for stage output


def _trace_stage1(tokens, tree):
    """Walk the tree with verbose output. Returns the stage 1 results."""
    print("  \u250c\u2500 Stage 1: Tree Walk \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
    node = tree
    idx = 0
    had_accepted = False
    running_cost = 0

    while idx < len(tokens):
        token = tokens[idx]
        keywords = get_keywords(node)
        variables = [k for k in node if is_variable(k)]

        exact = None
        for kw in keywords:
            if token.lower() == kw.lower():
                exact = kw
                break

        if exact:
            children = get_keywords(node.get(exact, {}))
            if children:
                print(f"{P}Token '{token}': exact match (cost 0, running total: {running_cost})"
                      f" \u2192 enter '{exact}' subtree")
                print(f"{P}  children: {', '.join(children)}")
            else:
                print(f"{P}Token '{token}': exact match (cost 0, running total: {running_cost})"
                      f" \u2192 '{exact}' (leaf)")
            node = node[exact]
            idx += 1
            continue

        if variables and not keywords:
            print(f"{P}Token '{token}': variable slot (cost 0, running total: {running_cost})"
                  f" \u2192 keep as argument value")
            node = node[variables[0]]
            idx += 1
            continue

        print(f"{P}Token '{token}': no exact match")
        if keywords:
            print(f"{P}  Candidates at this level: {', '.join(keywords)}")

        scores = []
        for kw in keywords:
            if "-" in kw:
                result = _match_hyphenated(tokens, idx, kw)
                if result is not None:
                    cost, consumed = result
                    thresh = _weighted_token_threshold(len(kw))
                    accepted = cost <= thresh
                    consumed_text = " + ".join(
                        f"'{tokens[idx + i]}'" for i in range(consumed)
                        if idx + i < len(tokens)
                    )
                    scores.append((kw, cost, thresh, accepted, consumed,
                                   f"hyphen split: {consumed_text} \u2192 segments"))
                    continue
            dist = weighted_damerau_levenshtein(token, kw)
            thresh = STAGE1_THRESHOLD
            accepted = dist <= thresh
            edit = _classify_edit(token, kw, dist)
            scores.append((kw, dist, thresh, accepted, 1, edit))

        scores.sort(key=lambda x: x[1])
        print(f"{P}  Scoring '{token}' vs each candidate:")
        for kw, cost, thresh, accepted, consumed, edit in scores:
            mark = "\u2713" if accepted else "\u2717"
            extra = f", consumed {consumed} tokens" if consumed > 1 else ""
            print(f"{P}    {kw:20s} cost {cost:3}  (threshold {thresh}) "
                  f" {mark}  {edit}{extra}")

        had_accepted = any(s[3] for s in scores)

        best = [s for s in scores if s[3]]
        if best:
            best_kw, best_cost, _, _, best_consumed, best_edit = best[0]
            running_cost += best_cost
            print(f"{P}")
            children = get_keywords(node.get(best_kw, {}))
            if children:
                print(f"{P}Best: '{best_kw}' (cost {best_cost}, running total: {running_cost})"
                      f" \u2192 enter '{best_kw}' subtree")
                print(f"{P}  children: {', '.join(children)}")
            else:
                print(f"{P}Best: '{best_kw}' (cost {best_cost}, running total: {running_cost})"
                      " (leaf)")
            node = node[best_kw]
            idx += best_consumed
            continue

        break

    results = stage1(tokens, tree)
    if results:
        print(f"{P}")
        print(f"{P}Results:")
        for cmd, cost, src in results:
            print(f"{P}  \u2192 {cmd}  (cost {cost})")
        best_cost = results[0][1]
        if best_cost <= STRONG_MATCH:
            print(f"{P}")
            print(f"{P}\u2605 Strong match (cost {best_cost} \u2264 {STRONG_MATCH}) "
                  "\u2192 Stage 2 will be SKIPPED")
        else:
            print(f"{P}")
            print(f"{P}No strong match (best cost {best_cost} > {STRONG_MATCH}) "
                  "\u2192 Stage 2 will run")
    else:
        print(f"{P}")
        if idx == len(tokens):
            print(f"{P}All tokens matched exactly. No failing token to correct.")
        elif had_accepted:
            print(f"{P}Candidates above were accepted, but the walk could not")
            print(f"{P}complete: remaining tokens were too far from any keyword.")
        else:
            print(f"{P}No candidates within threshold.")
        print(f"{P}No strong match \u2192 Stage 2 will run")

    print("  \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
    return results


def _score_command_verbose(user_tokens, cmd_template):
    """Like _score_command but returns rejection detail on failure.

    Returns (matched_count, total_cost, display_string, token_details) on
    success, or (None, None, None, reject_reason) on failure.
    Each token_detail is (user_tok, cmd_tok, method_str).
    """
    cmd_tokens = cmd_template.split()
    u = 0
    matched = 0
    total = 0
    display = []
    details = []

    for cmd_tok in cmd_tokens:
        if u >= len(user_tokens):
            display.append(cmd_tok)
            continue

        token = user_tokens[u]

        if is_variable(cmd_tok):
            display.append(token)
            details.append((token, cmd_tok, "argument slot: keep as typed"))
            matched += 1
            u += 1
            continue

        if token.lower() == cmd_tok.lower():
            display.append(cmd_tok)
            details.append((token, cmd_tok, "exact match"))
            matched += 1
            u += 1
            continue

        if cmd_tok.lower().startswith(token.lower()) and token:
            display.append(cmd_tok)
            details.append((token, cmd_tok, "prefix expansion"))
            matched += 1
            u += 1
            continue

        if "-" in cmd_tok:
            result = _match_hyphenated(user_tokens, u, cmd_tok)
            if result is not None:
                cost, consumed = result
                if cost <= _weighted_token_threshold(len(cmd_tok)):
                    display.append(cmd_tok)
                    parts = " + ".join(f"'{user_tokens[u+i]}'"
                                       for i in range(consumed)
                                       if u + i < len(user_tokens))
                    details.append((parts, cmd_tok,
                                    f"hyphen match (cost {cost})"))
                    matched += 1
                    total += cost
                    u += consumed
                    continue

        dist = weighted_damerau_levenshtein(token, cmd_tok)
        thresh = _weighted_token_threshold(len(cmd_tok))
        if len(token) <= 2 and dist > 1:
            reject = (f"'{token}' vs '{cmd_tok}': cost {dist}, "
                      f"token too short for fuzzy match")
            return (None, None, None, reject)
        if len(token) * 2 < len(cmd_tok):
            reject = (f"'{token}' vs '{cmd_tok}': cost {dist}, "
                      f"token too short relative to keyword")
            return (None, None, None, reject)
        if dist <= thresh:
            display.append(cmd_tok)
            edit = _classify_edit(token, cmd_tok, dist)
            details.append((token, cmd_tok, edit))
            matched += 1
            total += dist
            u += 1
            continue

        reject = (f"'{token}' vs '{cmd_tok}': cost {dist} "
                  f"exceeds threshold {thresh}")
        return (None, None, None, reject)

    if matched == 0:
        return (None, None, None, "no tokens matched")
    extra = max(0, len(user_tokens) - u)
    total += extra * 2
    return (matched, total, " ".join(display), details)


def _trace_stage2(tokens, skip):
    """Run Stage 2 with verbose output."""
    print("  \u250c\u2500 Stage 2: Flat-Corpus Scan \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
    if skip:
        print(f"{P}SKIPPED (Stage 1 produced a strong match)")
        print("  \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
        return []

    total_cmds = len(ALL_COMMANDS)
    print(f"{P}Scanning all {total_cmds} known commands against "
          f"input tokens: {tokens}")
    print(f"{P}")

    accepted = []
    rejected = []

    for tmpl in ALL_COMMANDS:
        matched, cost, display, info = _score_command_verbose(tokens, tmpl)
        if matched is None:
            rejected.append((tmpl, info))
        else:
            accepted.append((tmpl, matched, cost, display, info))

    accepted.sort(key=lambda x: (-x[1], x[2]))

    if rejected:
        print(f"{P}Rejected {len(rejected)}/{total_cmds} commands:")
        for tmpl, reason in rejected:
            print(f"{P}  \u2717 {tmpl:40s} {reason}")
        print(f"{P}")

    if accepted:
        print(f"{P}Accepted {len(accepted)}/{total_cmds} commands:")
        for tmpl, matched, cost, display, details in accepted:
            print(f"{P}")
            print(f"{P}  \u2713 {display}  (cost {cost})")
            for ut, ct, method in details:
                print(f"{P}      {ut} \u2192 '{ct}': {method}")
    else:
        print(f"{P}No matches found")

    print("  \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
    results = stage2(tokens, ALL_COMMANDS)
    return results


def _trace_stage3(user_input, tree):
    """Run Stage 3 with verbose output."""
    print("  \u250c\u2500 Stage 3: Positional Swap \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
    swap_results = suggest_swaps(user_input, tree)
    swaps = [(cmd, is_swap) for cmd, is_swap in swap_results if is_swap]
    tokens = user_input.strip().split()

    if not swaps:
        n = len(tokens)
        if n < 2:
            print(f"{P}Only {n} token \u2192 nothing to swap")
        elif n > 6:
            print(f"{P}{n} tokens \u2192 too many to try permutations")
        else:
            print(f"{P}Tried permutations of {n} tokens: no valid reordering found")
    else:
        for cmd, _ in swaps:
            reordered = cmd.split()
            moves = []
            for i, (orig, new) in enumerate(zip(tokens, reordered)):
                if orig != new:
                    moves.append(f"position {i+1}: '{orig}' \u2192 '{new}'")
            print(f"{P}\u2192 {cmd}  (cost 0)")
            for m in moves:
                print(f"{P}    {m}")

    print("  \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
    return swaps


def _trace_stage4(user_input, enable_ai, has_strong):
    """Run Stage 4 with verbose output."""
    print("  \u250c\u2500 Stage 4: AI Backend \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
    ai_results = []
    if not enable_ai:
        print(f"{P}SKIPPED (AI not enabled)")
    elif has_strong:
        print(f"{P}SKIPPED (strong match already found)")
    else:
        from importlib import import_module as _imp
        _key = _imp("15_ai_semantic")._load_api_key()
        if not _key:
            print(f"{P}SKIPPED (OPENAI_API_KEY not set)")
        else:
            print(f"{P}No strong local match \u2192 querying OpenAI (gpt-4o-mini)")
            ai_results = semantic_suggest(user_input)
            for cmd, vendor in ai_results:
                print(f"{P}\u2192 {cmd}  (vendor: {vendor})")
            if not ai_results:
                print(f"{P}AI returned no suggestions")
    print("  \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
    return ai_results


def _demo_run(user_input, enable_ai=False):
    """Run the full pipeline with stage-by-stage verbose output."""
    tokens = user_input.strip().split()

    print(f"\n{'=' * 64}")
    print(f"  Input: '{user_input}'")
    print(f"{'=' * 64}")

    # Stage 1
    s1 = _trace_stage1(tokens, COMMAND_TREE)
    tree_strong = any(cost <= STRONG_MATCH for _, cost, _ in s1)

    # Stage 2
    s2 = _trace_stage2(tokens, skip=tree_strong)

    # Stage 3
    swaps = _trace_stage3(user_input, COMMAND_TREE)

    # Stage 4
    has_strong = tree_strong or any(
        cost <= STRONG_MATCH for _, cost, _ in s1 + s2
    ) or bool(swaps)
    ai = _trace_stage4(user_input, enable_ai, has_strong)

    # Final results
    results = combined_suggest(user_input, enable_ai=enable_ai)
    print()
    if results:
        print("  Final results (deduplicated, sorted by cost):")
        for i, (cmd, dist, source) in enumerate(results, 1):
            print(f"    {i}) {cmd}  (source: {source}, cost: {dist})")
    else:
        print("  Final results: no suggestions")
    print()


def demo(ai_enabled=False):
    print("=" * 64)
    print("  Technique 16: Combined Pipeline — Verbose Demo")
    print("=" * 64)

    print("\n  Pipeline stages:")
    print("    1. Tree walk + weighted Damerau-Levenshtein + hyphenated")
    print("       keyword splitting (Techniques 4, 5, 10, 12)")
    print("    2. Flat-Corpus Scan (fallback for structural mismatches)")
    print("    3. Positional Swap Detection (reordering errors)")
    print("    4. AI Semantic Backend (cross-vendor, opt-in)")
    print()
    print("  Weighted edit costs:")
    print("    Transposition = 0   Insertion = 1")
    print("    Substitution  = 2   Deletion  = 3")
    print()
    print("  Strong match: cost <= 1 (skips Stage 2 and Stage 4)")
    print("  Stage 1 threshold: cost <= 3")
    print(f"  AI backend: {'ENABLED (--ai)' if ai_enabled else 'DISABLED (use --ai to enable)'}")

    tests = [
        # --- Edit types (README examples) ---
        ("show interfce",
         "Insertion (cost 1, strong match)"),
        ("show intarface",
         "Substitution (cost 2, NOT strong)"),
        ("show vversion",
         "Deletion (cost 3, NOT strong)"),
        ("shwo version",
         "Transposition (cost 0, strong match)"),

        # --- Multiple typos with accumulated cost ---
        ("show bpg sumary",
         "Two typos: transposition (cost 0) + insertion (cost 1) = total 1, strong match"),

        # --- Hyphenated keyword (after accumulated cost, since it builds on the concept) ---
        ("show rning config",
         "Hyphenated keyword split"),

        # --- Stage 2: abbreviation and partial input ---
        ("sh ip int",
         "Abbreviation (Stage 2)"),
        ("debug",
         "Partial input (Stage 2)"),

        # --- Stage 3: positional swap ---
        ("router 65001 bgp",
         "Swapped tokens (Stage 3)"),

        # --- Stage 4: cross-vendor ---
        ("show ip bgp summary",
         "Cisco syntax (Stage 4 AI)"),

        # --- Argument preservation ---
        ("neigbor 10.0.0.1 remote-as 65200",
         "Argument preservation (Technique 13)"),

        # --- Multi-token typo ---
        ("confgure termnial",
         "Typos across two tokens"),
    ]

    for user_input, label in tests:
        print(f"\n  {'~' * 60}")
        print(f"  TEST: {label}")
        _demo_run(user_input, enable_ai=ai_enabled)

    # --- Shortcomings ---
    print(f"\n{'=' * 64}")
    print("  Known limitations")
    print(f"{'=' * 64}")
    print()
    print("  1) Stage 1 uses fuzzy matching, not prefix expansion.")
    print("     Short abbreviations like 'int' vs long keywords like")
    print("     'interface' require many insertions (cost 6), which")
    print("     exceeds the threshold. Stage 2 handles this with prefix")
    print("     matching instead:")
    _demo_run("sh ip int")

    print("  2) Each stage adds latency — the full pipeline cost is the")
    print("     sum of all stages that run. The AI backend (if enabled)")
    print("     adds a network round trip on top of the local computation.")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combined Pipeline demo")
    parser.add_argument("--ai", action="store_true",
                        help="Enable AI semantic backend (Stage 4) for all tests")
    args = parser.parse_args()
    demo(ai_enabled=args.ai)
