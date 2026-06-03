"""Report exporters: JSON, CSV, vCard, and QR code (ASCII + PNG)."""
from __future__ import annotations

import csv
import io
import json
import os
from typing import List, Optional

try:
    import qrcode
except ImportError:  # pragma: no cover
    qrcode = None  # type: ignore


def _safe_stub(e164: Optional[str], fallback: str = "number") -> str:
    s = (e164 or fallback).replace("+", "").strip()
    return "".join(ch for ch in s if ch.isalnum()) or fallback


def to_json(intel, path: Optional[str] = None, extra: Optional[dict] = None) -> str:
    payload = intel.to_dict()
    if extra:
        payload.update(extra)
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return text


def to_json_list(intels: List) -> str:
    return json.dumps([it.to_dict() for it in intels], indent=2, ensure_ascii=False)


def batch_to_csv(intels: List, path: str) -> str:
    """Write a flat CSV summary of many lookups. Returns the path."""
    cols = ["input", "ok", "valid", "e164", "country_iso", "country_name",
            "calling_code", "region", "carrier", "line_type", "area_code",
            "timezones", "error"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for it in intels:
            d = it.to_dict()
            d["timezones"] = ";".join(d.get("timezones") or [])
            w.writerow([d.get(c, "") for c in cols])
    return path


def to_vcard(intel, path: Optional[str] = None) -> str:
    """Build a vCard (.vcf) for the *number* — no invented owner name.

    TEL is set to the validated E.164. The display name is intentionally the
    number itself, because we do not know (and will not fabricate) the owner.
    """
    tel = intel.e164 or intel.input
    note_bits = [f"Country: {intel.country_name or intel.country_iso or '?'}"]
    if intel.region:
        note_bits.append(f"Region (registration): {intel.region}")
    if intel.carrier:
        note_bits.append(f"Carrier: {intel.carrier}")
    if intel.line_type:
        note_bits.append(f"Line type: {intel.line_type}")
    note = " | ".join(note_bits)
    vcard = (
        "BEGIN:VCARD\r\n"
        "VERSION:3.0\r\n"
        f"FN:{tel}\r\n"
        f"TEL;TYPE=cell:{tel}\r\n"
        f"NOTE:{note}\r\n"
        "X-GENERATED-BY:phone_intel (number metadata only)\r\n"
        "END:VCARD\r\n"
    )
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(vcard)
    return vcard


def qr_ascii(intel) -> str:
    """Return a terminal-renderable QR code for the number's tel: URI."""
    if qrcode is None:
        return "[qrcode library not installed]"
    uri = intel.rfc3966 or (f"tel:{intel.e164}" if intel.e164 else None)
    if not uri:
        return "[no valid number to encode]"
    qr = qrcode.QRCode(border=1, box_size=1,
                       error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(uri)
    qr.make(fit=True)
    buf = io.StringIO()
    qr.print_ascii(out=buf, invert=True)
    return buf.getvalue()


def qr_png(intel, path: Optional[str] = None) -> Optional[str]:
    """Save a PNG QR code of the tel: URI. Returns the path, or None."""
    if qrcode is None:
        return None
    uri = intel.rfc3966 or (f"tel:{intel.e164}" if intel.e164 else None)
    if not uri:
        return None
    path = path or f"qr_{_safe_stub(intel.e164)}.png"
    img = qrcode.make(uri)
    img.save(path)
    return path
