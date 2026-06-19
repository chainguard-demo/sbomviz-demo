from __future__ import annotations

import io
import secrets
from dataclasses import asdict
from datetime import datetime, timezone

from flask import Flask, abort, redirect, render_template, request, url_for

from sbomviz.parser import ParsedSbom, parse_spdx_json

app = Flask(__name__)
_REPORT_STORE: dict[str, ParsedSbom] = {}


@app.template_global(name="current_year")
def current_year() -> int:
    return datetime.now(timezone.utc).year


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/upload")
def upload():
    uploaded = request.files.get("sbom_file")
    if not uploaded or not uploaded.filename:
        return render_template(
            "index.html",
            error="Please choose an SPDX SBOM JSON file to upload.",
        )

    try:
        raw_bytes = uploaded.read()
        raw_text = io.TextIOWrapper(io.BytesIO(raw_bytes), encoding="utf-8").read()
        parsed = parse_spdx_json(raw_text)
    except Exception as exc:  # noqa: BLE001
        return render_template(
            "index.html",
            error=f"Could not parse file as SPDX JSON: {exc}",
        )

    report_id = secrets.token_urlsafe(12)
    _REPORT_STORE[report_id] = parsed
    return redirect(url_for("report", report_id=report_id))


@app.get("/report/<report_id>")
def report(report_id: str):
    parsed = _REPORT_STORE.get(report_id)
    if not parsed:
        abort(404)

    query = request.args.get("q", "")
    return render_template(
        "report.html",
        report_id=report_id,
        report=asdict(parsed),
        dependencies=parsed.dependencies,
        dependency_query=query,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
