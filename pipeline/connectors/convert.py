#!/usr/bin/env python3
"""Standalone connector CLI - same adapters the upload screen uses.

Usage:
  python3 connectors/convert.py export.xml                       # P6 -> schedule.csv on stdout
  python3 connectors/convert.py po_export.json                   # SAP OData -> po_register.csv
  python3 connectors/convert.py feed.json --po po_register.csv   # logistics merge
  add -o out.csv to write a file instead of stdout
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from connectors import logistics, p6xml, sap_odata  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", help="P6 .xml, SAP OData .json, or logistics feed .json")
    ap.add_argument("--po", help="existing po_register.csv (required for a logistics feed)")
    ap.add_argument("-o", "--out", help="write result CSV here instead of stdout")
    a = ap.parse_args()
    data = open(a.file, "rb").read()
    if a.file.lower().endswith(".xml"):
        if not p6xml.sniff(data):
            sys.exit("not a recognizable Primavera P6 XML export")
        text, note = p6xml.convert(data)
    else:
        obj = json.loads(data.decode("utf-8", errors="ignore"))
        if sap_odata.sniff(obj):
            text, note = sap_odata.convert(obj)
        elif logistics.sniff(obj):
            if not a.po:
                sys.exit("logistics feed needs --po <existing po_register.csv> to merge into")
            text, note = logistics.merge(open(a.po).read(), obj)
        else:
            sys.exit("JSON is neither an SAP OData PO payload nor a shipment-visibility feed")
    print("# " + note, file=sys.stderr)
    if a.out:
        open(a.out, "w").write(text)
        print(f"wrote {a.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
