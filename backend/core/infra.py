"""Infrastructure-evidence assistance (ADVISORY only). Computer vision cannot establish physical
measurements, capacity or safety conditions - it only judges whether the evidence itself is usable."""
import numpy as np
from PIL import Image

MIN_SHORT_SIDE = 600
MIN_BLUR_VAR = 60.0
BRIGHT_RANGE = (45, 220)


def image_quality(path, registered_lat=None, registered_lon=None):
    try:
        from core import ml_service
        return ml_service.assess_infrastructure_image(path, registered_lat, registered_lon)
    except Exception:
        pass
    import cv2
    im = Image.open(path).convert("L")
    a = np.array(im)
    issues = []
    if min(im.size) < MIN_SHORT_SIDE:
        issues.append(f"low resolution ({im.width}x{im.height})")
    blur = float(cv2.Laplacian(a, cv2.CV_64F).var())
    if blur < MIN_BLUR_VAR:
        issues.append(f"image appears blurred (sharpness {blur:.0f})")
    br = float(a.mean())
    if not (BRIGHT_RANGE[0] <= br <= BRIGHT_RANGE[1]):
        issues.append(f"poor exposure (mean brightness {br:.0f})")
    return {"width": im.width, "height": im.height, "sharpness": round(blur, 1),
            "brightness": round(br, 1), "issues": issues, "usable": len(issues) == 0,
            "disclaimer": "Advisory visual screening only. Physical inspection by AICTE Visiting Committee required."}
