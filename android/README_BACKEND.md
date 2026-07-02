# AirKu IoT Backend & ESP32 Integration (Production-Ready)

This repository contains the production-ready central backend code for **Cloudflare Workers** and the **ESP32 Arduino** source code to construct a complete, secure, on-device to cloud IoT environment.

---

## 1. Cloudflare Workers Backend (TypeScript + Hono)

This lightweight API handles telemetry registration from multiple ESP32 micro-controllers and provides a high-performance endpoint for the AirKu Android application. It utilizes **Cloudflare KV** for persistent cache storage and features an automatic in-memory fallback for instant, zero-config staging.

### Deploying to Cloudflare
1. Install Wrangler CLI: `npm install -g wrangler`
2. Authenticate: `wrangler login`
3. Initialize project: `wrangler init airku-backend`
4. Copy the following code into `src/index.ts` (or `src/index.js`):

```typescript
import { Hono } from 'hono'
import { cors } from 'hono/cors'

type Bindings = {
  AIRKU_KV?: KVNamespace
}

interface TelemetryPayload {
  room: string
  aqi: number
  temperature: number
  humidity: number
  pm25: number
  pm10: number
  co2: number
  voc: number
  espId?: string
  ip?: string
}

const app = new Hono<{ Bindings: Bindings }>()

// Enable CORS for the Android application and testing
app.use('*', cors())

// Simple memory-cache fallback if KV Namespace is not bound yet
const memoryCache = new Map<string, string>()

app.get('/', (c) => {
  return c.json({
    status: "online",
    service: "AirKu IoT Gateway",
    timestamp: Date.now()
  })
})

/**
 * GET /api/readings
 * Returns list of latest telemetry readings for all registered rooms.
 */
app.get('/api/readings', async (c) => {
  try {
    const list: TelemetryPayload[] = []
    
    if (c.env.AIRKU_KV) {
      // Fetch from Cloudflare KV Namespace
      const keys = await c.env.AIRKU_KV.list({ prefix: "room:" })
      for (const key of keys.keys) {
        const data = await c.env.AIRKU_KV.get(key.name)
        if (data) {
          list.push(JSON.parse(data))
        }
      }
    } else {
      // Fallback to in-memory store
      for (const value of memoryCache.values()) {
        list.push(JSON.parse(value))
      }
    }

    // Default mock data if no ESP32 has uploaded data yet
    if (list.length === 0) {
      return c.json([
        {
          room: "Ruang Kelas A (Simulasi)",
          aqi: 42,
          temperature: 24.5,
          humidity: 62,
          pm25: 12,
          pm10: 34,
          co2: 410,
          voc: 0.20,
          espId: "esp32_class_a",
          ip: "192.168.1.121",
          timestamp: Date.now()
        },
        {
          room: "Ruang Meeting Kantor (Simulasi)",
          aqi: 112,
          temperature: 23.8,
          humidity: 61,
          pm25: 42,
          pm10: 75,
          co2: 1150,
          voc: 0.62,
          espId: "esp32_meeting",
          ip: "192.168.1.144",
          timestamp: Date.now()
        }
      ])
    }

    return c.json(list)
  } catch (error: any) {
    return c.json({ error: "Failed to read database", message: error.message }, 500)
  }
})

/**
 * POST /api/telemetry
 * Receives real-time telemetry from an ESP32.
 * Handled with strict input validation.
 */
app.post('/api/telemetry', async (c) => {
  try {
    const body = await c.req.json<Partial<TelemetryPayload>>()
    
    // Strict Input Validation
    if (!body.room || body.aqi === undefined || body.temperature === undefined || body.humidity === undefined) {
      return c.json({ error: "Bad Request", message: "Missing required telemetry fields: room, aqi, temperature, humidity" }, 400)
    }

    const roomKey = `room:${body.room.trim().toLowerCase().replace(/\s+/g, '_')}`
    const record: TelemetryPayload & { timestamp: number } = {
      room: body.room.trim(),
      aqi: Number(body.aqi),
      temperature: Number(body.temperature),
      humidity: Number(body.humidity),
      pm25: Number(body.pm25 || 0),
      pm10: Number(body.pm10 || 0),
      co2: Number(body.co2 || 400),
      voc: Number(body.voc || 0.1),
      espId: body.espId || `esp32_${body.room.trim().toLowerCase().replace(/\s+/g, '_')}`,
      ip: body.ip || "192.168.1.100",
      timestamp: Date.now()
    }

    const valueStr = JSON.stringify(record)

    if (c.env.AIRKU_KV) {
      // Persist in Cloudflare KV with no expiration (or e.g. TTL of 7 days: { expirationTtl: 604800 })
      await c.env.AIRKU_KV.put(roomKey, valueStr)
    } else {
      // In-memory cache
      memoryCache.set(roomKey, valueStr)
    }

    return c.json({ success: true, message: `Telemetry updated for room: ${record.room}`, record })
  } catch (error: any) {
    return c.json({ error: "Internal Server Error", message: error.message }, 500)
  }
})

export default app
```

5. Deploy instantly using: `wrangler deploy`

---

## 2. ESP32 Arduino Client Code (C++)

This production-grade script connects the ESP32 to a local Wi-Fi, reads from sensor interfaces (simulated below, but easily mapped to DHT22/MQ-135/SGP30 hardware pins), and transmits telemetry over HTTP.

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// WiFi Configuration
const char* ssid = "NAMA_WIFI_ANDA";
const char* password = "PASSWORD_WIFI_ANDA";

// Gateway / Backend Configuration
// Ganti dengan alamat backend Cloudflare Worker atau IP server lokal Anda
const char* serverUrl = "https://airku-backend.nama-anda.workers.dev/api/telemetry";

// Room Labeling (Tentukan identitas unik untuk unit ESP32 ini)
const char* roomLabel = "Ruang Kelas B"; 

// Telemetry transmit interval (e.g., 10 seconds)
const unsigned long postInterval = 10000;
unsigned long lastPostTime = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Initialize WiFi Connection
  Serial.println();
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("Wi-Fi connected successfully!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  unsigned long currentTime = millis();
  
  if (currentTime - lastPostTime >= postInterval) {
    lastPostTime = currentTime;

    if (WiFi.status() == WL_CONNECTED) {
      sendSensorData();
    } else {
      Serial.println("WiFi Disconnected. Reconnecting...");
      WiFi.disconnect();
      WiFi.begin(ssid, password);
    }
  }
}

void sendSensorData() {
  // 1. Read Sensor Values (Replace this logic with real DHT22/SGP30/MQ-135 drivers)
  int mockAqi = random(40, 125);
  double mockTemp = 24.5 + (random(-15, 15) / 10.0);
  int mockHumidity = random(55, 75);
  int mockPm25 = random(10, 50);
  int mockPm10 = random(20, 80);
  int mockCo2 = random(400, 1100);
  double mockVoc = 0.15 + (random(-10, 20) / 100.0);

  // 2. Build JSON Document
  StaticJsonDocument<300> doc;
  doc["room"] = roomLabel;
  doc["aqi"] = mockAqi;
  doc["temperature"] = mockTemp;
  doc["humidity"] = mockHumidity;
  doc["pm25"] = mockPm25;
  doc["pm10"] = mockPm10;
  doc["co2"] = mockCo2;
  doc["voc"] = mockVoc;
  doc["espId"] = WiFi.macAddress(); // Unique MAC Address of ESP32
  doc["ip"] = WiFi.localIP().toString(); // Local IP address of ESP32

  String jsonString;
  serializeJson(doc, jsonString);

  // 3. Perform HTTP Post Request
  HTTPClient http;
  Serial.print("Sending telemetry to: ");
  Serial.println(serverUrl);

  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");

  int httpResponseCode = http.POST(jsonString);

  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.print("HTTP Success! Response Code: ");
    Serial.println(httpResponseCode);
    Serial.println(response);
  } else {
    Serial.print("HTTP Error Occurred: ");
    Serial.println(httpResponseCode);
  }

  http.end();
}
```

---

## 3. Direct Local Server Configuration (Option B: Fully Local)

If you prefer to connect **100% offline without internet**, you can flash an HTTP Web Server directly onto the ESP32 using `WebServer.h`.
- The Android App setting should be toggled to **"Direct IP Mode"**.
- Specify the ESP32 Local IP address (e.g., `192.168.1.105`).
- The ESP32 must expose an endpoint `GET /api/reading` returning a single telemetry JSON.

```cpp
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>

WebServer server(80);

void handleReading() {
  StaticJsonDocument<300> doc;
  doc["room"] = "Kamar Utama";
  doc["aqi"] = 32;
  doc["temperature"] = 23.4;
  doc["humidity"] = 58;
  doc["pm25"] = 8;
  doc["pm10"] = 22;
  doc["co2"] = 430;
  doc["voc"] = 0.09;

  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

void setup() {
  WiFi.begin("Your_SSID", "Your_PASS");
  server.on("/api/reading", handleReading);
  server.begin();
}

void loop() {
  server.handleClient();
}
```
