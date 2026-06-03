"""Flask backend for the phone_intel web terminal.

The browser is a thin client: it POSTs a number to /api/lookup and the SAME
Python engine that powers the CLI does the real work. One source of truth, real
data only, no owner identification.
"""
from __future__ import annotations

import os
import sys

# Make the sibling phone_intel package importable when run from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, render_template, request

from phone_intel import lookup, __version__
from phone_intel import reputation as rep

app = Flask(__name__)


@app.after_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    # Defense-in-depth: contain any HTML injection. Everything is same-origin —
    # Leaflet and the world map polygons are vendored locally, so no external
    # script/img/connect origins are allowed at all.
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
    return resp


@app.errorhandler(Exception)
def on_error(e):
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return jsonify({"ok": False, "error": e.description}), e.code
    return jsonify({"ok": False, "error": "Internal error."}), 500


@app.route("/")
def index():
    return render_template("index.html", version=__version__)


@app.route("/api/lookup")
def api_lookup():
    number = request.args.get("number", "")
    region = request.args.get("region") or None
    if not number.strip():
        return jsonify({"ok": False, "error": "No number provided."}), 400
    try:
        intel = lookup(number, region)
        data = intel.to_dict()
        data["reputation"] = rep.assess(intel)
        if request.args.get("live") == "1":
            live = rep.live_lookup(intel.e164 or "")
            if live is not None:
                data["live"] = live
        if request.args.get("spam") == "1":
            spam = rep.spam_lookup(intel.e164 or "")
            if spam is not None:
                data["spam"] = spam
        return jsonify(data)
    except Exception:
        return jsonify({"ok": False, "error": "Internal error processing number."}), 500


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "version": __version__})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    print(f"\n  phone_intel web terminal -> http://127.0.0.1:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False)
