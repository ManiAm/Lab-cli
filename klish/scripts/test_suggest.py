#!/usr/bin/env python3
"""Tests for klish/scripts/suggest.py against klish/xml/test_suggest.xml.

Run from the repo:
    python3 klish/scripts/test_suggest.py
"""

import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
XML_SRC = os.path.join(REPO, "klish", "xml", "test_suggest.xml")

sys.path.insert(0, HERE)
import suggest  # noqa: E402


def load_view():
    tmp = tempfile.mkdtemp(prefix="suggest-xml-")
    shutil.copy(XML_SRC, os.path.join(tmp, "test_suggest.xml"))
    roots = suggest.parse_trees(tmp)
    views = suggest.get_views(roots)
    shutil.rmtree(tmp)
    view = views.get("main")
    if view is None:
        raise RuntimeError("test XML has no VIEW named main")
    return view


VIEW = None


def suggestions(line):
    tokens = line.split()
    return suggest.combined_suggest(tokens, VIEW)


def cmds(line):
    return [c for c, _cost, _src in suggestions(line)]


def top(line):
    results = cmds(line)
    return results[0] if results else None


def source_of(line, command):
    for c, _cost, src in suggestions(line):
        if c == command:
            return src
    return None


class SuggestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global VIEW
        VIEW = load_view()

    # --- Stage 1: tree walk + weighted DL ---

    def test_insertion_interface(self):
        self.assertEqual(top("test show interfce"), "test show interface")
        self.assertEqual(source_of("test show interfce", "test show interface"), "tree-walk")

    def test_transposition_bgp(self):
        self.assertEqual(top("test show bpg summary"), "test show bgp summary")

    def test_transposition_show(self):
        self.assertIn("test show version", cmds("test shwo version"))

    def test_extra_letter_deleted(self):
        self.assertEqual(top("test show versionn"), "test show version")

    def test_substitution_version(self):
        # one wrong letter (cost 2) still accepted
        self.assertIn("test show version", cmds("test show versiom"))

    def test_ranking_transposition_beats_substitution(self):
        # summary vs suppress vs suspend: "sumamry" is close to summary
        self.assertEqual(top("test show sumamry"), "test show summary")

    def test_deep_nest_typo(self):
        self.assertEqual(
            top("test router bgp neighbr remote-as"),
            "test router bgp neighbor remote-as",
        )

    def test_first_and_later_typo_both_corrected(self):
        # Stage 1 continues after correcting shwo, then scores interfce
        self.assertEqual(top("test shwo interfce"), "test show interface")

    def test_two_typos_bgp_summary(self):
        self.assertEqual(top("test show bpg sumary"), "test show bgp summary")

    def test_long_keyword_typo(self):
        self.assertIn("test show environment", cmds("test show environmnt")[0:2])

    def test_garbage_short_keyword_rejected(self):
        hits = cmds("test show xyz")
        self.assertFalse(any(h.endswith(" bgp") or h.endswith(" vrf") or h.endswith(" acl")
                             for h in hits))

    # --- Technique 12: hyphenated ---

    def test_hyphen_split_running_config(self):
        self.assertEqual(top("test show rning config"), "test show running-config")

    def test_hyphen_space_exact(self):
        self.assertEqual(top("test show running config"), "test show running-config")

    def test_hyphen_both_halves_typo(self):
        self.assertEqual(top("test show port chanel"), "test show port-channel")

    def test_double_hyphen_as_words(self):
        self.assertEqual(
            top("test clear mac address table"),
            "test clear mac-address-table",
        )

    def test_hyphen_nested(self):
        self.assertIn(
            "test copy running-config startup-config",
            cmds("test copy running config startup config"),
        )

    # --- Stage 2: prefix / incomplete ---

    def test_abbreviation_sh_bgp_sum(self):
        self.assertEqual(top("test sh bgp sum"), "test show bgp summary")

    def test_prefix_int_ambiguous(self):
        hits = cmds("test show int")
        self.assertTrue(
            any(h == "test show interface" or h == "test show interfaces" for h in hits)
        )

    def test_incomplete_debug_lists_children(self):
        hits = cmds("test debug")
        self.assertTrue(any(h.startswith("test debug ") for h in hits))
        self.assertIn("test debug bgp", hits)

    def test_skipped_level_needs_flat_scan(self):
        # "sum" is not a child of show; target is show bgp summary
        hits = cmds("test sh sum")
        self.assertTrue(any("summary" in h for h in hits))

    # --- Technique 13: arguments preserved ---

    def test_ping_ip_preserved(self):
        self.assertEqual(top("test png 10.0.0.1"), "test ping 10.0.0.1")

    def test_neighbor_ip_preserved_on_keyword_typo(self):
        self.assertEqual(
            top("test neigbor 10.0.0.1 remote-as 65200"),
            "test neighbor 10.0.0.1 remote-as 65200",
        )

    # --- Technique 14: positional swap ---

    def test_swap_asn_before_keyword(self):
        self.assertEqual(
            top("test asn-router 65001 bgp"),
            "test asn-router bgp 65001",
        )
        self.assertEqual(
            source_of("test asn-router 65001 bgp", "test asn-router bgp 65001"),
            "swap",
        )

    def test_swap_neighbor_ip_and_keyword(self):
        self.assertEqual(
            top("test neighbor remote-as 10.0.0.1 65200"),
            "test neighbor 10.0.0.1 remote-as 65200",
        )

    # --- Prefix ambiguity ---

    def test_interface_vs_interfaces(self):
        hits = cmds("test show interfacs")
        self.assertTrue(any("interface" in h for h in hits))

    # --- No crash / empty ---

    def test_unknown_root_is_empty_or_harmless(self):
        hits = cmds("zzzz notacommand")
        self.assertTrue(isinstance(hits, list))

    def test_configure_typos(self):
        self.assertEqual(top("test confgure terminal"), "test configure terminal")
        self.assertEqual(top("test configure termnial"), "test configure terminal")

    def test_hyphen_access_list(self):
        self.assertEqual(top("test show access list"), "test show access-list")

    def test_hyphen_snmp_server_nested(self):
        self.assertEqual(
            top("test configure snmp server community"),
            "test configure snmp-server community",
        )

    def test_monitor_telemetry_typo(self):
        self.assertEqual(
            top("test monitor telemety subscribe"),
            "test monitor telemetry subscribe",
        )

    def test_clear_arp_cache_hyphen(self):
        self.assertEqual(top("test clear arp cache"), "test clear arp-cache")

    def test_garbage_long_junk_empty(self):
        self.assertEqual(cmds("test show xyzabc"), [])

    def test_hook_stdout_format(self):
        tmp = tempfile.mkdtemp(prefix="suggest-hook-")
        shutil.copy(XML_SRC, os.path.join(tmp, "test_suggest.xml"))
        env = os.environ.copy()
        env["KLISH_SUGGEST_XML_DIR"] = tmp
        env["KLISH_SUGGEST_LINE"] = "test show interfce"
        import subprocess
        out = subprocess.check_output(
            [sys.executable, os.path.join(HERE, "suggest.py")],
            env=env,
            text=True,
        )
        shutil.rmtree(tmp)
        self.assertIn("Closest match:", out)
        self.assertIn("test show interface", out)


def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SuggestTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
