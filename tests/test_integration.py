import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from protocol import Telemetry, ProtocolError, parse_telemetry, encode_command, decode_response
from transports import SimulatedTransport
from integration import DeviceSession, classify, generate_report
import main


class ProtocolTests(unittest.TestCase):
    def test_valid_telemetry(self):
        text = json.dumps({"type":"telemetry","device":"ESP32","seq":1,"uptime_ms":1000,
                           "voltage_v":3.3,"temperature_c":25.0,"led_on":True})
        sample = parse_telemetry(text)
        self.assertEqual(sample.seq, 1)
        self.assertTrue(sample.led_on)

    def test_invalid_json_rejected(self):
        with self.assertRaises(ProtocolError):
            parse_telemetry("broken{")

    def test_wrong_type_rejected(self):
        with self.assertRaises(ProtocolError):
            parse_telemetry('{"type":"ack"}')

    def test_missing_field_rejected(self):
        with self.assertRaises(ProtocolError):
            parse_telemetry('{"type":"telemetry","device":"a"}')

    def test_boolean_sequence_rejected(self):
        with self.assertRaises(ProtocolError):
            parse_telemetry('{"type":"telemetry","device":"a","seq":true,"uptime_ms":1,"voltage_v":3.3,"temperature_c":25,"led_on":true}')

    def test_large_payload_rejected(self):
        with self.assertRaises(ProtocolError):
            parse_telemetry("x" * 2100)

    def test_ping_encoding(self):
        self.assertEqual(encode_command("PING"), b"PING\n")

    def test_led_encoding(self):
        self.assertEqual(encode_command("LED", "ON"), b"LED:ON\n")

    def test_interval_encoding(self):
        self.assertEqual(encode_command("INTERVAL", 1200), b"INTERVAL:1200\n")

    def test_invalid_command_rejected(self):
        with self.assertRaises(ProtocolError):
            encode_command("RUN_SHELL", "dir")

    def test_invalid_interval_rejected(self):
        with self.assertRaises(ProtocolError):
            encode_command("INTERVAL", 5)

    def test_ack_parse(self):
        self.assertEqual(decode_response('{"type":"ack","command":"PING","status":"OK"}')["status"], "OK")


class IntegrationTests(unittest.TestCase):
    def test_simulator_deterministic(self):
        a = SimulatedTransport(seed=11)
        b = SimulatedTransport(seed=11)
        self.assertEqual([a.readline() for _ in range(3)], [b.readline() for _ in range(3)])

    def test_led_switch_changes_telemetry(self):
        transport = SimulatedTransport()
        session = DeviceSession(transport)
        session.send("LED", "ON")
        session.collect(1)
        self.assertTrue(session.telemetry[0].led_on)
        self.assertEqual(len(session.acks), 1)

    def test_interval_changes_timing(self):
        session = DeviceSession(SimulatedTransport())
        session.send("INTERVAL", 500)
        session.collect(2)
        self.assertEqual(session.telemetry[1].uptime_ms, 1000)

    def test_invalid_transport_command_produces_error_ack(self):
        transport = SimulatedTransport()
        transport.write(b"COMMAND:INVALID\n")
        self.assertEqual(decode_response(transport.readline().decode())["status"], "ERROR")

    def test_multiple_acks_separated_from_telemetry(self):
        session = DeviceSession(SimulatedTransport())
        session.send("PING")
        session.send("INTERVAL", 1000)
        session.send("LED", "OFF")
        session.collect(4)
        self.assertEqual(len(session.acks), 3)
        self.assertEqual(len(session.telemetry), 4)

    def test_bad_utf8_handled(self):
        transport = SimulatedTransport()
        transport.messages.append(b"\xff\xfe\n")
        session = DeviceSession(transport)
        session.collect(1)
        self.assertEqual(len(session.errors), 1)

    def test_zero_samples_rejected(self):
        with self.assertRaises(ValueError):
            DeviceSession(SimulatedTransport()).collect(0)

    def test_timeout_on_empty_reads(self):
        class EmptyTransport:
            def readline(self):
                return b""
        with self.assertRaises(TimeoutError):
            DeviceSession(EmptyTransport()).collect(1, max_attempts=2)

    def test_good_reading_classifies_ok(self):
        self.assertEqual(classify(Telemetry("X", 1, 100, 3.3, 25, False))[0], "OK")

    def test_high_temperature_classifies_alert(self):
        self.assertEqual(classify(Telemetry("X", 1, 100, 3.3, 50, False))[0], "ALERT")

    def test_report_created(self):
        session = DeviceSession(SimulatedTransport())
        session.collect(3)
        with TemporaryDirectory() as tmp:
            jp, hp, report = generate_report(session, Path(tmp))
            self.assertTrue(jp.exists() and hp.exists())
            self.assertEqual(report["samples"], 3)

    def test_report_escapes_device(self):
        session = DeviceSession(SimulatedTransport())
        session.telemetry = [Telemetry("<script>", 1, 100, 3.3, 25, False)]
        with TemporaryDirectory() as tmp:
            _, hp, _ = generate_report(session, Path(tmp))
            html = hp.read_text()
            self.assertIn("&lt;script&gt;", html)
            self.assertNotIn("<script>", html)

    def test_cli_demo(self):
        with TemporaryDirectory() as tmp:
            result = main.run(["--demo", "--samples", "3", "--output", tmp])
            self.assertEqual(result, 0)
            self.assertTrue((Path(tmp) / "dashboard.html").exists())

    def test_cli_requires_mode(self):
        with self.assertRaises(SystemExit):
            main.run([])

    def test_cli_rejects_bad_interval(self):
        with self.assertRaises(SystemExit):
            main.run(["--demo", "--interval", "10"])


if __name__ == "__main__":
    unittest.main()
