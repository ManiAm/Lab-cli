#!/usr/bin/env python3

"""
Render a tree view of Klish 3 CLI definitions from an XML file.
"""

import xml.etree.ElementTree as ET
import sys
import os


def clean_tag(tag: str) -> str:
    """Remove XML namespace prefix from a tag, if present."""

    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def print_tree(node, prefix: str = "", is_last: bool = True) -> None:
    """
    Recursively print a tree of VIEW / COMMAND elements.
    SWITCH elements are flattened (their COMMAND children are printed directly).
    Commands with filter="true" are hidden.
    """

    tag = clean_tag(node.tag)

    # Only process VIEW and COMMAND nodes
    if tag not in ("VIEW", "COMMAND"):
        return

    # Skip pipe/filter commands entirely
    if node.attrib.get("filter", "false") == "true":
        return

    name = node.attrib.get("name", "N/A")
    help_text = node.attrib.get("help", "")

    connector = "└── " if is_last else "├── "

    # Build display line (avoid trailing " : " when help is empty)
    line = f"{prefix}{connector}{name}"
    if help_text:
        line += f" : {help_text}"
    print(line)

    # Prefix for children
    new_prefix = prefix + ("    " if is_last else "│   ")

    # Collect children of interest (VIEW, COMMAND, SWITCH)
    children = [
        child
        for child in node
        if clean_tag(child.tag) in ("VIEW", "COMMAND", "SWITCH")
    ]

    # Flatten SWITCH nodes (they just group COMMAND/VIEW in XML)
    real_children = []
    for child in children:
        ctag = clean_tag(child.tag)
        if ctag == "SWITCH":
            real_children.extend(
                c
                for c in child
                if clean_tag(c.tag) in ("VIEW", "COMMAND")
            )
        else:
            real_children.append(child)

    # Hide pipe/filter commands at child level as well
    visible_children = [
        c for c in real_children
        if c.attrib.get("filter", "false") != "true"
    ]

    # Recurse
    count = len(visible_children)
    for i, child in enumerate(visible_children):
        print_tree(child, new_prefix, i == count - 1)


def main() -> None:

    if len(sys.argv) < 2:
        print("Usage: xml_tree.py <path_to_xml_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)

    try:
        tree = ET.parse(file_path)
    except ET.ParseError as e:
        print(f"XML Parse Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: failed to parse '{file_path}': {e}")
        sys.exit(1)

    root = tree.getroot()
    print(f"\n[ CLI Tree for {file_path} ]\n")

    # Top-level VIEWs
    for child in root:
        if clean_tag(child.tag) == "VIEW":
            print_tree(child)
            print("")  # blank line between views


if __name__ == "__main__":

    main()
