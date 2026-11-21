"""Wire protocol for a simulated or physical ESP32 serial device.

One UTF-8 JSON object per newline. No arbitrary commands are executed.
"""
from dataclasses import dataclass
import json
import math


@dataclass(frozen=True)
class Telemetry:
    device: str
    seq: int
    uptime_ms: int
    voltage_v: float
    temperature_c: float
    led_on: bool


class ProtocolError(ValueError):
    """A serial message was malformed or violated the message schema."""


def parse_telemetry(line: str) -> Telemetry:
    if len(line) > 2048:
        raise ProtocolError("Message exceeds maximum length")
    try:
        data = json.loads(line)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ProtocolError("Invalid JSON telemetry") from exc
    if not isinstance(data, dict) or data.get("type") != "telemetry":
        raise ProtocolError("Expected a telemetry object")
    required = ("device", "seq", "uptime_ms", "voltage_v", "temperature_c", "led_on")
    if any(field not in data for field in required):
        raise ProtocolError("Missing required telemetry field")
    if not isinstance(data["device"], str) or not 1 <= len(data["device"]) <= 40:
        raise ProtocolError("Invalid device identifier")
    if type(data["seq"]) is not int or data["seq"] < 0:
        raise ProtocolError("Invalid sequence number")
    if type(data["uptime_ms"]) is not int or data["uptime_ms"] < 0:
        raise ProtocolError("Invalid uptime")
    if type(data["led_on"]) is not bool:
        raise ProtocolError("Invalid LED status")
    for key in ("voltage_v", "temperature_c"):
        if type(data[key]) not in (int, float) or not math.isfinite(data[key]):
            raise ProtocolError(f"Invalid {key}")
    return Telemetry(data["device"], data["seq"], data["uptime_ms"],
                     float(data["voltage_v"]), float(data["temperature_c"]), data["led_on"])


def encode_command(name: str, value=None) -> bytes:
    """Encode allowlisted commands accepted by the firmware."""
    if name == "PING" and value is None:
        command = "PING"
    elif name == "LED" and value in ("ON", "OFF"):
        command = f"LED:{value}"
    elif name == "INTERVAL" and type(value) is int and 200 <= value <= 10000:
        command = f"INTERVAL:{value}"
    else:
        raise ProtocolError("Unsupported command or value")
    return (command + "\n").encode("ascii")


def decode_response(line: str) -> dict:
    try:
        result = json.loads(line)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ProtocolError("Invalid JSON response") from exc
    if not isinstance(result, dict) or result.get("type") != "ack":
        raise ProtocolError("Expected command acknowledgment")
    if result.get("status") not in ("OK", "ERROR") or not isinstance(result.get("command"), str):
        raise ProtocolError("Malformed acknowledgment")
    return result
