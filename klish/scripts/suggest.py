#!/usr/bin/env python3

"""
Smart command suggestion engine for Lab-CLI.

Called by the klish daemon hook when a command fails to parse.
Reads the rejected command line from KLISH_SUGGEST_LINE, walks the XML
command tree, and prints the closest valid commands.

Pipeline (Technique 16, with production gap-fills):
    Stage 1  Tree walk with weighted Damerau-Levenshtein (Techniques 4+5).
             Continues into the best sibling after a correction so later
             tokens are still scored. Hyphenated keywords (Technique 12)
             are split and matched as separate user tokens. PARAM values
             are kept as typed (Technique 13).
    Stage 2  Flat-corpus scan with prefix abbreviation (Techniques 1, 2, 11)
             if Stage 1 has no strong match (cost <= 1).
    Stage 3  Positional swap (Technique 14), always.

The klish C patch does not need to change when this algorithm changes.
"""

import glob
import itertools
import os
import sys
import xml.etree.ElementTree as ET

XML_DIR = os.environ.get("KLISH_SUGGEST_XML_DIR", "/root/.klish")
NS = "{https://klish.libcode.org/klish3}"
MAX_RESULTS = 3
STAGE1_THRESHOLD = 3
STRONG_MATCH = 1

WEIGHTS = {
    "transposition": 0,
    "insertion": 1,
    "substitution": 2,
    "deletion": 3,
}


# ---------------------------------------------------------------------------
# Scorer: Technique 5 on Technique 4
# ---------------------------------------------------------------------------

def weighted_damerau_levenshtein(s, t, weights=None):
    """Weighted Damerau-Levenshtein: turn s into t."""
    if weights is None:
        weights = WEIGHTS
    w_trans = weights["transposition"]
    w_ins = weights["insertion"]
    w_sub = weights["substitution"]
    w_del = weights["deletion"]

    s = s.lower()
    t = t.lower()
    len_s, len_t = len(s), len(t)
    if len_s == 0:
        return len_t * w_ins
    if len_t == 0:
        return len_s * w_del

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
                d[i][j] + cost,
                d[i + 1][j] + w_ins,
                d[i][j + 1] + w_del,
                trans_cost,
            )
        char_map[s[i - 1]] = i
    return d[len_s + 1][len_t + 1]


def token_threshold(token_len):
    """Accept one deletion (cost 3) on short tokens; a bit more on long ones."""
    if token_len <= 4:
        return 3
    if token_len <= 8:
        return 4
    return 5


# ---------------------------------------------------------------------------
# XML tree helpers
# ---------------------------------------------------------------------------

def _local(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def parse_trees(xml_dir):
    roots = []
    for path in sorted(glob.glob(os.path.join(xml_dir, "*.xml"))):
        try:
            roots.append(ET.parse(path).getroot())
        except Exception:
            continue
    return roots


def get_views(roots):
    views = {}
    for root in roots:
        for elem in root.iter(f"{NS}VIEW"):
            name = elem.get("name")
            if not name:
                continue
            if name in views:
                for child in list(elem):
                    views[name].append(child)
            else:
                views[name] = elem
    return views


def collect_commands(elem):
    commands = []
    for child in list(elem):
        tag = _local(child.tag)
        if tag == "SWITCH":
            commands.extend(collect_commands(child))
        elif tag == "COMMAND":
            commands.append(child)
    return commands


def collect_params(elem):
    params = []
    for child in list(elem):
        tag = _local(child.tag)
        if tag == "SWITCH":
            params.extend(collect_params(child))
        elif tag == "PARAM":
            params.append(child)
    return params


def cmd_name(elem):
    val = elem.get("value")
    if val and "|" in val:
        val = None
    return val or elem.get("name", "")


def is_param(elem):
    return _local(elem.tag) == "PARAM"


# ---------------------------------------------------------------------------
# Hyphenated matching (Technique 12)
# ---------------------------------------------------------------------------

def match_hyphenated(user_tokens, start_idx, candidate):
    """Match candidate 'running-config' against user tokens starting at start_idx.

    Returns (total_cost, tokens_consumed) or None.
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
            total += len(segment) * WEIGHTS["insertion"]
            break
        user_tok = user_tokens[token_idx]
        dist = weighted_damerau_levenshtein(user_tok, segment)
        thresh = token_threshold(len(segment))
        if dist <= thresh:
            total += dist
            consumed += 1
        elif seg_idx == 0:
            return None
        else:
            total += len(segment) * WEIGHTS["insertion"]
    if consumed == 0:
        return None
    return (total, consumed)


# ---------------------------------------------------------------------------
# Stage 1: recursive tree walk
# ---------------------------------------------------------------------------

def _keyword_hits(token, tokens, idx, names):
    """Exact, hyphenated, and fuzzy hits for one user token against keywords."""
    hits = []  # (cost, consumed, canonical_name)
    token_l = token.lower()
    for name in names:
        if token_l == name.lower():
            hits.append((0, 1, name))
            continue
        hyphen = match_hyphenated(tokens, idx, name)
        if hyphen is not None:
            cost, consumed = hyphen
            if cost <= token_threshold(len(name)):
                hits.append((cost, consumed, name))
            continue
        dist = weighted_damerau_levenshtein(token, name)
        if dist <= token_threshold(len(name)):
            hits.append((dist, 1, name))
    hits.sort(key=lambda x: (x[0], -x[1], x[2]))
    # Keep the cheapest name once
    seen = set()
    unique = []
    for h in hits:
        if h[2] not in seen:
            seen.add(h[2])
            unique.append(h)
    return unique


def tree_walk(tokens, idx, node, prefix, cost_so_far, branch_limit=MAX_RESULTS):
    """Walk from *node* starting at tokens[idx]. Returns list of (cmd, cost)."""
    if idx >= len(tokens):
        return [(" ".join(prefix), cost_so_far)] if prefix else []

    token = tokens[idx]
    commands = collect_commands(node)
    params = collect_params(node)
    names = {cmd_name(c): c for c in commands}

    hits = _keyword_hits(token, tokens, idx, names)

    # Prefer an exact keyword over treating the token as a PARAM.
    exact = [h for h in hits if h[0] == 0]
    if exact:
        _, consumed, name = exact[0]
        child = names[name]
        return tree_walk(tokens, idx + consumed, child, prefix + [name], cost_so_far)

    results = []
    close = [h for h in hits if h[0] <= STAGE1_THRESHOLD]
    for cost, consumed, name in close[:branch_limit]:
        child = names[name]
        results.extend(
            tree_walk(
                tokens, idx + consumed, child,
                prefix + [name], cost_so_far + cost,
            )
        )

    # Technique 13: no close keyword → accept PARAM as typed
    if params and not close:
        child = params[0]
        results.extend(
            tree_walk(
                tokens, idx + 1, child,
                prefix + [token], cost_so_far,
            )
        )

    if results:
        return results

    # Stuck: return what we have plus leftover tokens (uncorrected)
    leftover = prefix + tokens[idx:]
    return [(" ".join(leftover), cost_so_far + 99)] if leftover else []


def stage1(tokens, view):
    raw = tree_walk(tokens, 0, view, [], 0)
    # Drop "stuck" paths that only echoed the input with a huge penalty
    cleaned = []
    original = " ".join(tokens)
    for cmd, cost in raw:
        if cost >= 99:
            continue
        if cmd == original and cost == 0:
            continue
        cleaned.append((cmd, cost, "tree-walk"))
    cleaned.sort(key=lambda x: x[1])
    return cleaned


# ---------------------------------------------------------------------------
# Stage 2: flat-corpus scan
# ---------------------------------------------------------------------------

def enumerate_paths(elem, prefix):
    """Yield (token_list, node) for every COMMAND/PARAM path under elem."""
    commands = collect_commands(elem)
    params = collect_params(elem)
    if not commands and not params:
        if prefix:
            yield prefix
        return
    emitted = False
    for child in commands:
        name = cmd_name(child)
        emitted = True
        yield from enumerate_paths(child, prefix + [("kw", name)])
    for param in params:
        emitted = True
        yield from enumerate_paths(param, prefix + [("param", param.get("name", "arg"))])
    if not emitted and prefix:
        yield prefix


def path_to_display(path):
    parts = []
    for kind, name in path:
        if kind == "param":
            parts.append("<" + name + ">")
        else:
            parts.append(name)
    return " ".join(parts)


def score_path(user_tokens, path):
    """Return (matched_keywords, total_cost, display, exact_prefix) or None.

    exact_prefix is True when every user token matched its keyword exactly
    or as a prefix (cost 0). This lets stage2 prioritize exact-prefix
    results over fuzzy ones.
    """
    u = 0
    total = 0
    matched = 0
    exact_prefix = True
    display = []
    for kind, name in path:
        if u >= len(user_tokens):
            display.append(name if kind == "kw" else "<" + name + ">")
            continue
        if kind == "param":
            display.append(user_tokens[u])
            matched += 1
            u += 1
            continue
        token = user_tokens[u]
        if token.lower() == name.lower():
            display.append(name)
            matched += 1
            u += 1
            continue
        if name.lower().startswith(token.lower()) and token:
            display.append(name)
            matched += 1
            u += 1
            continue
        exact_prefix = False
        hyphen = match_hyphenated(user_tokens, u, name)
        if hyphen is not None:
            cost, consumed = hyphen
            thresh = token_threshold(len(name))
            if cost <= thresh:
                display.append(name)
                matched += 1
                total += cost
                u += consumed
                continue
        dist = weighted_damerau_levenshtein(token, name)
        if len(token) <= 2 and dist > 1:
            return None
        if len(token) * 2 >= len(name) and dist <= token_threshold(len(name)):
            display.append(name)
            matched += 1
            total += dist
            u += 1
            continue
        return None
    if matched == 0:
        return None
    extra = max(0, len(user_tokens) - u)
    total += extra * 2
    return (matched, total, " ".join(display), exact_prefix)


def stage2(tokens, view):
    results = []
    has_exact = False
    for path in enumerate_paths(view, []):
        scored = score_path(tokens, path)
        if scored is None:
            continue
        matched, total, display, exact_prefix = scored
        results.append((display, total, "flat-scan", matched, exact_prefix))
        if exact_prefix:
            has_exact = True
    if has_exact:
        results = [r for r in results if r[4]]
    results.sort(key=lambda x: (-x[3], x[1]))
    out = []
    seen = set()
    for display, total, src, _matched, _exact in results:
        if display in seen:
            continue
        seen.add(display)
        out.append((display, total, src))
        if len(out) >= MAX_RESULTS * 3:
            break
    return out


# ---------------------------------------------------------------------------
# Stage 3: positional swap
# ---------------------------------------------------------------------------

def _path_fits_permutation(perm, path):
    """True if permuted user tokens fill the path (keywords match, params take anything).

    Only exact keyword matches are accepted — prefix/fuzzy matching would
    produce false positives (e.g. treating abbreviations as swapped tokens).
    """
    if len(perm) != len(path):
        return False
    for user_tok, (kind, name) in zip(perm, path):
        if kind == "param":
            continue
        if user_tok.lower() != name.lower():
            return False
    return True


def _display_swap(perm, path):
    parts = []
    for user_tok, (kind, name) in zip(perm, path):
        parts.append(user_tok if kind == "param" else name)
    return " ".join(parts)


def stage3(tokens, view):
    original = " ".join(tokens)
    n = len(tokens)
    if n < 2 or n > 6:
        return []
    results = []
    seen = set()
    for path in enumerate_paths(view, []):
        if len(path) != n:
            continue
        # Skip paths with no PARAM — swap is about keyword/value order
        if not any(kind == "param" for kind, _ in path):
            continue
        for perm in itertools.permutations(tokens):
            if not _path_fits_permutation(perm, path):
                continue
            display = _display_swap(perm, path)
            if display == original or display in seen:
                continue
            seen.add(display)
            results.append((display, 0, "swap"))
    return results


# ---------------------------------------------------------------------------
# Combine
# ---------------------------------------------------------------------------

def combined_suggest(tokens, view):
    candidates = []
    s1 = stage1(tokens, view)
    candidates.extend(s1)

    strong = any(cost <= STRONG_MATCH for _, cost, _ in candidates)
    if not strong:
        candidates.extend(stage2(tokens, view))

    candidates.extend(stage3(tokens, view))

    seen = set()
    unique = []
    original = " ".join(tokens)
    for cmd, cost, source in sorted(candidates, key=lambda x: x[1]):
        if cmd == original:
            continue
        if cmd in seen:
            continue
        seen.add(cmd)
        unique.append((cmd, cost, source))
    return unique[:MAX_RESULTS]


def find_suggestions(tokens, view_elem):
    """Return display strings for the hook (closest matches only)."""
    return [cmd for cmd, _cost, _src in combined_suggest(tokens, view_elem)]


def main():
    line = os.environ.get("KLISH_SUGGEST_LINE", "")
    if not line and len(sys.argv) > 1:
        line = " ".join(sys.argv[1:])
    line = line.strip()
    if not line:
        return

    tokens = line.split()
    if not tokens:
        return

    roots = parse_trees(XML_DIR)
    if not roots:
        return

    views = get_views(roots)
    view = views.get("main")
    if view is None:
        return

    matches = find_suggestions(tokens, view)
    if matches:
        print("Closest match:")
        for m in matches:
            print("  " + m)


if __name__ == "__main__":
    main()
