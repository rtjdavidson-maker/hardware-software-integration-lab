"""Run a serial integration session in simulated or explicit real-hardware mode."""
import argparse
from pathlib import Path
from integration import DeviceSession, generate_report
from transports import RealSerialTransport, SimulatedTransport


def make_parser():
    parser = argparse.ArgumentParser(description="ESP32-style serial integration simulator and test tool")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true", help="Use deterministic simulator; no serial hardware")
    mode.add_argument("--port", help="Real serial port (e.g. COM4 on Windows or /dev/ttyUSB0 on Linux)")
    parser.add_argument("--samples", type=int, default=10, help="Number of telemetry messages, 1–500")
    parser.add_argument("--interval", type=int, default=1000, help="Sampling interval, 200–10000 ms")
    parser.add_argument("--led", choices=["ON", "OFF"], default="ON", help="Device LED command")
    parser.add_argument("--output", default="output", help="Output folder")
    return parser


def run(argv=None):
    parser = make_parser()
    options = parser.parse_args(argv)
    if not 1 <= options.samples <= 500:
        parser.error("--samples must be between 1 and 500")
    if not 200 <= options.interval <= 10000:
        parser.error("--interval must be between 200 and 10000")
    transport = SimulatedTransport() if options.demo else RealSerialTransport(options.port)
    session = DeviceSession(transport)
    try:
        session.send("PING")
        session.send("INTERVAL", options.interval)
        session.send("LED", options.led)
        session.collect(options.samples)
        json_path, html_path, report = generate_report(session, Path(options.output))
        print("MODE: SIMULATED SERIAL TRANSPORT — NO HARDWARE" if options.demo else f"MODE: REAL SERIAL DEVICE — {options.port}")
        print(f"Samples received: {report['samples']} | Alerts: {report['alerts']}")
        print(f"Command acknowledgments: {len(report['acks'])} | Protocol errors: {len(report['errors'])}")
        for sample in report["measurements"]:
            print(f"{sample['device']} #{sample['seq']:02d} {sample['voltage_v']:.3f} V "
                  f"{sample['temperature_c']:.2f} °C LED={sample['led_on']} {sample['status']}")
        print(f"Saved JSON: {json_path.resolve()}")
        print(f"Saved HTML: {html_path.resolve()}")
        print('Windows: start "" "output\\dashboard.html"')
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(run())
