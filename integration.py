"""High-level integration session with message classification and reporting."""
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from html import escape
import json

from protocol import ProtocolError, decode_response, encode_command, parse_telemetry


class DeviceSession:
    def __init__(self, transport):
        self.transport = transport
        self.telemetry = []
        self.acks = []
        self.errors = []

    def send(self, command, value=None):
        self.transport.write(encode_command(command, value))

    def collect(self, count: int = 10, *, max_attempts: int | None = None):
        if not 1 <= count <= 500:
            raise ValueError("count must be between 1 and 500")
        limit = max_attempts if max_attempts is not None else count * 5 + 10
        if limit < count:
            raise ValueError("max_attempts must be >= count")
        attempts = 0
        while len(self.telemetry) < count and attempts < limit:
            attempts += 1
            raw = self.transport.readline()
            if not raw:
                self.errors.append("Timed out waiting for a serial line")
                continue
            try:
                line = raw.decode("utf-8").strip()
            except UnicodeDecodeError:
                self.errors.append("Invalid UTF-8 serial line")
                continue
            try:
                data = json.loads(line)
                if isinstance(data, dict) and data.get("type") == "ack":
                    self.acks.append(decode_response(line))
                else:
                    self.telemetry.append(parse_telemetry(line))
            except (ValueError, ProtocolError) as exc:
                self.errors.append(str(exc))
        if len(self.telemetry) < count:
            raise TimeoutError(f"Received {len(self.telemetry)}/{count} telemetry samples after {attempts} reads")
        return self.telemetry

    def close(self):
        self.transport.close()


def classify(reading):
    problems = []
    if not 3.0 <= reading.voltage_v <= 3.5:
        problems.append("Voltage outside demonstration range")
    if not 10 <= reading.temperature_c <= 40:
        problems.append("Temperature outside demonstration range")
    return ("ALERT", "; ".join(problems)) if problems else ("OK", "Within demonstration thresholds")


def generate_report(session: DeviceSession, folder: Path):
    if not session.telemetry:
        raise ValueError("No telemetry to report")
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for sample in session.telemetry:
        status, detail = classify(sample)
        rows.append({**asdict(sample), "status": status, "detail": detail})
    report = {"project": "Hardware/Software Integration Lab",
              "generated_utc": datetime.now(timezone.utc).isoformat(),
              "samples": len(rows), "alerts": sum(row["status"] == "ALERT" for row in rows),
              "acks": session.acks, "errors": session.errors, "measurements": rows}
    json_path = folder / "telemetry.json"
    html_path = folder / "dashboard.html"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    table_rows = []
    for row in rows:
        style = "bad" if row["status"] == "ALERT" else "good"
        table_rows.append(
            f'<tr><td>{escape(row["device"])}</td><td>{row["seq"]}</td><td>{row["uptime_ms"]}</td>'
            f'<td>{row["voltage_v"]:.3f}</td><td>{row["temperature_c"]:.2f}</td>'
            f'<td>{"ON" if row["led_on"] else "OFF"}</td>'
            f'<td class="{style}">{row["status"]}</td><td>{escape(row["detail"])}</td></tr>'
        )
    css = """<style>:root{font-family:system-ui,sans-serif;background:#0e1829;color:#eaf1fa}main{max-width:1150px;margin:40px auto;padding:0 20px}h1{font-size:2rem}p{color:#b2c4d8}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}.card,.panel{padding:20px;background:#1c2d45;border:1px solid #395574;border-radius:13px}.card strong{display:block;font-size:2.1rem;margin-top:7px}.panel{margin-top:18px;overflow:auto}table{width:100%;border-collapse:collapse;min-width:850px;text-align:left}td,th{padding:11px;border-bottom:1px solid #38516a}.good{color:#50e6af}.bad{color:#ff91a1}</style>"""
    html_path.write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Serial Telemetry Dashboard</title>'
        + css + '</head><body><main><h1>Hardware / Software Integration Lab</h1><p>Serial-protocol telemetry. Check run mode in terminal; demo values are simulated, not physical sensor readings.</p>'
        + f'<section class="metrics"><div class="card">Samples<strong>{len(rows)}</strong></div><div class="card">Alerts<strong>{report["alerts"]}</strong></div><div class="card">Command ACKs<strong>{len(session.acks)}</strong></div><div class="card">Protocol errors<strong>{len(session.errors)}</strong></div></section>'
        + '<section class="panel"><h2>Device telemetry</h2><table><thead><tr><th>Device</th><th>Sequence</th><th>Uptime (ms)</th><th>Voltage (V)</th><th>Temperature (°C)</th><th>LED</th><th>Status</th><th>Detail</th></tr></thead><tbody>'
        + "".join(table_rows) + '</tbody></table></section><p>Educational software. No real device has been validated in demo mode.</p></main></body></html>',
        encoding="utf-8")
    return json_path, html_path, report
