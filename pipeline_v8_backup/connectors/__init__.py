"""CLAUSE connectors - deterministic adapters from real-world EPC data
sources to the pipeline's canonical registers. Zero LLM calls: format
conversion is mechanical, so it must be exact, free and infinitely scalable.

- p6xml     : Oracle Primavera P6 XML export        -> registers/schedule.csv
- sap_odata : SAP S/4HANA OData purchase-order JSON -> registers/po_register.csv
- logistics : shipment-visibility JSON (FourKites/project44 style)
              -> merged into po_register.csv (eta / current_location / status)

Each module exposes sniff(payload) and convert(payload) (logistics: merge).
The upload endpoint auto-detects these formats; connectors/convert.py is the
same thing as a standalone CLI.
"""
