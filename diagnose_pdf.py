"""Shows exactly what SmartVerify reads from a document.   python diagnose_pdf.py path/to/file.pdf
Prints: how it was read (text layer / OCR), the classification, the raw text, and every extracted field."""
import sys
from core import extractor

path = sys.argv[1]
ex = extractor.extract_pages(path)
text = "\n".join(p["text"] for p in ex["pages"])
dtype, conf = extractor.classify(text, path)
fields = extractor.extract_fields(ex["pages"], ex["method"])
print(f"read by: {ex['method']}   pages: {len(ex['pages'])}   mean confidence: {ex['mean_conf']}")
print(f"classified as: {dtype} ({conf})")
print("\n===== RAW TEXT =====")
print(text)
print("\n===== EXTRACTED FIELDS =====")
for k, v in fields.items():
    print(f"{k:20} {v['value']!r}   conf={v['confidence']}")
print("\n===== EoA TABLE =====")
for label, value, c in extractor.eoa_summary("approval_record", fields):
    print(f"{label:20} {value if value else 'NOT FOUND'}")
