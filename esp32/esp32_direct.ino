#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <DHT.h>

// Konfigurasi Hotspot Mandiri (Access Point - Tanpa Internet/Router)
const char* ssid = "AirKu_Sensor_Local";
const char* password = "password123"; // Minimal 8 karakter

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

  // Estimasi kasar partikel dan VOC berbasis MQ135 (Agar format JSON lengkap)
  int estimated_pm25 = map(mq135_raw, 0, 4095, 5, 150);
  int estimated_pm10 = map(mq135_raw, 0, 4095, 10, 200);
  int estimated_co2 = map(mq135_raw, 0, 4095, 400, 2000);
  float estimated_voc = map(mq135_raw, 0, 4095, 1, 100) / 100.0;

  // 3. Menyusun Data JSON Sesuai dengan Format Pipeline ML AirKu
  StaticJsonDocument<500> doc;
  
  doc["room"] = ROOM_NAME;
  doc["espId"] = ESP_ID;
  doc["ip"] = WiFi.softAPIP().toString();
  doc["timestamp"] = millis();

  // Field krusial untuk fitur AI
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  doc["mq135_raw"] = mq135_raw;
  doc["mq135_ppm"] = mq135_ppm;
  doc["aqi"] = estimated_aqi; 
  
  // Field pelengkap UI
  doc["pm25"] = estimated_pm25;
  doc["pm10"] = estimated_pm10;
  doc["co2"] = estimated_co2;
  doc["voc"] = estimated_voc;

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

  // Membuat Jaringan WiFi Mandiri (Access Point)
  Serial.print("\nMembangun Jaringan Hotspot (Tanpa Internet): ");
  Serial.println(ssid);
  
  // Memulai mode AP
  WiFi.softAP(ssid, password);
  
  Serial.println("Hotspot Aktif!");
  Serial.print("Sambungkan HP Anda ke WiFi ini, lalu akses IP: ");
  Serial.println(WiFi.softAPIP());

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
