#!/usr/bin/env python3

"""
Search Klish 3 XML for commands whose name or help text
matches a given pattern, and print their location as a path.
"""

import sys
import xml.etree.ElementTree as ET

NS = {"k": "https://klish.libcode.org/klish3"}
K_NS = "{https://klish.libcode.org/klish3}"


def usage():
    print("Usage: cli_search.py /path/to/main.xml <pattern>")
    sys.exit(1)


def is_view(elem):
    return elem.tag == f"{K_NS}VIEW"


def is_command(elem):
    return elem.tag == f"{K_NS}COMMAND"


def get_attr(elem, name, default=""):
    val = elem.get(name)
    return val if val is not None else default


def walk(elem, path, pattern, results):

    if is_view(elem):
        view_name = get_attr(elem, "name", "<unnamed-view>")
        path = [view_name]

    elif is_command(elem):
        cmd_name = get_attr(elem, "name", "<unnamed-command>")
        new_path = path + [cmd_name]
        path = new_path

        name_l = cmd_name.lower()
        help_l = get_attr(elem, "help", "").lower()

        if pattern in name_l or (help_l and pattern in help_l):
            results.append(
                {
                    "path": path[:],
                    "name": cmd_name,
                    "help": get_attr(elem, "help", ""),
                }
            )

    for child in list(elem):
        walk(child, path, pattern, results)


def main():

    if len(sys.argv) < 3:
        usage()

    xml_path = sys.argv[1]

    # join & strip to handle stray whitespace/newlines
    pattern_raw = " ".join(sys.argv[2:]).strip()

    if not pattern_raw:
        print(f"[ CLI Search: (empty pattern) in {xml_path} ]\n")
        print("Please provide a non-empty search term.")
        return

    pattern = pattern_raw.lower()

    try:
        tree = ET.parse(xml_path)
    except Exception as e:
        print(f"Error: failed to parse XML '{xml_path}': {e}")
        sys.exit(1)

    root = tree.getroot()
    results = []

    walk(root, [], pattern, results)

    print(f'[ CLI Search: "{pattern_raw}" in {xml_path} ]\n')

    if not results:
        print(f"No matches found for '{pattern_raw}'.")
        return

    for idx, r in enumerate(results, 1):
        path_str = " -> ".join(r["path"])
        print(f"{idx}. {path_str}")
        if r["help"]:
            print(f"   help: {r['help']}")
        print("")


if __name__ == "__main__":

    main()
