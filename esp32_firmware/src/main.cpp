#include <Arduino.h>
#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <AsyncTCP.h>
#include <ArduinoJson.h>
#include <WiFiUdp.h>

// --- Configuration ---
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// --- Network Objects ---
AsyncWebServer server(80);
WiFiUDP udp;
const int UDP_PORT = 8266;
String espId;

// --- Sensor Variables (Simulated for this demo) ---
float currentAqi = 0.0;
float currentTemp = 0.0;
float currentHumidity = 0.0;
float currentPm25 = 0.0;
float currentPm10 = 0.0;
float currentCo2 = 0.0;
float currentVoc = 0.0;

unsigned long lastSensorUpdate = 0;
const unsigned long SENSOR_UPDATE_INTERVAL = 2000; // 2 seconds

// --- Function Prototypes ---
void setupWiFi();
void setupWebServer();
void handleUdpDiscovery();
void updateSensors();

void setup() {
    Serial.begin(115200);
    delay(1000);
    
    // Generate unique ID based on MAC Address
    uint8_t mac[6];
    WiFi.macAddress(mac);
    espId = "ESP32-" + String(mac[4], HEX) + String(mac[5], HEX);
    espId.toUpperCase();
    
    Serial.println("\n--- AirKu ESP32 Node ---");
    Serial.println("Device ID: " + espId);
    
    setupWiFi();
    setupWebServer();
    
    // Start UDP Listener for Discovery
    if (udp.begin(UDP_PORT)) {
        Serial.printf("UDP Discovery listening on port %d\n", UDP_PORT);
    }
}

void loop() {
    handleUdpDiscovery();
    updateSensors();
}

void setupWiFi() {
    Serial.print("Connecting to Wi-Fi");
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    
    unsigned long startAttemptTime = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < 10000) {
        Serial.print(".");
        delay(500);
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWi-Fi Connected!");
        Serial.print("IP Address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\nWi-Fi Connection Failed. Operating in fallback mode or resetting...");
    }
}

void setupWebServer() {
    // Enable CORS for frontend web apps if needed
    DefaultHeaders::Instance().addHeader("Access-Control-Allow-Origin", "*");
    
    server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
        request->send(200, "text/plain", "AirKu ESP32 Node (" + espId + ") is running.");
    });
    
    // Main data endpoint
    server.on("/data", HTTP_GET, [](AsyncWebServerRequest *request){
        JsonDocument doc;
        
        doc["espId"] = espId;
        doc["aqi"] = (int)currentAqi;
        doc["temperature"] = currentTemp;
        doc["humidity"] = (int)currentHumidity;
        doc["pm25"] = (int)currentPm25;
        doc["pm10"] = (int)currentPm10;
        doc["co2"] = (int)currentCo2;
        doc["voc"] = currentVoc;
        doc["room"] = espId; // Default room name is ID until changed by app
        
        String responseStr;
        serializeJson(doc, responseStr);
        request->send(200, "application/json", responseStr);
    });
    
    server.begin();
    Serial.println("Async Web Server started.");
}

void handleUdpDiscovery() {
    int packetSize = udp.parsePacket();
    if (packetSize) {
        char incomingPacket[255];
        int len = udp.read(incomingPacket, 255);
        if (len > 0) {
            incomingPacket[len] = '\0';
        }
        
        String request = String(incomingPacket);
        if (request == "AIRKU_DISCOVER") {
            // Reply with device ID
            String replyMsg = "AIRKU_REPLY:" + espId;
            udp.beginPacket(udp.remoteIP(), udp.remotePort());
            udp.print(replyMsg);
            udp.endPacket();
            
            Serial.printf("Received discovery ping from %s. Sent reply: %s\n", udp.remoteIP().toString().c_str(), replyMsg.c_str());
        }
    }
}

void updateSensors() {
    // Non-blocking delay for reading sensors
    if (millis() - lastSensorUpdate >= SENSOR_UPDATE_INTERVAL) {
        lastSensorUpdate = millis();
        
        // --- REAL HARDWARE INTEGRATION HERE ---
        // float t = dht.readTemperature();
        // float h = dht.readHumidity();
        // int co2_val = mhz19.getCO2();
        // ...
        
        // For production, if hardware is not attached yet, we simulate slightly fluctuating realistic data
        currentTemp = 25.0 + random(-10, 10) / 10.0;
        currentHumidity = 60.0 + random(-20, 20) / 10.0;
        currentAqi = 45.0 + random(-5, 5);
        currentPm25 = 12.0 + random(-3, 3);
        currentPm10 = 30.0 + random(-5, 5);
        currentCo2 = 410.0 + random(-10, 20);
        currentVoc = 0.2 + random(-5, 5) / 100.0;
    }
}
