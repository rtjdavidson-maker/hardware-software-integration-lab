# Hardware/Software Integration Lab — Python ↔ ESP32 Serial Protocol

A portfolio-ready **systems integration project** for structured data exchange between a Python desktop application and an ESP32-style device. The same newline-delimited message protocol works with either an offline Python device emulator or an optional USB serial connection to ESP32 firmware.

> **Scope:** The default demo is simulated: no physical sensors, voltages, or temperatures are measured. Even the optional ESP32 firmware reports synthetic measurements. Physical ESP32 communication has **not yet been validated**. Do not use this example for safety-critical equipment.

## Highlights

- Host commands: `PING`, `LED:ON`, `LED:OFF`, and `INTERVAL:1000`
- JSON telemetry with device ID, sequence, uptime, voltage, temperature, and LED state
- Command acknowledgments handled separately from measurements
- Validation of message type, required fields, lengths and value ranges
- Interchangeable simulated serial and optional `pyserial` hardware transports
- HTML dashboard, structured JSON report, 27 Python unit tests and GitHub Actions CI
- ESP32 Arduino firmware sketch for later low-voltage experiments

## Quick start — Windows

Download the latest repository ZIP, **Extract All**, and open the folder containing `main.py` in File Explorer. Click the address bar, type `cmd`, and press Enter.

Run these commands **one at a time**:

```cmd
python main.py --demo
start "" "output\dashboard.html"
python -m unittest discover -s tests -v
```

**Expected sample demo results:** 10 telemetry samples, 3 command acknowledgments, zero errors and no alerts. All demo measurements fall within educational example thresholds. The generated files are `output/telemetry.json` and `output/dashboard.html`. No additional Python packages are required for demo mode.

Try another simulated scenario:

```cmd
python main.py --demo --samples 15 --interval 500 --led OFF
```

## Verified Windows demonstration — screenshots

These five captures document **simulated** host/device communication and local tests on Windows. They do not demonstrate live physical ESP32 measurements.

### 1. Console: commands, acknowledgments and simulated device telemetry

The demo processed **10 readings and 3 command acknowledgments**, with zero protocol errors. It produced JSON and HTML reports.

![Command Prompt showing simulated serial communication, ten samples, and three ACKs](Screenshot%202026-11-21%20151347.png)

### 2. Integration test suite and validation cases

The test output demonstrates protocol parsing, device commands, malformed message handling, timing checks, and report generation.

![Windows terminal running automated protocol and integration tests](Screenshot%202026-11-21%20151444.png)

### 3. All 27 automated Python tests passed

The final test output displays `Ran 27 tests` and `OK`.

![Successful completion of all 27 automated tests](Screenshot%202026-11-21%20151520.png)

### 4. HTML telemetry dashboard overview

The dashboard summarizes **10 samples, zero alerts, 3 acknowledgments, and zero protocol errors**, along with voltage, temperature, simulated LED status, and device sequence numbers.

![HTML integration lab telemetry dashboard summary](Screenshot%202026-11-21%20151551.png)

### 5. Detailed simulated device measurements

The continued table displays sequential readings from `ESP32-SIM-01`, classified as inside demonstration thresholds.

![Detailed telemetry table for simulated ESP32 serial readings](Screenshot%202026-11-21%20151609.png)

## Data flow

```text
Python CLI (main.py)
       |
       v
DeviceSession (integration.py) ←→ Protocol validation (protocol.py)
       |
       v
SimulatedTransport or RealSerialTransport (transports.py)
       |
       v
ESP32 emulator or future physical ESP32 firmware
       |
       v
Telemetry JSON + HTML monitoring dashboard
```

## Real USB serial mode — optional and not yet tested

This requires a supported ESP32 board, USB data cable, correct firmware flashing, and `pyserial`.

```cmd
python -m pip install pyserial
python -m serial.tools.list_ports
python main.py --port COM4 --samples 10
```

Replace `COM4` with the actual port for your board. Close Arduino Serial Monitor before Python connects. On Linux, ports might be named `/dev/ttyUSB0` or `/dev/ttyACM0`.

Firmware: `firmware/ESP32SerialTelemetry/ESP32SerialTelemetry.ino`. The sketch uses optional GPIO 2 LED output, which is board-dependent. Verify pinout and current-limiting requirements before connecting anything.

## Protocol example

Host sends plain ASCII lines:

```text
PING
INTERVAL:1000
LED:ON
```

Device answers with newline-delimited JSON:

```json
{"type":"ack","command":"PING","status":"OK"}
{"type":"telemetry","device":"ESP32-SIM-01","seq":1,"uptime_ms":1000,"voltage_v":3.33,"temperature_c":26.2,"led_on":true}
```

The sample telemetry above is illustrative. Demo-mode values are deterministic simulated readings.

## Repository contents

| File | Role |
|---|---|
| `main.py` | CLI runner for demo or optional serial-port mode |
| `protocol.py` | Validated message schema and command encoding |
| `transports.py` | Device emulator and physical serial abstraction |
| `integration.py` | Session orchestration, classification, JSON and HTML reports |
| `tests/test_integration.py` | 27 automated protocol and integration tests |
| `firmware/ESP32SerialTelemetry/ESP32SerialTelemetry.ino` | Firmware for future ESP32 experiment |
| `.github/workflows/python-tests.yml` | Continuous integration checks |

## Engineering significance and next steps

This project demonstrates serial protocol design, framing, transport abstraction, error handling, reproducible integration tests and diagnostic visualization. It is relevant to Systems Integration, Embedded Software, Hardware Validation and Test Automation engineering.

**Next milestones:** test actual USB serial transport with an ESP32, detect missing sequence numbers, measure reconnections and timing, and add a timestamped telemetry database. Document hardware results separately from simulations.
