"""phone_intel TUI — hacker-themed terminal front end over the honest engine.

Usage examples:
    python -m phone_intel +14155552671
    python -m phone_intel "+63 917 123 4567" --qr --live
    python -m phone_intel --batch numbers.txt --export out
    python -m phone_intel                      # interactive recon shell
"""
from __future__ import annotations

import argparse
import io
import sys
import urllib.parse

# Force UTF-8 so flags/emoji/box-drawing render on Windows consoles (cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    # Last-resort wrap so undecodable glyphs degrade to '?' instead of raising
    # UnicodeEncodeError mid-render on a stripped-down console.
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from . import lookup, __version__
from . import effects as fx
from . import reputation as rep
from . import report as rp

console = Console(highlight=False)

LBL = "#2f6f3f"
VAL = "bold #d8d8e8"
GREEN = "bold #00ff41"
CYAN = "bold #00bfff"
AMBER = "bold #ffb700"
RED = "bold #ff3860"

RISK_STYLE = {"LOW": GREEN, "MEDIUM": AMBER, "HIGH": RED, "UNKNOWN": LBL}


def _osm_pin(lat, lng) -> str:
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=5/{lat}/{lng}"


def _osm_search(region) -> str:
    return "https://www.openstreetmap.org/search?query=" + urllib.parse.quote(region)


def _row(table, label, value, vstyle=VAL):
    if value in (None, "", []):
        value = "—"
        vstyle = LBL
    table.add_row(Text(label, style=LBL), Text(str(value), style=vstyle))


def render_intel(intel, args) -> None:
    flag = intel.country_flag or "🌐"
    title = Text(f"{flag} ", style="")
    title.append(intel.international or intel.input, style=GREEN)
    badge = ("VALID" if intel.valid else ("INVALID" if intel.ok else "UNPARSED"))
    badge_style = GREEN if intel.valid else (AMBER if intel.ok else RED)

    table = Table(show_header=False, box=box.SIMPLE_HEAD, expand=True,
                  pad_edge=False, padding=(0, 1))
    table.add_column(justify="right", no_wrap=True, ratio=2)
    table.add_column(ratio=5)

    _row(table, "STATUS", badge, badge_style)
    _row(table, "COUNTRY",
         f"{intel.country_name or intel.country_iso or '?'}"
         + (f"  (+{intel.calling_code})" if intel.calling_code else ""))
    _row(table, "ISO / CAPITAL",
         f"{intel.country_iso or '—'}   ·   {intel.capital or '—'}")
    _row(table, "REGION (reg.)", intel.region, CYAN)
    _row(table, "CARRIER", intel.carrier, CYAN)
    _row(table, "LINE TYPE", intel.line_type)
    table.add_row("", "")
    _row(table, "E.164", intel.e164, GREEN)
    _row(table, "NATIONAL", intel.national)
    _row(table, "RFC3966", intel.rfc3966)
    _row(table, "AREA / SUB",
         f"{intel.area_code or '—'}  /  {intel.subscriber_number or '—'}")

    # Live clocks
    if intel.local_times:
        table.add_row("", "")
        for i, t in enumerate(intel.local_times):
            label = "LOCAL TIME ⏱" if i == 0 else ""
            _row(table, label, f"{t['clock']}  {t['utc_offset']}   ({t['tz']})", AMBER)
    elif intel.timezones:
        _row(table, "TIMEZONE", ", ".join(intel.timezones))

    # Map (clearly registration region, not a person)
    # URLs have no spaces, so the default 'ellipsis' overflow would crop them at
    # normal terminal widths. Fold instead so the full link survives.
    if intel.lat is not None and intel.lng is not None:
        table.add_row("", "")
        table.add_row(Text("MAP (region)", style=LBL),
                      Text(_osm_pin(intel.lat, intel.lng), style="#4a90d9", overflow="fold"))
    if intel.region:
        table.add_row(Text("REGION MAP", style=LBL),
                      Text(_osm_search(intel.region), style="#4a90d9", overflow="fold"))

    subtitle = Text("registration region — NOT the owner's live location",
                    style="italic #555566")
    console.print(Panel(table, title=title, subtitle=subtitle,
                        border_style="#00ff41", box=box.HEAVY))

    if intel.error and not intel.valid:
        console.print(Text(f"  ⚠ {intel.error}", style=AMBER))

    # Reputation (heuristic)
    if getattr(args, "reputation", True):
        r = rep.assess(intel)
        rs = RISK_STYLE.get(r["level"], LBL)
        head = Text("  RISK ", style=LBL)
        head.append(f"{r['level']}", style=rs)
        head.append(f"  ({r['score']}/100)  ", style=LBL)
        head.append("· heuristic, not a spam-DB verdict", style="italic #555566")
        console.print(head)
        for reason in r["reasons"]:
            console.print(Text(f"     - {reason}", style="#9aa"))

    # Optional live enrichment
    if getattr(args, "live", False):
        live = rep.live_lookup(intel.e164 or "")
        if live is None:
            console.print(Text("  ⓘ live enrichment unavailable (set its API key — see phone_intel/_live_private.py)",
                               style="italic #555566"))
        elif "error" in live:
            console.print(Text(f"  ⚠ live: {live['error']}", style=AMBER))
        else:
            console.print(Text(
                f"  ◉ LIVE ({live.get('source')}): carrier={live.get('carrier') or '—'} "
                f"line={live.get('line_type') or '—'} valid={live.get('valid')}",
                style=CYAN))

    # Optional live fraud/spam database
    if getattr(args, "spam", False):
        s = rep.spam_lookup(intel.e164 or "")
        if s is None:
            console.print(Text("  ⓘ fraud DB unavailable (set its API key — see phone_intel/_live_private.py)",
                               style="italic #555566"))
        elif "error" in s:
            console.print(Text(f"  ⚠ fraud DB: {s['error']}", style=AMBER))
        else:
            sstyle = RISK_STYLE.get(s["level"], LBL)
            head = Text("  FRAUD DB ", style=LBL)
            head.append(f"{s['level']}", style=sstyle)
            head.append(f"  score={s.get('fraud_score')}  ", style=LBL)
            head.append(
                f"recent_abuse={s.get('recent_abuse')} risky={s.get('risky')} "
                f"active={s.get('active')}", style="#9aa")
            head.append(f"  · {s.get('source')}", style="italic #555566")
            console.print(head)

    # QR
    if getattr(args, "qr", False):
        console.print(Text("  QR · tel: URI", style=LBL))
        console.print(Text(rp.qr_ascii(intel), style="#d8d8e8"))

    console.print()


def do_one(number: str, args) -> object:
    if not args.json:
        fx.boot_sequence(console, number)
    intel = lookup(number, args.region)
    if args.json:
        print(rp.to_json(intel))
        return intel
    fx.access_granted(console, intel.valid)
    render_intel(intel, args)
    _maybe_export(intel, args)
    return intel


def _maybe_export(intel, args) -> None:
    if not args.export:
        return
    stub = rp._safe_stub(intel.e164 or intel.input)
    base = f"{args.export}_{stub}" if args.export != "out" else f"out_{stub}"
    j = base + ".json"
    rp.to_json(intel, j)
    v = base + ".vcf"
    rp.to_vcard(intel, v)
    msgs = [j, v]
    png = rp.qr_png(intel, base + ".png")
    if png:
        msgs.append(png)
    console.print(Text("  ⤓ exfil report -> " + ", ".join(msgs), style=GREEN))


def do_batch(path: str, args) -> None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            numbers = [ln.strip() for ln in f if ln.strip()
                       and not ln.strip().startswith("#")]
    except OSError as e:
        console.print(Text(f"✗ cannot read batch file: {e}", style=RED))
        sys.exit(1)

    console.print(Text(f"> BATCH RECON  [ {len(numbers)} targets ]\n", style=CYAN))
    intels = []
    for n in numbers:
        intel = lookup(n, args.region)
        intels.append(intel)

    summary = Table(title="BATCH RECON SUMMARY", box=box.HEAVY,
                    border_style="#00ff41", title_style=GREEN, expand=True)
    for col in ["#", "INPUT", "CC", "COUNTRY", "REGION", "CARRIER", "TYPE", "OK"]:
        summary.add_column(col, style="#d8d8e8", no_wrap=(col in {"#", "CC", "OK"}))
    for i, it in enumerate(intels, 1):
        ok = "✔" if it.valid else ("~" if it.ok else "✗")
        ok_style = GREEN if it.valid else (AMBER if it.ok else RED)
        summary.add_row(
            str(i), it.input, (f"+{it.calling_code}" if it.calling_code else "—"),
            (it.country_name or "—")[:18], (it.region or "—")[:22],
            (it.carrier or "—")[:16], (it.line_type_code or "—"),
            Text(ok, style=ok_style))
    console.print(summary)

    if args.json:
        print(rp.to_json_list(intels))
    if args.export:
        csv_path = (args.export if args.export.endswith(".csv")
                    else args.export + "_batch.csv")
        rp.batch_to_csv(intels, csv_path)
        console.print(Text(f"\n  ⤓ exfil summary -> {csv_path}", style=GREEN))


def interactive(args) -> None:
    console.print(Text("Entering recon shell. Type a number, or 'q' to quit.\n",
                       style=LBL))
    while True:
        try:
            raw = console.input(Text("phone_intel ▶ ", style=GREEN))
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        raw = raw.strip()
        if raw.lower() in {"q", "quit", "exit"}:
            break
        if not raw:
            continue
        do_one(raw, args)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="phone_intel",
        description="Legitimate phone-number intelligence (registration metadata only).")
    p.add_argument("number", nargs="?", help="Phone number, ideally E.164 (+14155552671).")
    p.add_argument("-r", "--region", help="Default ISO region for national-format numbers (e.g. US).")
    p.add_argument("--batch", metavar="FILE", help="File with one number per line.")
    p.add_argument("--export", metavar="PREFIX", help="Write JSON/vCard/QR (and CSV for batch).")
    p.add_argument("--json", action="store_true", help="Emit raw JSON (no theatrics).")
    p.add_argument("--qr", action="store_true", help="Show an ASCII QR of the tel: URI.")
    p.add_argument("--live", action="store_true",
                   help="Live carrier/validity enrichment (optional; needs the private live module + key).")
    p.add_argument("--spam", action="store_true",
                   help="Live fraud/spam reputation (optional; needs the private live module + key).")
    p.add_argument("--no-reputation", dest="reputation", action="store_false",
                   help="Hide the heuristic risk assessment.")
    p.add_argument("--matrix", action="store_true", help="Matrix-rain intro. Pure vibes.")
    p.add_argument("--no-fx", action="store_true", help="Disable all animations (instant).")
    p.add_argument("-V", "--version", action="version",
                   version=f"phone_intel {__version__}")
    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    fx.set_fx(not args.no_fx and not args.json)

    if not args.json:
        fx.banner(console)
        if args.matrix:
            fx.matrix_rain(console)

    if args.batch:
        do_batch(args.batch, args)
    elif args.number:
        do_one(args.number, args)
    else:
        interactive(args)


if __name__ == "__main__":
    main()
