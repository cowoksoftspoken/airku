#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <HardwareSerial.h>

// Konfigurasi WiFi
const char* ssid = "NAMA_WIFI_ANDA";
const char* password = "PASSWORD_WIFI_ANDA";

// Identitas Perangkat
const String ESP_ID = "ESP32-Ruang-Tamu";
const String ROOM_NAME = "Ruang Tamu";

// Konfigurasi Sensor DHT22
#define DHTPIN 4
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

// Konfigurasi WebServer
WebServer server(80);

// Variabel Sensor Dummy (Jika sensor MQ tidak terpasang)
int currentAqi = 45;
int currentPm25 = 15;
int currentPm10 = 25;
int currentCo2 = 410;
float currentVoc = 0.05;

void handleGetReading() {
  // Membaca suhu dan kelembaban aktual
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  // Jika DHT gagal, gunakan fallback
  if (isnan(temperature) || isnan(humidity)) {
    temperature = 25.0;
    humidity = 60.0;
  }

  // Membuat JSON Response
  StaticJsonDocument<500> doc;
  
  doc["room"] = ROOM_NAME;
  doc["espId"] = ESP_ID;
  doc["ip"] = WiFi.localIP().toString();
  doc["timestamp"] = millis(); // Gunakan RTC jika tersedia untuk epoch time

  doc["aqi"] = currentAqi;
  doc["temperature"] = temperature;
  doc["humidity"] = (int)humidity;
  doc["pm25"] = currentPm25;
  doc["pm10"] = currentPm10;
  doc["co2"] = currentCo2;
  doc["voc"] = currentVoc;

  String jsonResponse;
  serializeJson(doc, jsonResponse);

  server.send(200, "application/json", jsonResponse);
  
  // Simulasi fluktuasi sensor udara untuk pengujian
  currentAqi = random(30, 60);
  currentCo2 = random(400, 450);
}

void setup() {
  Serial.begin(115200);
  dht.begin();

  // Koneksi WiFi
  Serial.println("Menghubungkan ke WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi Terhubung!");
  Serial.print("Alamat IP ESP32: ");
  Serial.println(WiFi.localIP());

  // Rute API Server
  server.on("/api/reading", HTTP_GET, handleGetReading);
  
  // Handle CORS
  server.onNotFound([]() {
    if (server.method() == HTTP_OPTIONS) {
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.sendHeader("Access-Control-Allow-Headers", "*");
      server.send(204);
    } else {
      server.send(404, "text/plain", "Not Found");
    }
  });

  server.begin();
  Serial.println("HTTP Server Dimulai!");
}

void loop() {
  server.handleClient();
}
