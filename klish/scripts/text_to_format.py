#!/usr/bin/env python3
"""
Format converter: reads JSON from stdin and emits JSON, XML, or CSV.

When the upstream command produces native JSON (e.g. ip -j addr show),
the data is used directly.  Plain text stdin is wrapped into a list of
{"line": N, "text": "..."} objects as a fallback.

Usage:
    ip -j addr show | python3 text_to_format.py json
    ip -j addr show | python3 text_to_format.py xml
    ip -j addr show | python3 text_to_format.py csv
"""

import sys
import json
import csv
import io
import xml.etree.ElementTree as ET


def _parse_stdin():
    raw = sys.stdin.read()
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        return data
    except (json.JSONDecodeError, ValueError):
        pass
    lines = raw.rstrip("\n").split("\n")
    return [{"line": i + 1, "text": line} for i, line in enumerate(lines)]


def _to_json(data):
    print(json.dumps(data, indent=2))


def _flatten(obj, prefix=""):
    """Flatten a nested dict/list into a single-level dict for CSV."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
            out.update(_flatten(v, key))
    elif isinstance(obj, list):
        if all(isinstance(i, (str, int, float, bool)) for i in obj):
            out[prefix] = ", ".join(str(i) for i in obj)
        else:
            for i, item in enumerate(obj):
                out.update(_flatten(item, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def _to_csv(data):
    if not data:
        return
    flat_rows = [_flatten(row) for row in data]
    all_keys = []
    seen = set()
    for row in flat_rows:
        for k in row:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=all_keys, quoting=csv.QUOTE_ALL,
                            extrasaction="ignore")
    writer.writeheader()
    for row in flat_rows:
        writer.writerow(row)
    sys.stdout.write(buf.getvalue())


def _dict_to_xml(parent, data):
    if isinstance(data, dict):
        for key, val in data.items():
            tag = str(key).replace(" ", "_").replace(".", "_")
            child = ET.SubElement(parent, tag)
            _dict_to_xml(child, val)
    elif isinstance(data, list):
        for item in data:
            child = ET.SubElement(parent, "item")
            _dict_to_xml(child, item)
    else:
        parent.text = str(data)


def _to_xml(data):
    root = ET.Element("output")
    _dict_to_xml(root, data)
    ET.indent(root)
    ET.dump(root)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("json", "xml", "csv"):
        sys.stderr.write("Usage: text_to_format.py {json|xml|csv}\n")
        sys.exit(1)

    fmt = sys.argv[1]
    data = _parse_stdin()
    {"json": _to_json, "xml": _to_xml, "csv": _to_csv}[fmt](data)


if __name__ == "__main__":
    main()
