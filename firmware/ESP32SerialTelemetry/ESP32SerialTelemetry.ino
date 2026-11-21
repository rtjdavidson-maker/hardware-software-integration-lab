/*
  ESP32 serial telemetry demonstration (educational low-voltage hardware only).
  Matches Python protocol.py. Samples are SYNTHETIC, even on a real ESP32.
  No external sensor is connected or measured by this sketch.
  Built-in LED availability/pin varies by ESP32 board. GPIO 2 is optional.
  Use only a board-supported LED with proper current limiting.
*/

#include <Arduino.h>

static const int DEMO_LED_PIN = 2;
static bool ledOn = false;
static unsigned long intervalMs = 1000;
static unsigned long lastSend = 0;
static uint32_t sequence = 0;
static String inputBuffer;

void reply(const String& command, const char* status) {
  Serial.print("{\"type\":\"ack\",\"command\":\"");
  // Only the allowlisted strings are passed here, never arbitrary input.
  Serial.print(command);
  Serial.print("\",\"status\":\"");
  Serial.print(status);
  Serial.println("\"}");
}

void handleCommand(String cmd) {
  cmd.trim();
  if (cmd == "PING") {
    reply("PING", "OK");
  } else if (cmd == "LED:ON") {
    ledOn = true;
    digitalWrite(DEMO_LED_PIN, HIGH);
    reply("LED:ON", "OK");
  } else if (cmd == "LED:OFF") {
    ledOn = false;
    digitalWrite(DEMO_LED_PIN, LOW);
    reply("LED:OFF", "OK");
  } else if (cmd.startsWith("INTERVAL:")) {
    String digits = cmd.substring(9);
    bool numeric = digits.length() > 0 && digits.length() <= 5;
    for (unsigned int i = 0; i < digits.length(); ++i) {
      if (!isDigit(digits[i])) numeric = false;
    }
    long n = numeric ? digits.toInt() : -1;
    if (n >= 200 && n <= 10000) {
      intervalMs = static_cast<unsigned long>(n);
      reply(cmd, "OK");
    } else {
      reply("INTERVAL", "ERROR");
    }
  } else {
    reply("UNKNOWN", "ERROR");
  }
}

void sendTelemetry() {
  sequence++;
  const float voltageV = 3.30f + 0.08f * sinf(sequence * 0.73f);
  const float tempC = 25.0f + 3.0f * sinf(sequence * 0.39f);
  Serial.print("{\"type\":\"telemetry\",\"device\":\"ESP32-DEMO-01\",\"seq\":");
  Serial.print(sequence);
  Serial.print(",\"uptime_ms\":");
  Serial.print(millis());
  Serial.print(",\"voltage_v\":");
  Serial.print(voltageV, 3);
  Serial.print(",\"temperature_c\":");
  Serial.print(tempC, 2);
  Serial.print(",\"led_on\":");
  Serial.print(ledOn ? "true" : "false");
  Serial.println("}");
}

void setup() {
  pinMode(DEMO_LED_PIN, OUTPUT);
  digitalWrite(DEMO_LED_PIN, LOW);
  Serial.begin(115200);
  inputBuffer.reserve(80);
  lastSend = millis();
}

void loop() {
  while (Serial.available()) {
    const char ch = static_cast<char>(Serial.read());
    if (ch == '\n') {
      handleCommand(inputBuffer);
      inputBuffer = "";
    } else if (ch != '\r') {
      if (inputBuffer.length() < 75) inputBuffer += ch;
      else inputBuffer = "";  // drop overlong commands
    }
  }
  unsigned long now = millis();
  if (now - lastSend >= intervalMs) {
    lastSend = now;
    sendTelemetry();
  }
}
