"""Interchangeable simulated and USB serial transports.

RealSerialTransport needs `pip install pyserial` and an explicit port.
"""
import json
import random
from collections import deque


class SimulatedTransport:
    """Predictable device emulator, with the same line protocol as firmware."""

    def __init__(self, seed=42, device="ESP32-SIM-01"):
        self.random = random.Random(seed)
        self.device = device
        self.interval_ms = 1000
        self.led_on = False
        self.seq = 0
        self.messages = deque()
        self.closed = False

    def write(self, data: bytes):
        if self.closed:
            raise OSError("Transport closed")
        try:
            command = data.decode("ascii").strip()
        except UnicodeDecodeError:
            command = "INVALID"
        status = "OK"
        if command == "PING":
            pass
        elif command == "LED:ON":
            self.led_on = True
        elif command == "LED:OFF":
            self.led_on = False
        elif command.startswith("INTERVAL:"):
            try:
                value = int(command.split(":", 1)[1])
                if not 200 <= value <= 10000:
                    raise ValueError
                self.interval_ms = value
            except ValueError:
                status = "ERROR"
        else:
            status = "ERROR"
        ack = {"type": "ack", "command": command, "status": status}
        self.messages.append((json.dumps(ack, separators=(",", ":")) + "\n").encode())
        return len(data)

    def readline(self) -> bytes:
        if self.closed:
            raise OSError("Transport closed")
        if self.messages:
            return self.messages.popleft()
        self.seq += 1
        reading = {
            "type": "telemetry", "device": self.device, "seq": self.seq,
            "uptime_ms": self.seq * self.interval_ms,
            "voltage_v": round(3.30 + self.random.uniform(-0.12, 0.12), 3),
            "temperature_c": round(25 + self.random.uniform(-6, 6), 2),
            "led_on": self.led_on,
        }
        return (json.dumps(reading, separators=(",", ":")) + "\n").encode()

    def close(self):
        self.closed = True


class RealSerialTransport:
    """Real serial USB device. Requires pyserial (not used in simulation)."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 3.0):
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("Install pyserial first: python -m pip install pyserial") from exc
        if not port:
            raise ValueError("An explicit serial port is required")
        self.connection = serial.Serial(port, baudrate=baudrate, timeout=timeout)

    def write(self, data: bytes):
        return self.connection.write(data)

    def readline(self) -> bytes:
        return self.connection.readline()

    def close(self):
        self.connection.close()
