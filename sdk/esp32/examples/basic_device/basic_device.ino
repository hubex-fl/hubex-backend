/**
 * basic_device.ino — Minimal HUBEX device example
 *
 * This sketch demonstrates the full HUBEX lifecycle:
 *   1. Connect to WiFi
 *   2. Pair with HUBEX (blocks until user claims the device)
 *   3. Loop: heartbeat + read sensors + push telemetry + check OTA
 *
 * Hardware: Any ESP32 board. Simulates a temperature/humidity sensor.
 *
 * Required libraries (install via Library Manager):
 *   - ArduinoJson by Benoit Blanchon (>= 7.x)
 *
 * Configuration: fill in the #define values below.
 */

#include <WiFi.h>
#include "HubexClient.h"

// ---------------------------------------------------------------------------
// Configuration — fill these in
// ---------------------------------------------------------------------------

#define WIFI_SSID      "your-wifi-ssid"
#define WIFI_PASS      "your-wifi-password"

#define HUBEX_SERVER   "http://192.168.1.100:8000"   // or "https://your-hubex.example.com"
#define DEVICE_UID     "esp32-basic-001"             // unique ID for this device
#define FIRMWARE_VER   "1.0.0"

// Set true in production to verify TLS certs; false for local dev
#define SKIP_TLS       true

// How often to send heartbeat + telemetry (milliseconds)
#define LOOP_INTERVAL_MS  30000

// ---------------------------------------------------------------------------
// Globals
// ---------------------------------------------------------------------------

HubexClient hubex(HUBEX_SERVER, DEVICE_UID);

unsigned long lastLoop = 0;

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n=== HUBEX Basic Device ===");

    // Connect WiFi
    Serial.printf("Connecting to WiFi: %s", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\nWiFi connected — IP: %s\n", WiFi.localIP().toString().c_str());

    // Init HUBEX SDK
    hubex.begin(FIRMWARE_VER, SKIP_TLS);

    // Pair if needed (blocks until dashboard user claims the device)
    if (!hubex.isPaired()) {
        Serial.println("Open HUBEX dashboard, go to Devices → Pair Device");
        Serial.printf("Device UID: %s\n", DEVICE_UID);
    }
    hubex.ensurePaired();

    Serial.println("Device ready!");
}

// ---------------------------------------------------------------------------
// Loop
// ---------------------------------------------------------------------------

void loop() {
    unsigned long now = millis();
    if (now - lastLoop < LOOP_INTERVAL_MS) return;
    lastLoop = now;

    // --- Heartbeat ---
    HubexResult hb = hubex.heartbeat();
    if (hb) {
        Serial.println("[heartbeat] OK");
    } else {
        Serial.printf("[heartbeat] FAILED (%d): %s\n", hb.httpCode, hb.error.c_str());
    }

    // --- Read sensors (simulated) ---
    float temperature = 20.0f + (float)(random(0, 100)) / 10.0f;  // 20.0–30.0
    float humidity    = 40.0f + (float)(random(0, 400)) / 10.0f;  // 40.0–80.0
    int   rssi        = WiFi.RSSI();

    Serial.printf("[sensors] temp=%.1f°C  humidity=%.1f%%  rssi=%d dBm\n",
                  temperature, humidity, rssi);

    // --- Push telemetry ---
    HubexResult tel = hubex.pushTelemetry({
        {"temperature", temperature},
        {"humidity",    humidity},
        {"rssi",        (float)rssi},
        {"uptime_s",    (float)(millis() / 1000)},
    });
    if (tel) {
        Serial.println("[telemetry] pushed OK");
    } else {
        Serial.printf("[telemetry] FAILED (%d): %s\n", tel.httpCode, tel.error.c_str());
    }

    // --- Read config variables ---
    String reportInterval = hubex.getVar("report_interval_s", "30");
    Serial.printf("[config] report_interval_s=%s\n", reportInterval.c_str());

    // --- Check OTA ---
    HubexResult ota = hubex.checkOta();
    // Note: if update is applied, device restarts here and never reaches this line
    if (!ota) {
        Serial.printf("[ota] check failed (%d): %s\n", ota.httpCode, ota.error.c_str());
    }

    // --- Reconnect WiFi if dropped ---
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[wifi] reconnecting...");
        WiFi.reconnect();
    }
}
