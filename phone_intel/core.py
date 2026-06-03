"""Core phone-number intelligence engine.

REAL DATA ONLY. Everything here is derived from the phone number itself via
Google's libphonenumber dataset (the `phonenumbers` package) plus static public
country geo facts. There is deliberately NO owner identification, NO name
lookup, and NO real-time person tracking — those are not derivable from a number
and any tool claiming otherwise is a scam. "Region" always means the number's
registration region, never a person's current location.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None  # type: ignore

import phonenumbers
from phonenumbers import (
    NumberParseException,
    PhoneNumberFormat,
    PhoneNumberType,
    geocoder,
    carrier,
)
from phonenumbers import timezone as pn_timezone

from .countries import COUNTRIES, flag

# Human labels + a hacker-friendly glyph for each libphonenumber line type.
TYPE_LABELS = {
    PhoneNumberType.MOBILE: ("Mobile", "MOBILE"),
    PhoneNumberType.FIXED_LINE: ("Fixed line", "FIXED_LINE"),
    PhoneNumberType.FIXED_LINE_OR_MOBILE: ("Fixed line or mobile", "FIXED_OR_MOBILE"),
    PhoneNumberType.TOLL_FREE: ("Toll-free", "TOLL_FREE"),
    PhoneNumberType.PREMIUM_RATE: ("Premium rate", "PREMIUM_RATE"),
    PhoneNumberType.SHARED_COST: ("Shared cost", "SHARED_COST"),
    PhoneNumberType.VOIP: ("VoIP", "VOIP"),
    PhoneNumberType.PERSONAL_NUMBER: ("Personal number", "PERSONAL"),
    PhoneNumberType.PAGER: ("Pager", "PAGER"),
    PhoneNumberType.UAN: ("Universal access number", "UAN"),
    PhoneNumberType.VOICEMAIL: ("Voicemail", "VOICEMAIL"),
    PhoneNumberType.UNKNOWN: ("Unknown", "UNKNOWN"),
}


@dataclass
class Intel:
    """Structured intelligence for a single phone number."""

    input: str
    ok: bool = False
    error: Optional[str] = None

    # Validity
    valid: bool = False
    possible: bool = False

    # Identity of the *number* (never the person)
    e164: Optional[str] = None
    international: Optional[str] = None
    national: Optional[str] = None
    rfc3966: Optional[str] = None

    country_iso: Optional[str] = None
    country_name: Optional[str] = None
    country_flag: Optional[str] = None
    calling_code: Optional[int] = None
    capital: Optional[str] = None

    region: Optional[str] = None          # registration region, e.g. "California"
    carrier: Optional[str] = None         # original network operator (mobile)
    line_type: Optional[str] = None       # human label
    line_type_code: Optional[str] = None  # machine code

    national_number: Optional[str] = None
    area_code: Optional[str] = None
    subscriber_number: Optional[str] = None

    timezones: List[str] = field(default_factory=list)
    local_times: List[dict] = field(default_factory=list)  # [{tz, time, utc_offset}]

    # Map (country centroid — NOT the person)
    lat: Optional[float] = None
    lng: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _local_times(tz_names: List[str]) -> List[dict]:
    """Current wall-clock time for each IANA timezone the number maps to."""
    out: List[dict] = []
    if ZoneInfo is None:
        return out
    now_utc = datetime.now().astimezone()
    for tz in tz_names:
        if tz in ("Etc/Unknown", ""):
            continue
        try:
            local = now_utc.astimezone(ZoneInfo(tz))
        except Exception:
            continue
        offset = local.utcoffset()
        if offset is not None:
            total = int(offset.total_seconds() // 60)
            sign = "+" if total >= 0 else "-"
            hh, mm = divmod(abs(total), 60)
            utc_off = f"UTC{sign}{hh:02d}:{mm:02d}"
        else:
            utc_off = "UTC"
        out.append({
            "tz": tz,
            "time": local.strftime("%Y-%m-%d %H:%M:%S"),
            "clock": local.strftime("%H:%M:%S"),
            "utc_offset": utc_off,
        })
    return out


def lookup(raw: str, default_region: Optional[str] = None) -> Intel:
    """Parse a phone number and return everything legitimately derivable from it.

    `default_region` (an ISO code like "US") lets national-format numbers without
    a leading '+' still parse. With no region, the number must be in E.164
    (e.g. +14155552671).
    """
    raw = (raw or "").strip()
    intel = Intel(input=raw)
    if not raw:
        intel.error = "No number provided."
        return intel

    try:
        num = phonenumbers.parse(raw, default_region)
    except NumberParseException as e:
        intel.error = _friendly_parse_error(e)
        return intel

    intel.possible = phonenumbers.is_possible_number(num)
    intel.valid = phonenumbers.is_valid_number(num)

    # Formats
    intel.e164 = phonenumbers.format_number(num, PhoneNumberFormat.E164)
    intel.international = phonenumbers.format_number(num, PhoneNumberFormat.INTERNATIONAL)
    intel.national = phonenumbers.format_number(num, PhoneNumberFormat.NATIONAL)
    intel.rfc3966 = phonenumbers.format_number(num, PhoneNumberFormat.RFC3966)

    # Country
    intel.calling_code = num.country_code
    iso = phonenumbers.region_code_for_number(num)
    # "001" is libphonenumber's sentinel for non-geographic ranges (satellite,
    # shared international, etc.) — not a real ISO code, so don't surface it raw.
    non_geo = iso == "001"
    if non_geo:
        iso = None
    intel.country_iso = iso
    if iso and iso in COUNTRIES:
        c = COUNTRIES[iso]
        intel.country_name = c["name"]
        intel.capital = c["capital"]
        intel.lat = c["lat"]
        intel.lng = c["lng"]
    elif non_geo:
        intel.country_name = "Non-geographic / international"
    intel.country_flag = flag(iso) if iso else "\U0001f310"

    # Region / carrier / type (English locale)
    region = geocoder.description_for_number(num, "en")
    intel.region = region or None
    intel.carrier = carrier.name_for_number(num, "en") or None
    label, code = TYPE_LABELS.get(phonenumbers.number_type(num), ("Unknown", "UNKNOWN"))
    intel.line_type = label
    intel.line_type_code = code

    # National number anatomy
    nsn = phonenumbers.national_significant_number(num)
    intel.national_number = nsn
    ndc_len = phonenumbers.length_of_national_destination_code(num)
    if ndc_len > 0:
        intel.area_code = nsn[:ndc_len]
        intel.subscriber_number = nsn[ndc_len:]
    else:
        intel.subscriber_number = nsn

    # Timezones + live local time
    tzs = [t for t in pn_timezone.time_zones_for_number(num) if t != "Etc/Unknown"]
    intel.timezones = tzs
    intel.local_times = _local_times(tzs)

    intel.ok = True
    if not intel.valid:
        intel.error = ("Number is not a valid number for its country "
                       "(parsed, but fails validation).")
    return intel


def _friendly_parse_error(e: NumberParseException) -> str:
    code = getattr(e, "error_type", None)
    mapping = {
        NumberParseException.INVALID_COUNTRY_CODE:
            "Invalid or missing country code. Include it, e.g. +14155552671.",
        NumberParseException.NOT_A_NUMBER:
            "That doesn't look like a phone number.",
        NumberParseException.TOO_SHORT_NSN: "Number is too short.",
        NumberParseException.TOO_SHORT_AFTER_IDD: "Number is too short.",
        NumberParseException.TOO_LONG: "Number is too long.",
    }
    return mapping.get(code, f"Could not parse number ({e}).")
