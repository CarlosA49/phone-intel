# 📡 PHONE_INTEL — Phone Number Intelligence Terminal

A hacker-themed OSINT tool that, given a phone number, shows **everything that is
legitimately derivable from the number itself**: the country and region it's
*registered* to, the carrier, line type, validity, timezone, and the current
local time there. Terminal (TUI) **and** web interfaces, both powered by one
honest Python engine.

```
 ___ __  __ ___    _    ___  ___   _ _____ ___  ___
/ __|  \/  / __|  | |  / _ \/ __| /_\_   _/ _ \| _ \
\__ \ |\/| \__ \  | |_| (_) \__ \/ _ \| || (_) |   /
|___/_|  |_|___/  |____\___/|___/_/ \_\_| \___/|_|_\
```

## ⚖️ What this does — and what it deliberately does NOT do

This tool reports **number metadata**. It does **not** identify the *owner* and
it does **not** track a person's live location, because **neither is derivable
from a phone number**. Any site that claims to reveal a stranger's name or live
GPS from their number is a scam, a data-broker reselling breach data, or malware.

| ✅ It DOES show (real, from the number) | ❌ It does NOT do (impossible / off-limits) |
|---|---|
| Country & calling code | Owner's name or identity |
| **Registration region** (e.g. "San Francisco, CA") | The person's **live** location / GPS |
| Carrier / network operator | Home address |
| Line type (mobile / VoIP / landline / toll-free…) | Social-media or account de-anonymization |
| Validity & all number formats | Anything requiring carrier/warrant/malware access |
| Timezone + **live local clock** | |

> **"Region" always means where the number is *registered*, never where the
> holder currently is.** Real-time tracking of a person requires their consent
> (Find My / location sharing) or a lawful warrant — full stop.

## 🚀 Install

```bash
pip install -r requirements.txt        # quick start
# — or install as a package so `phone-intel` is on your PATH:
pip install -e .                       # core CLI
pip install -e ".[web]"                # + Flask web app
```

Then run `phone-intel +14155552671` (or `python -m phone_intel +14155552671`).

Requires Python 3.9+ (tested on 3.12). Dependencies: `phonenumbers` (Google's
libphonenumber dataset), `rich`, `qrcode`, `requests`; `flask` for the web app.

## 🖥️ Terminal (TUI)

```bash
# single number
python -m phone_intel +14155552671
scan.bat +14155552671               # Windows convenience launcher

# with an ASCII QR of the tel: URI, and live API enrichment
python -m phone_intel "+63 917 123 4567" --qr --live

# batch recon from a file (one number per line, '#' = comment)
python -m phone_intel --batch numbers.txt

# export JSON + vCard + QR.png (and CSV for batch)
python -m phone_intel +442079460958 --export out

# raw JSON, no theatrics (good for piping)
python -m phone_intel +14155552671 --json

# interactive recon shell (no argument)
python -m phone_intel
```

### Flags
| Flag | Effect |
|---|---|
| `-r, --region ISO` | Default region for national-format numbers (e.g. `US`) |
| `--batch FILE` | Scan many numbers, print a summary table |
| `--export PREFIX` | Write JSON / vCard / QR-PNG (+ CSV in batch mode) |
| `--qr` | Render an ASCII QR code of the `tel:` URI |
| `--live` | Live carrier/validity enrichment (optional; needs the private live module + key) |
| `--spam` | Live fraud/spam score (optional; needs the private live module + key) |
| `--json` | Emit raw JSON, skip all animations |
| `--matrix` | Matrix-rain intro (pure vibes) |
| `--no-reputation` | Hide the heuristic risk assessment |
| `--no-fx` | Disable all animations (instant) |

## 🌐 Web terminal

```bash
python web/app.py        # -> http://127.0.0.1:5000
run_web.bat              # Windows
```

Matrix-rain background, scan animation, live ticking clock, a dark Leaflet map
centered on the **registration region** (clearly labelled "not a person"), a
heuristic risk chip, and JSON copy/export. The browser is a thin client — the
same Python engine does the real work via `/api/lookup`.

## 🧠 Features

- **Real data** via Google's libphonenumber: country, region, carrier, line type, timezone, validity.
- **Live local clock** ⏱ — current wall-clock time at the number's timezone, ticking.
- **Reputation heuristic** — flags structural risk signals (premium-rate, VoIP/disposable, invalid). Clearly labelled as a heuristic, *not* a spam-database verdict.
- **Batch recon** — scan a list, get a summary table / CSV.
- **Exports** — JSON, CSV, vCard (`.vcf`, number metadata only), QR code (ASCII + PNG).
- **Optional live enrichment** — pluggable live carrier + fraud-score providers via a private module (not included here); the public build runs fully offline.
- **Fully offline web map** — world borders are vendored locally (no tile servers, no external calls); CSP is same-origin only.
- **`pip install`-able** — exposes a `phone-intel` command; `pip install -e ".[web]"` adds the Flask app.
- **Two front ends, one engine** — identical results in terminal and browser.

## 🔌 Optional: live enrichment & fraud database

The `--live` (carrier/validity) and `--spam` (fraud score) features are powered by
a **private integration module that is intentionally not included in this
repository**. Without it, everything still works offline from the bundled
libphonenumber dataset — `--live` / `--spam` simply report "unavailable".

With the private module installed, set the relevant API key in your environment
to enable each feature. Neither integration reveals an owner's identity or live
location.

## 🗂️ Layout

```
phone_intel/        # the engine (importable package)
  core.py           # lookup() -> Intel  (real data only)
  reputation.py     # heuristic risk + optional live API
  report.py         # JSON / CSV / vCard / QR exporters
  effects.py        # hacker-terminal animations (cosmetic)
  cli.py            # TUI front end
  countries.py      # public country geo data (auto-generated)
web/
  app.py            # Flask backend (/api/lookup)
  templates/, static/
numbers.txt         # sample batch input
```

## 📋 Note on `index.html`

The original standalone `index.html` at the repo root (legacy "v1") contained a
**simulated subscriber-name generator** — it invented a random fake "SUBSCRIBER
NAME" for every number and presented it as a real lookup. That was deceptive, so
the page has been **replaced with a static notice** explaining why it was retired
and pointing to the real tool. It performs no lookups. Use the `web/` app or the
TUI for actual results.

---

*Educational / legitimate use only. Number metadata is public-numbering-plan
data. This tool does not store data, identify owners, or track people.*
