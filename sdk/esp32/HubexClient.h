/**
 * HubexClient.h — ESP32 Arduino SDK for HUBEX IoT Hub
 *
 * Single-header library. Dependencies:
 *   - ArduinoJson  >= 7.x   (Library Manager: "ArduinoJson" by Bblanchon)
 *   - HTTPClient              (bundled with ESP32 Arduino core)
 *   - WiFiClientSecure        (bundled with ESP32 Arduino core)
 *   - Preferences             (bundled with ESP32 Arduino core — for token storage)
 *
 * Quick start:
 *   #include "HubexClient.h"
 *   HubexClient hubex("https://your-hubex-server.com", "my-device-uid");
 *
 *   void setup() {
 *     hubex.begin("1.0.0");           // firmware version
 *     hubex.ensurePaired();           // blocks until user claims device
 *   }
 *   void loop() {
 *     hubex.heartbeat();
 *     hubex.pushTelemetry({{"temp", 23.5}, {"humidity", 60}});
 *     hubex.checkOta();               // triggers update if available
 *     delay(30000);
 *   }
 *
 * Copyright (c) 2026 HUBEX Project — MIT License
 */

#pragma once
#ifndef HUBEX_CLIENT_H
#define HUBEX_CLIENT_H

#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <Update.h>
#include <initializer_list>
#include <utility>

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

#ifndef HUBEX_PAIRING_POLL_INTERVAL_MS
#define HUBEX_PAIRING_POLL_INTERVAL_MS 5000
#endif

#ifndef HUBEX_HTTP_TIMEOUT_MS
#define HUBEX_HTTP_TIMEOUT_MS 10000
#endif

#ifndef HUBEX_NVS_NAMESPACE
#define HUBEX_NVS_NAMESPACE "hubex"
#endif

// ---------------------------------------------------------------------------
// Result type
// ---------------------------------------------------------------------------

struct HubexResult {
    bool ok;
    int  httpCode;   // -1 = network error
    String error;   // human-readable error string on failure

    explicit operator bool() const { return ok; }
};

// ---------------------------------------------------------------------------
// Telemetry payload helper
// ---------------------------------------------------------------------------

using HubexField = std::pair<const char*, float>;

// ---------------------------------------------------------------------------
// OTA info
// ---------------------------------------------------------------------------

struct HubexOtaInfo {
    bool     available;
    int      rolloutId;
    String   version;
    String   binaryUrl;
    String   checksum;
};

// ---------------------------------------------------------------------------
// HubexClient
// ---------------------------------------------------------------------------

class HubexClient {
public:
    /**
     * @param serverUrl   Base URL of the HUBEX server, e.g. "https://hub.example.com"
     * @param deviceUid   Unique device identifier, e.g. "esp32-abc123"
     */
    HubexClient(const char* serverUrl, const char* deviceUid)
        : _serverUrl(serverUrl), _deviceUid(deviceUid) {}

    // -----------------------------------------------------------------------
    // Setup
    // -----------------------------------------------------------------------

    /**
     * Call once in setup(). Loads stored device token from NVS.
     * @param firmwareVersion  Semver string reported to server, e.g. "1.2.3"
     * @param skipTls          Set true to skip TLS certificate verification (dev only)
     */
    void begin(const char* firmwareVersion = "0.0.0", bool skipTls = false) {
        _fwVersion = firmwareVersion;
        _skipTls   = skipTls;
        _prefs.begin(HUBEX_NVS_NAMESPACE, false);
        _deviceToken = _prefs.getString("device_token", "");
        _deviceId    = _prefs.getInt("device_id", -1);
        if (_deviceToken.length() > 0) {
            Serial.printf("[HUBEX] Loaded token for device_id=%d\n", _deviceId);
        } else {
            Serial.println("[HUBEX] No token stored — need pairing");
        }
    }

    /** Returns true if the device has a stored token (is paired). */
    bool isPaired() const { return _deviceToken.length() > 0; }

    /** Clears stored token — forces re-pairing on next ensurePaired(). */
    void clearToken() {
        _prefs.remove("device_token");
        _prefs.remove("device_id");
        _deviceToken = "";
        _deviceId    = -1;
        Serial.println("[HUBEX] Token cleared");
    }

    // -----------------------------------------------------------------------
    // Pairing
    // -----------------------------------------------------------------------

    /**
     * Blocks until the device is paired (user claims it in the dashboard).
     * Shows pairing code on Serial. Polls every HUBEX_PAIRING_POLL_INTERVAL_MS.
     * Returns when token is stored in NVS.
     */
    void ensurePaired() {
        if (isPaired()) return;

        Serial.printf("[HUBEX] Starting pairing for device UID: %s\n", _deviceUid.c_str());

        while (!isPaired()) {
            HubexResult res = _pairingHello();
            if (!res.ok) {
                Serial.printf("[HUBEX] Pairing hello failed (%d): %s — retrying in 10s\n",
                              res.httpCode, res.error.c_str());
                delay(10000);
                continue;
            }
            // If hello returns a token (device was pre-claimed), store it
            if (_deviceToken.length() > 0) break;

            delay(HUBEX_PAIRING_POLL_INTERVAL_MS);
        }
        Serial.printf("[HUBEX] Paired! device_id=%d\n", _deviceId);
    }

    // -----------------------------------------------------------------------
    // Heartbeat
    // -----------------------------------------------------------------------

    /**
     * POST /api/v1/edge/heartbeat — updates last_seen_at on the server.
     * Call this regularly (e.g. every 30s) to keep the device "online".
     */
    HubexResult heartbeat() {
        if (!isPaired()) return {false, -1, "not paired"};

        JsonDocument doc;
        doc["firmware_version"] = _fwVersion;
        String body;
        serializeJson(doc, body);

        return _post("/api/v1/edge/heartbeat", body, true);
    }

    // -----------------------------------------------------------------------
    // Edge Config
    // -----------------------------------------------------------------------

    /**
     * GET /api/v1/edge/config — fetches effective variables and pending tasks.
     * @param outVars  JsonDocument to populate with {key: value} pairs
     * @param outTasks JsonDocument to populate with task array
     */
    HubexResult getConfig(JsonDocument& outVars, JsonDocument& outTasks) {
        if (!isPaired()) return {false, -1, "not paired"};

        String body;
        int code = _get("/api/v1/edge/config", body, true);
        if (code < 200 || code >= 300) {
            return {false, code, body};
        }

        JsonDocument resp;
        auto err = deserializeJson(resp, body);
        if (err) return {false, -1, String("JSON parse error: ") + err.c_str()};

        outVars.set(resp["variables"]);
        outTasks.set(resp["tasks"]);
        return {true, code, ""};
    }

    /**
     * Convenience: get a single variable value as String.
     * Returns defaultValue if not found.
     */
    String getVar(const char* key, const char* defaultValue = "") {
        JsonDocument vars, tasks;
        if (!getConfig(vars, tasks)) return defaultValue;
        if (vars[key].isNull()) return defaultValue;
        return vars[key].as<String>();
    }

    // -----------------------------------------------------------------------
    // Telemetry
    // -----------------------------------------------------------------------

    /**
     * POST /api/v1/telemetry — push sensor readings.
     * @param fields  Brace-initializer list of {key, float_value} pairs.
     *
     * Example:
     *   hubex.pushTelemetry({{"temp", 23.5f}, {"humidity", 60.0f}});
     */
    HubexResult pushTelemetry(std::initializer_list<HubexField> fields) {
        if (!isPaired()) return {false, -1, "not paired"};

        JsonDocument doc;
        JsonObject payload = doc["payload"].to<JsonObject>();
        for (auto& f : fields) {
            payload[f.first] = f.second;
        }
        doc["device_uid"] = _deviceUid;

        String body;
        serializeJson(doc, body);
        return _post("/api/v1/telemetry", body, true);
    }

    /**
     * Overload: push a pre-built JsonDocument as telemetry payload.
     */
    HubexResult pushTelemetry(JsonDocument& payloadDoc) {
        if (!isPaired()) return {false, -1, "not paired"};

        JsonDocument doc;
        doc["payload"]    = payloadDoc;
        doc["device_uid"] = _deviceUid;

        String body;
        serializeJson(doc, body);
        return _post("/api/v1/telemetry", body, true);
    }

    // -----------------------------------------------------------------------
    // OTA
    // -----------------------------------------------------------------------

    /**
     * GET /api/v1/ota/check — checks if an OTA update is available for this device.
     * @param outInfo  Populated with OTA details if available.
     */
    HubexResult checkOtaInfo(HubexOtaInfo& outInfo) {
        if (!isPaired()) return {false, -1, "not paired"};
        outInfo.available = false;

        String body;
        int code = _get("/api/v1/ota/check", body, true);
        if (code == 204) return {true, 204, ""};  // no update
        if (code < 200 || code >= 300) return {false, code, body};

        JsonDocument resp;
        auto err = deserializeJson(resp, body);
        if (err) return {false, -1, String("JSON parse error: ") + err.c_str()};

        outInfo.available  = resp["update_available"] | false;
        outInfo.rolloutId  = resp["rollout_id"]       | -1;
        outInfo.version    = resp["version"].as<String>();
        outInfo.binaryUrl  = resp["binary_url"].as<String>();
        outInfo.checksum   = resp["checksum_sha256"].as<String>();
        return {true, code, ""};
    }

    /**
     * Full OTA: check + download + apply firmware update.
     * If an update is available, the device will restart after successful flash.
     * @return false if no update or error; does not return on success (ESP.restart)
     */
    HubexResult checkOta() {
        HubexOtaInfo info;
        HubexResult res = checkOtaInfo(info);
        if (!res || !info.available) return res;

        Serial.printf("[HUBEX] OTA update available: v%s — starting download\n",
                      info.version.c_str());

        // Acknowledge to server
        _otaAck(info.rolloutId, "downloading");

        // Perform OTA update via HTTPClient stream
        HTTPClient http;
        WiFiClientSecure* secureClient = nullptr;

        if (info.binaryUrl.startsWith("https")) {
            secureClient = new WiFiClientSecure();
            if (_skipTls) secureClient->setInsecure();
            http.begin(*secureClient, info.binaryUrl);
        } else {
            http.begin(info.binaryUrl);
        }
        http.setTimeout(60000);

        int code = http.GET();
        if (code != 200) {
            http.end();
            if (secureClient) delete secureClient;
            _otaAck(info.rolloutId, "failed");
            return {false, code, "OTA download failed"};
        }

        int totalBytes = http.getSize();
        WiFiClient* stream = http.getStreamPtr();

        if (!Update.begin(totalBytes > 0 ? totalBytes : UPDATE_SIZE_UNKNOWN)) {
            http.end();
            if (secureClient) delete secureClient;
            _otaAck(info.rolloutId, "failed");
            return {false, -1, "Update.begin failed"};
        }

        size_t written = Update.writeStream(*stream);
        http.end();
        if (secureClient) delete secureClient;

        if (!Update.end() || !Update.isFinished()) {
            _otaAck(info.rolloutId, "failed");
            return {false, -1, "Update.end failed"};
        }

        Serial.println("[HUBEX] OTA complete — restarting");
        _otaAck(info.rolloutId, "done");
        delay(500);
        ESP.restart();

        return {true, 200, ""};  // unreachable
    }

    // -----------------------------------------------------------------------
    // Accessors
    // -----------------------------------------------------------------------

    const String& deviceToken() const { return _deviceToken; }
    int           deviceId()    const { return _deviceId; }
    const String& deviceUid()   const { return _deviceUid; }

private:
    String     _serverUrl;
    String     _deviceUid;
    String     _fwVersion  = "0.0.0";
    String     _deviceToken;
    int        _deviceId   = -1;
    bool       _skipTls    = false;
    Preferences _prefs;

    // -----------------------------------------------------------------------
    // Internal — Pairing Hello
    // -----------------------------------------------------------------------

    HubexResult _pairingHello() {
        JsonDocument doc;
        doc["device_uid"]      = _deviceUid;
        doc["firmware_version"] = _fwVersion;

        String body;
        serializeJson(doc, body);

        String respBody;
        int code = _postRaw("/api/v1/devices/pairing/hello", body, "", respBody);

        if (code < 200 || code >= 300) {
            return {false, code, respBody};
        }

        JsonDocument resp;
        auto err = deserializeJson(resp, respBody);
        if (err) return {false, -1, String("JSON parse: ") + err.c_str()};

        bool claimed      = resp["claimed"]       | false;
        bool pairingActive = resp["pairing_active"] | false;

        if (claimed && resp["device_token"].is<const char*>()) {
            _storeToken(resp["device_token"].as<String>(),
                        resp["device_id"].as<int>());
        } else if (pairingActive) {
            const char* code_str = resp["pairing_code"];
            Serial.printf("[HUBEX] Waiting for claim — pairing code: %s\n",
                          code_str ? code_str : "?");
        } else {
            Serial.println("[HUBEX] Pairing hello sent — waiting for activation");
        }

        return {true, code, ""};
    }

    void _storeToken(const String& token, int deviceId) {
        _deviceToken = token;
        _deviceId    = deviceId;
        _prefs.putString("device_token", token);
        _prefs.putInt("device_id", deviceId);
        Serial.printf("[HUBEX] Token stored for device_id=%d\n", deviceId);
    }

    // -----------------------------------------------------------------------
    // Internal — HTTP helpers
    // -----------------------------------------------------------------------

    HubexResult _post(const String& path, const String& body, bool auth) {
        String respBody;
        int code = _postRaw(path, body, auth ? _deviceToken : "", respBody);
        if (code >= 200 && code < 300) return {true, code, ""};
        return {false, code, respBody};
    }

    int _postRaw(const String& path, const String& body,
                 const String& token, String& outBody) {
        HTTPClient http;
        WiFiClientSecure* sec = nullptr;
        String url = _serverUrl + path;

        if (url.startsWith("https")) {
            sec = new WiFiClientSecure();
            if (_skipTls) sec->setInsecure();
            http.begin(*sec, url);
        } else {
            http.begin(url);
        }

        http.setTimeout(HUBEX_HTTP_TIMEOUT_MS);
        http.addHeader("Content-Type", "application/json");
        if (token.length() > 0) {
            http.addHeader("X-Device-Token", token);
        }

        int code = http.POST(body);
        outBody  = (code > 0) ? http.getString() : "";
        http.end();
        if (sec) delete sec;
        return code;
    }

    int _get(const String& path, String& outBody, bool auth) {
        HTTPClient http;
        WiFiClientSecure* sec = nullptr;
        String url = _serverUrl + path;

        if (url.startsWith("https")) {
            sec = new WiFiClientSecure();
            if (_skipTls) sec->setInsecure();
            http.begin(*sec, url);
        } else {
            http.begin(url);
        }

        http.setTimeout(HUBEX_HTTP_TIMEOUT_MS);
        if (auth && _deviceToken.length() > 0) {
            http.addHeader("X-Device-Token", _deviceToken);
        }

        int code = http.GET();
        outBody  = (code > 0) ? http.getString() : "";
        http.end();
        if (sec) delete sec;
        return code;
    }

    HubexResult _otaAck(int rolloutId, const char* status) {
        JsonDocument doc;
        doc["status"] = status;
        String body;
        serializeJson(doc, body);
        return _post("/api/v1/ota/status/" + String(rolloutId) + "/ack", body, true);
    }
};

#endif // HUBEX_CLIENT_H
