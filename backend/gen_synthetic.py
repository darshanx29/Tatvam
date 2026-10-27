"""Generates synthetic test applications + the mock issuer registry.  python gen_synthetic.py"""
import os, json, shutil
import pymupdf as fitz

OUT = "data/synthetic"
REG = {}
APR1 = ("Programme: B.Tech Computer Engineering", "Approved Intake: 120")


def pdf(path, title, lines, producer="SmartVerify-Gen", created="D:20260105100000", mod=None):
    doc = fitz.open()
    pg = doc.new_page()
    pg.insert_text((72, 72), title, fontsize=16)
    for i, l in enumerate(lines):
        pg.insert_text((72, 110 + i * 22), l, fontsize=11)
    doc.set_metadata({"producer": producer, "creator": producer,
                      "creationDate": created, "modDate": mod or created})
    doc.save(path)


def reg(ref, iid, valid):
    REG[ref] = {"institution_id": iid, "valid_until": valid}


def common(iid, name, ref, issuer, issue, valid, extra=()):
    return [f"Institution Name: {name}", f"Institution ID: {iid}", f"Certificate No: {ref}",
            f"Issued By: {issuer}", f"Issue Date: {issue}", f"Valid Until: {valid}", *extra]


def app001():  # clean application
    d = f"{OUT}/APP-001"; os.makedirs(d, exist_ok=True)
    iid, nm = "1-1001", "Demo Institute of Technology"
    specs = [("accreditation.pdf", "ACCREDITATION CERTIFICATE (NBA Grade A)", "ACC-2026-001", "NBA", "01-01-2026", "31-12-2028"),
             ("noc.pdf", "NO OBJECTION CERTIFICATE (NOC)", "NOC-MH-777", "State Govt", "10-02-2026", "31-12-2027"),
             ("affidavit.pdf", "AFFIDAVIT AND UNDERTAKING - I solemnly affirm", "AFF-55", "Notary", "05-03-2026", "31-12-2027"),
             ("approval_record.pdf", "EXTENSION OF APPROVAL RECORD - Approved Intake 120", "EOA-2025-9", "AICTE", "01-06-2025", "31-05-2027"),
             ("infra_fire.pdf", "FIRE SAFETY / INFRASTRUCTURE CERTIFICATE", "INF-FIRE-12", "Fire Dept", "15-01-2026", "14-01-2027")]
    for fn, title, ref, iss, i, v in specs:
        pdf(f"{d}/{fn}", title, common(iid, nm, ref, iss, i, v, extra=APR1 if fn == "approval_record.pdf" else ())); reg(ref, iid, v)


def app002():  # problem application
    d = f"{OUT}/APP-002"; os.makedirs(d, exist_ok=True)
    iid, nm = "1-2002", "Sample College of Engineering"
    # 1. expired accreditation
    pdf(f"{d}/accreditation.pdf", "ACCREDITATION CERTIFICATE (NAAC Grade B)",
        common(iid, nm, "ACC-2024-002", "NAAC", "01-07-2021", "30-06-2026")); reg("ACC-2024-002", iid, "30-06-2026")
    # 2. NOC with wrong institution id (registry has the right one) + exact duplicate copy
    pdf(f"{d}/noc.pdf", "NO OBJECTION CERTIFICATE (NOC)",
        common("1-2999", nm, "NOC-MH-888", "State Govt", "10-02-2026", "31-12-2027")); reg("NOC-MH-888", iid, "31-12-2027")
    shutil.copy(f"{d}/noc.pdf", f"{d}/noc_copy.pdf")
    # 3. affidavit intentionally missing
    # 4. approval record with date anomaly (issue after validity)
    pdf(f"{d}/approval_record.pdf", "EXTENSION OF APPROVAL RECORD - Approved Intake 60",
        common(iid, nm, "EOA-2025-4", "AICTE", "10-05-2026", "01-01-2026",
               extra=("Programme: B.Tech Mechanical Engineering", "Approved Intake: 60"))); reg("EOA-2025-4", iid, "01-01-2026")
    # 5. infra cert: source unavailable + edited-metadata flag
    pdf(f"{d}/infra_fire.pdf", "FIRE SAFETY / INFRASTRUCTURE CERTIFICATE",
        common(iid, nm, "UNAVAIL-INF-3", "Fire Dept", "15-01-2026", "14-01-2027"),
        producer="Adobe Photoshop 25.0", created="D:20260115100000", mod="D:20261001120000")


# ---------------------------------------------------------------- image-based applications
def _img(path, title, lines, size=(1240, 900), jpeg=False, blur=0, noise=0, seed=0):
    import random
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    random.seed(seed)
    im = Image.new("RGB", size, "white"); dr = ImageDraw.Draw(im)
    f1, f2 = ImageFont.load_default(size=40), ImageFont.load_default(size=30)
    dr.text((60, 50), title, fill="black", font=f1)
    for i, l in enumerate(lines):
        dr.text((60, 150 + i * 60), l, fill="black", font=f2)
    if blur: im = im.filter(ImageFilter.GaussianBlur(blur))
    if noise:
        px = im.load()
        for _ in range(size[0] * size[1] // 40):
            x, y = random.randrange(size[0]), random.randrange(size[1]); v = random.randrange(255)
            px[x, y] = (v, v, v)
    meta = json.dumps({"title": title, "lines": lines})
    if jpeg:
        im.save(path, "JPEG", quality=92, comment=meta.encode("utf-8"))
    else:
        from PIL.PngImagePlugin import PngInfo
        info = PngInfo()
        info.add_text("synth_ocr", meta)
        im.save(path, pnginfo=info)


def app003():  # scanned (image) application: OCR path + low-res poor scan + QR-free
    d = f"{OUT}/APP-003"; os.makedirs(d, exist_ok=True)
    iid, nm = "1-3003", "Scan Test Institute"
    _img(f"{d}/accreditation.png", "ACCREDITATION CERTIFICATE (NBA Grade A)", common(iid, nm, "ACC-2026-031", "NBA", "01-01-2026", "31-12-2028")); reg("ACC-2026-031", iid, "31-12-2028")
    _img(f"{d}/noc.png", "NO OBJECTION CERTIFICATE (NOC)", common(iid, nm, "NOC-MH-031", "State Govt", "10-02-2026", "31-12-2027")); reg("NOC-MH-031", iid, "31-12-2027")
    _img(f"{d}/affidavit.png", "AFFIDAVIT AND UNDERTAKING - I solemnly affirm", common(iid, nm, "AFF-031", "Notary", "05-03-2026", "31-12-2027")); reg("AFF-031", iid, "31-12-2027")
    _img(f"{d}/approval_record.png", "EXTENSION OF APPROVAL RECORD", common(iid, nm, "EOA-2025-31", "AICTE", "01-06-2025", "31-05-2027", extra=("Programme: B.Tech Civil Engineering", "Approved Intake: 60"))); reg("EOA-2025-31", iid, "31-05-2027")
    _img(f"{d}/infra_fire.png", "FIRE SAFETY / INFRASTRUCTURE CERTIFICATE", common(iid, nm, "INF-FIRE-31", "Fire Dept", "15-01-2026", "14-01-2027")); reg("INF-FIRE-31", iid, "14-01-2027")
    _img(f"{d}/lab_photo.jpg", "LABORATORY PHOTO", ["Computer Lab 2"], size=(320, 240), jpeg=True, blur=4)   # unusable evidence photo


def app004():  # incomplete application submitted as a single JPEG scan (JPEG OCR path + missing documents)
    d = f"{OUT}/APP-004"; os.makedirs(d, exist_ok=True)
    iid, nm = "1-3003", "Scan Test Institute"
    _img(f"{d}/accreditation.jpg", "ACCREDITATION CERTIFICATE (NBA Grade A)", common(iid, nm, "ACC-2026-041", "NBA", "01-01-2026", "31-12-2028"), jpeg=True)
    reg("ACC-2026-041", iid, "31-12-2028")


if __name__ == "__main__":
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs("data", exist_ok=True)
    app001(); app002(); app003(); app004()
    json.dump(REG, open("data/mock_registry.json", "w"), indent=2)
    print("Generated synthetic apps + mock registry")
