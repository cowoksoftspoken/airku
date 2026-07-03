#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <DHT.h>

// Konfigurasi WiFi
const char* ssid = "NAMA_WIFI_ANDA";
const char* password = "PASSWORD_WIFI_ANDA";

// Identitas Perangkat
const String ESP_ID = "ESP32-Ruang-Tamu";
const String ROOM_NAME = "Ruang Tamu";

// Konfigurasi Pin Sensor Aktual
#define DHTPIN 4
#define DHTTYPE DHT22
#define MQ135_PIN 34 // Pin ADC untuk sensor gas MQ-135 (Mendukung resolusi 12-bit 0-4095)

DHT dht(DHTPIN, DHTTYPE);
WebServer server(80);

void handleGetReading() {
  // 1. Membaca Sensor Suhu & Kelembaban (DHT22)
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  // Fallback jika kabel lepas/sensor rusak agar ML tidak error (NaN)
  if (isnan(temperature) || isnan(humidity)) {
    temperature = 25.0;
    humidity = 60.0;
    Serial.println("Peringatan: Gagal membaca DHT22, menggunakan nilai default.");
  }

  // 2. Membaca Sensor Udara / Gas (MQ-135)
  int mq135_raw = analogRead(MQ135_PIN);
  
  // Konversi kasar ke PPM (Pastikan dikalibrasi di dunia nyata dengan load resistor)
  // Untuk demo lomba: Kita petakan secara linier (Nilai asli MQ butuh kurva logaritmik)
  float mq135_ppm = map(mq135_raw, 0, 4095, 10, 1000); 

  // Kalkulasi AQI dasar berbasis sensor lokal (Sebelum diolah TFLite di Android)
  int estimated_aqi = map(mq135_raw, 0, 4095, 15, 300);

  // 3. Menyusun Data JSON Sesuai dengan Format Pipeline ML AirKu
  StaticJsonDocument<500> doc;
  
  doc["room"] = ROOM_NAME;
  doc["espId"] = ESP_ID;
  doc["ip"] = WiFi.localIP().toString();
  doc["timestamp"] = millis();

  // Field krusial untuk fitur AI
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  doc["mq135_raw"] = mq135_raw;
  doc["mq135_ppm"] = mq135_ppm;
  doc["aqi"] = estimated_aqi; 

  String jsonResponse;
  serializeJson(doc, jsonResponse);

  // Mengirim ke Klien (Android App)
  server.send(200, "application/json", jsonResponse);
  Serial.println("Data dikirim: " + jsonResponse);
}

void setup() {
  Serial.begin(115200);
  
  // Inisialisasi Sensor
  dht.begin();
  analogReadResolution(12); // ESP32 ADC resolusi tinggi (0 - 4095)

  // Koneksi WiFi
  Serial.print("\nMenghubungkan ke WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi Terhubung!");
  Serial.print("IP Address ESP32: ");
  Serial.println(WiFi.localIP());

  // Rute API untuk diambil datanya oleh Aplikasi Android
  server.on("/api/reading", HTTP_GET, handleGetReading);
  
  // Menangani masalah CORS untuk keamanan jaringan lokal
  server.onNotFound([]() {
    if (server.method() == HTTP_OPTIONS) {
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.sendHeader("Access-Control-Allow-Headers", "*");
      server.send(204);
    } else {
      server.send(404, "text/plain", "Endpoint API tidak valid.");
    }
  });

  server.begin();
  Serial.println("HTTP Server siap!");
}

void loop() {
  server.handleClient();
}
