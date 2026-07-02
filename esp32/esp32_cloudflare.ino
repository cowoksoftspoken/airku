#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// Konfigurasi WiFi
const char* ssid = "NAMA_WIFI_ANDA";
const char* password = "PASSWORD_WIFI_ANDA";

// Konfigurasi Cloudflare Worker API
// Ubah "backend.dbgaming679.workers.dev" sesuai dengan alamat URL Cloudflare Worker Anda!
const String CLOUDFLARE_URL = "https://backend.dbgaming679.workers.dev/api/sensor";

// Identitas Perangkat
const String ESP_ID = "ESP32-Kamar-Tidur";
const String ROOM_NAME = "Kamar Tidur Utama";

// Konfigurasi Sensor DHT22
#define DHTPIN 4
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

// Interval Pengiriman Data (5 Menit = 300000 ms)
const unsigned long INTERVAL = 300000;
unsigned long previousMillis = 0;

// Variabel Sensor Dummy (Jika sensor MQ tidak terpasang)
int currentAqi = 45;
int currentPm25 = 15;
int currentPm10 = 25;
int currentCo2 = 410;
float currentVoc = 0.05;

void sendDataToCloudflare() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(CLOUDFLARE_URL);
    http.addHeader("Content-Type", "application/json");

    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();

    if (isnan(temperature) || isnan(humidity)) {
      temperature = 22.0;
      humidity = 55.0;
    }

    StaticJsonDocument<500> doc;
    doc["room"] = ROOM_NAME;
    doc["espId"] = ESP_ID;
    
    // Cloudflare biasanya memproduksi timestampnya sendiri, 
    // tetapi kita bisa menyuplai metrik sensor:
    doc["aqi"] = currentAqi;
    doc["temperature"] = temperature;
    doc["humidity"] = (int)humidity;
    doc["pm25"] = currentPm25;
    doc["pm10"] = currentPm10;
    doc["co2"] = currentCo2;
    doc["voc"] = currentVoc;

    String jsonRequest;
    serializeJson(doc, jsonRequest);

    Serial.println("Mengirim data ke Cloudflare...");
    Serial.println(jsonRequest);

    int httpResponseCode = http.POST(jsonRequest);
    
    if (httpResponseCode > 0) {
      Serial.print("Sukses, HTTP Response code: ");
      Serial.println(httpResponseCode);
      String response = http.getString();
      Serial.println(response);
    } else {
      Serial.print("Error saat POST: ");
      Serial.println(httpResponseCode);
      Serial.println(http.errorToString(httpResponseCode).c_str());
    }
    http.end();

    // Simulasi fluktuasi
    currentAqi = random(30, 70);
    currentCo2 = random(400, 480);
  } else {
    Serial.println("WiFi tidak terhubung, gagal mengirim data.");
  }
}

void setup() {
  Serial.begin(115200);
  dht.begin();

  Serial.println("Menghubungkan ke WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi Terhubung!");
  
  // Kirim data pertama kali saat boot
  sendDataToCloudflare();
}

void loop() {
  unsigned long currentMillis = millis();
  
  // Timer non-blocking untuk mengirim data secara berkala
  if (currentMillis - previousMillis >= INTERVAL) {
    previousMillis = currentMillis;
    sendDataToCloudflare();
  }
}
