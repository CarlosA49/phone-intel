"""Hacker-terminal theatrics for the TUI. Pure cosmetics over honest data.

Every animation honours a global FX switch so `--no-fx` makes the tool instant.
The data shown after the theatrics is 100% real; the green-phosphor drama is just
for the vibe.
"""
from __future__ import annotations

import random
import time

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

GREEN = "bold #00ff41"
DIM = "#2f6f3f"
CYAN = "bold #00bfff"
AMBER = "bold #ffb700"
RED = "bold #ff3860"

BANNER = r"""
 ___ __  __ ___    _    ___  ___   _ _____ ___  ___
/ __|  \/  / __|  | |  / _ \/ __| /_\_   _/ _ \| _ \
\__ \ |\/| \__ \  | |_| (_) \__ \/ _ \| || (_) |   /
|___/_|  |_|___/  |____\___/|___/_/ \_\_| \___/|_|_\
"""

_FX_ENABLED = True


def set_fx(enabled: bool) -> None:
    global _FX_ENABLED
    _FX_ENABLED = enabled


def _sleep(seconds: float) -> None:
    if _FX_ENABLED:
        time.sleep(seconds)


def banner(console: Console) -> None:
    console.print(Text(BANNER, style=GREEN))
    sub = Text("  PHONE INTELLIGENCE TERMINAL  ::  v3.0  ::  OSINT / NUMBER RECON",
               style=DIM)
    console.print(sub)
    console.print(Text("  registration metadata only — no owner ID, no live tracking",
                       style="italic #555566"))
    console.print()


def typewriter(console: Console, text: str, style: str = GREEN,
               delay: float = 0.004, prefix: str = "") -> None:
    if not _FX_ENABLED:
        console.print(Text(prefix + text, style=style))
        return
    rendered = Text(prefix, style=style)
    for ch in text:
        rendered.append(ch, style=style)
        console.print(rendered, end="\r")
        time.sleep(delay)
    console.print(rendered)


def matrix_rain(console: Console, rows: int = 8, cols: int = 64,
                frames: int = 14) -> None:
    """A brief burst of matrix rain. No-op when FX disabled."""
    if not _FX_ENABLED:
        return
    # The in-place redraw below uses raw VT cursor escapes, which print as
    # literal junk on legacy Windows consoles (conhost without virtual-terminal
    # processing). Skip there rather than garble the screen.
    if getattr(console, "legacy_windows", False):
        return
    charset = "01ｱｲｳｴｵｶｷｸ#%@&$<>/\\|=+*"
    width = min(cols, console.width or cols)
    drops = [random.randint(-rows, 0) for _ in range(width)]
    for _ in range(frames):
        grid = []
        for y in range(rows):
            line = Text()
            for x in range(width):
                d = drops[x]
                if y == d:
                    line.append(random.choice(charset), style="bold #ccffcc")
                elif d - 4 < y < d:
                    line.append(random.choice(charset), style="#00ff41")
                elif d - 8 < y < d - 4:
                    line.append(random.choice(charset), style=DIM)
                else:
                    line.append(" ")
            grid.append(line)
        console.print(*grid, sep="\n")
        for x in range(width):
            drops[x] += 1
            if drops[x] > rows + random.randint(0, 6):
                drops[x] = random.randint(-rows, 0)
        time.sleep(0.05)
        # move cursor back up to overwrite
        console.file.write(f"\x1b[{rows}A")
    console.file.write(f"\x1b[{rows}B")


def boot_sequence(console: Console, target: str) -> None:
    """The fake 'recon' progress lines. Theatrics — the work is instant."""
    steps = [
        ("acquiring target signature", 0.25),
        ("parsing E.164 structure", 0.20),
        ("querying libphonenumber dataset", 0.30),
        ("resolving country numbering plan", 0.22),
        ("mapping carrier prefix", 0.28),
        ("triangulating registration region", 0.26),
        ("syncing timezone clock", 0.18),
        ("compiling intel report", 0.20),
    ]
    console.print(Text(f"> TARGET ACQUIRED: {target}", style=CYAN))
    for label, dur in steps:
        dots = "." * (34 - len(label))
        line = Text(f"  > {label} ", style=DIM)
        line.append(dots, style="#1f4f2f")
        console.print(line, end=" ")
        _sleep(dur * (0.4 + random.random() * 0.6) if _FX_ENABLED else 0)
        console.print(Text("OK", style=GREEN))
    console.print()


def access_granted(console: Console, valid: bool) -> None:
    if valid:
        txt = Text(" ◈ ACCESS GRANTED — INTEL DECRYPTED ◈ ", style="bold #001100 on #00ff41")
    else:
        txt = Text(" ◈ PARTIAL MATCH — NUMBER FAILED VALIDATION ◈ ",
                   style="bold #1a1000 on #ffb700")
    console.print(Align.center(txt))
    console.print()


def scan_line(console: Console) -> None:
    console.print(Text("─" * (min(console.width, 70)), style=DIM))
