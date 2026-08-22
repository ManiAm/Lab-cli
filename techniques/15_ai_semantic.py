"""
Technique 15: AI Semantic Backend

Sends an unrecognized command to OpenAI (GPT-4o-mini) for intent-based
matching and cross-vendor translation.  When string-matching algorithms
fail because the user typed valid syntax from a *different* vendor
(Cisco IOS, Juniper Junos, Arista EOS), the LLM recognizes the intent
and suggests the equivalent command for the current platform.

Requirements:
    pip install openai
    Set OPENAI_API_KEY in a .env file at the project root, or export it
    as an environment variable.

When no API key is available or the call fails, Stage 4 is skipped
entirely (no suggestion).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_tree import ALL_COMMANDS

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _load_api_key():
    """Return the OpenAI API key from the environment or .env file."""
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    env_path = os.path.join(_PROJECT_ROOT, ".env")
    if os.path.isfile(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == "OPENAI_API_KEY":
                    return v.strip().strip("\"'")
    return None


SYSTEM_PROMPT = """\
You are a network CLI command translator.

The user typed a command that the local CLI does not recognize.  It may
be valid syntax from another vendor (Cisco IOS, Juniper Junos, Arista
EOS, Nokia SR-OS, etc.) or a natural-language description.

Your job: suggest 1-3 equivalent commands from the LOCAL command list
below.  Only suggest commands that appear in this list.  Preserve any
IP addresses, AS numbers, or interface names the user supplied.

LOCAL COMMANDS:
{commands}

Reply with a JSON array of objects.  Each object has:
  "command" — the suggested local command (string)
  "vendor"  — which vendor syntax the user likely used (string)
  "reason"  — one-sentence explanation (string)

If nothing in the list matches the user's intent, return an empty array: []
Do NOT invent commands that are not in the list above.\
"""


def _build_system_prompt(commands=None):
    if commands is None:
        commands = ALL_COMMANDS
    cmd_list = "\n".join(f"  {c}" for c in sorted(commands))
    return SYSTEM_PROMPT.format(commands=cmd_list)


def semantic_suggest(user_input, commands=None, timeout_ms=3000):
    """Query OpenAI to translate cross-vendor or ambiguous input.

    Returns a list of (command, vendor) tuples, or an empty list when
    no API key is set, the call fails, or the model finds no match.
    """
    global _last_error
    _last_error = None

    api_key = _load_api_key()
    if not api_key:
        _last_error = ("NO_API_KEY",
                       "OPENAI_API_KEY not set. "
                       "Add it to .env or export it as an environment variable.")
        return []

    try:
        from openai import OpenAI
    except ImportError:
        _last_error = ("MISSING_PACKAGE",
                       "openai package not installed. Run: pip install openai")
        return []

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=256,
            timeout=timeout_ms / 1000,
            messages=[
                {"role": "system", "content": _build_system_prompt(commands)},
                {"role": "user", "content": user_input},
            ],
            response_format={"type": "json_object"},
        )

        text = response.choices[0].message.content.strip()
        data = json.loads(text)

        if isinstance(data, dict):
            if "command" in data:
                data = [data]
            else:
                data = data.get("suggestions",
                       data.get("commands",
                       data.get("results", [])))
        if not isinstance(data, list):
            return []

        results = []
        for item in data[:3]:
            if isinstance(item, dict) and "command" in item:
                vendor = item.get("vendor", "unknown")
                results.append((item["command"], vendor))
        return results

    except Exception as exc:
        exc_str = str(exc)
        if "insufficient_quota" in exc_str or "credit_balance" in exc_str:
            _last_error = ("NO_CREDITS",
                           "OpenAI account has no credits remaining. "
                           "Add credits at https://platform.openai.com/settings/organization/billing/")
        elif "invalid_api_key" in exc_str or "Incorrect API key" in exc_str:
            _last_error = ("BAD_API_KEY",
                           "Invalid API key. Check your OPENAI_API_KEY value.")
        elif "timeout" in exc_str.lower() or "timed out" in exc_str.lower():
            _last_error = ("TIMEOUT",
                           f"Request timed out after {timeout_ms}ms. "
                           "Check network connectivity or increase timeout.")
        elif "connection" in exc_str.lower():
            _last_error = ("NETWORK",
                           "Cannot reach OpenAI API. Check network/proxy settings.")
        else:
            _last_error = ("API_ERROR", exc_str)
        return []


_last_error = None


def last_error():
    """Return the last error as (code, message) tuple, or None."""
    return _last_error


def demo():
    print("=" * 60)
    print("Technique 15: AI Semantic Backend (OpenAI)")
    print("=" * 60)

    api_key = _load_api_key()
    if not api_key:
        print()
        print("  ✗ [NO_API_KEY] OPENAI_API_KEY not found.")
        print()
        print("  How to fix:")
        print("    echo 'OPENAI_API_KEY=sk-...' > .env")
        print("    # or")
        print("    export OPENAI_API_KEY=sk-...")
        print()
        print("  Stage 4 will be skipped when no key is available.")
        print()
        return

    print()
    print(f"  API key loaded: {api_key[:8]}...{api_key[-4:]}")
    print(f"  Model: gpt-4o-mini")
    print(f"  Verifying API access... ", end="", flush=True)

    semantic_suggest("test", timeout_ms=10000)
    err = last_error()
    if err:
        code, msg = err
        print(f"FAILED")
        print()
        print(f"  ✗ [{code}] {msg}")
        print()
        return

    print(f"OK")
    print(f"  Local command count: {len(ALL_COMMANDS)}")
    print()

    tests = [
        (
            "show ip bgp neighbors 10.0.0.1 received-routes",
            "Cisco IOS syntax — different keyword structure",
        ),
        (
            "show route receive-protocol bgp 10.0.0.1",
            "Juniper Junos syntax — completely different command",
        ),
        (
            "show ip bgp summary",
            "Cisco/Arista syntax — extra 'ip' keyword",
        ),
        (
            "show configuration",
            "Juniper Junos for 'show running-config'",
        ),
        (
            "show interfaces status",
            "Arista EOS for 'show interfaces summary'",
        ),
        (
            "display bgp peer",
            "Huawei VRP syntax",
        ),
    ]

    for user_input, note in tests:
        print(f"  Input: '{user_input}'")
        print(f"  Note:  {note}")
        results = semantic_suggest(user_input)
        if results:
            for cmd, vendor in results:
                print(f"    → {cmd}  (from {vendor} syntax)")
        else:
            err = last_error()
            if err:
                code, msg = err
                print(f"    ✗ [{code}] {msg}")
                break
            else:
                print("    (no match)")
        print()

    print("  Shortcomings:")
    print("  ─────────────")
    print("  1) Requires an OpenAI API key and network connectivity.")
    print("     Not usable in air-gapped environments.")
    print()
    print("  2) Non-deterministic — the model may produce slightly")
    print("     different suggestions across calls.")
    print()
    print("  3) Latency — adds a network round-trip (typically 200-800ms).")
    print("     Acceptable for a last-resort stage, not for every typo.")
    print()
    print("  4) Security/privacy — sends command text to an external API.")
    print("     Should always be opt-in behind a configuration flag.")
    print()

    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  PROS vs CONS SUMMARY                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ✅ PROS:                                               │")
    print("  │    • Handles cross-vendor translation (Cisco→SONiC etc.)│")
    print("  │    • Works when syntax is completely different (not typo)│")
    print("  │    • Intent-based — understands 'what' not just 'how'   │")
    print("  │    • No manual mapping maintenance — LLM generalizes    │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  ❌ CONS:                                               │")
    print("  │    • Requires API key + network (not air-gapped)        │")
    print("  │    • Non-deterministic — results may vary across calls  │")
    print("  │    • Latency — 200-800ms network round-trip             │")
    print("  │    • Security/privacy risk (sends commands to OpenAI)   │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │  → NEXT: Technique 16 (Combined Pipeline) chains all    │")
    print("  │          techniques for comprehensive coverage          │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    demo()
