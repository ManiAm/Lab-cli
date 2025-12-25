#!/usr/bin/env python3

import sys
import json
import xml.etree.ElementTree as ET


def d2x(data, root):

    if isinstance(data, dict):
        for k, v in data.items():
            child = ET.SubElement(root, str(k))
            d2x(v, child)

    elif isinstance(data, list):
        for item in data:
            child = ET.SubElement(root, "item")
            d2x(item, child)

    else:
        root.text = str(data)


def main():

    data = json.load(sys.stdin)
    root = ET.Element("interfaces")
    d2x(data, root)
    ET.dump(root)


if __name__ == "__main__":

    main()
