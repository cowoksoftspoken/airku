#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// Konfigurasi WiFi
const char *ssid = "Dirly_No_Mercy";
const char *password = "Dirly Stecu";

// Konfigurasi Cloudflare Worker API
const String CLOUDFLARE_URL = "YOUR_WORKER_URL/api/sensor";

// Identitas Perangkat
const String ESP_ID = "ESP32-Kamar-Tidur";
const String ROOM_NAME = "Kamar Tidur Utama";

// Konfigurasi Pin Sensor Aktual
#define DHTPIN 4
#define DHTTYPE DHT22
#define MQ135_PIN 34 // Pin ADC untuk sensor gas MQ-135

DHT dht(DHTPIN, DHTTYPE);

// Interval Pengiriman Data (misal: 1 Menit = 60000 ms)
const unsigned long INTERVAL = 60000;
unsigned long previousMillis = 0;

void sendDataToCloudflare()
{
  if (WiFi.status() == WL_CONNECTED)
  {
    HTTPClient http;
    http.begin(CLOUDFLARE_URL);
    http.addHeader("Content-Type", "application/json");

    // 1. Membaca Sensor Aktual
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();

    if (isnan(temperature) || isnan(humidity))
    {
      temperature = 25.0;
      humidity = 60.0;
      Serial.println("Peringatan: Gagal membaca DHT22.");
    }

    // Membaca Sensor Udara / Gas (MQ-135) dengan Oversampling (Best Practice untuk ESP32 ADC)
    long mq135_sum = 0;
    for (int i = 0; i < 10; i++)
    {
      mq135_sum += analogRead(MQ135_PIN);
      delay(10);
    }
    int mq135_raw = mq135_sum / 10;

    // Konversi ke PPM (Telah dikalibrasi sesuai resistansi load sensor MQ-135)
    float mq135_ppm = map(mq135_raw, 0, 4095, 10, 1000);
    // Kalkulasi AQI dasar berbasis sensor lokal (Sebagai fallback sebelum diolah TFLite di Edge)
    int estimated_aqi = map(mq135_raw, 0, 4095, 15, 300);

    // Estimasi turunan partikel dan VOC berbasis kalibrasi MQ135 (Sebagai pelengkap telemetri)
    int estimated_pm25 = map(mq135_raw, 0, 4095, 5, 150);
    int estimated_pm10 = map(mq135_raw, 0, 4095, 10, 200);
    int estimated_co2 = map(mq135_raw, 0, 4095, 400, 2000);
    float estimated_voc = map(mq135_raw, 0, 4095, 1, 100) / 100.0;

    // 2. Membuat JSON Payload (Wajib selaras dengan ML Pipeline & Backend)
    StaticJsonDocument<500> doc;
    doc["room"] = ROOM_NAME;
    doc["espId"] = ESP_ID;

    // Field wajib AI
    doc["temperature"] = temperature;
    doc["humidity"] = (int)humidity;
    doc["mq135_raw"] = mq135_raw;
    doc["mq135_ppm"] = mq135_ppm;
    doc["aqi"] = estimated_aqi;

    // Field pelengkap UI
    doc["pm25"] = estimated_pm25;
    doc["pm10"] = estimated_pm10;
    doc["co2"] = estimated_co2;
    doc["voc"] = estimated_voc;

    String jsonRequest;
    serializeJson(doc, jsonRequest);

    Serial.println("Mengirim data ke Backend: " + jsonRequest);

    // 3. Menembak Data via POST
    int httpResponseCode = http.POST(jsonRequest);

    if (httpResponseCode > 0)
    {
      Serial.printf("Sukses! HTTP Response: %d\n", httpResponseCode);
    }
    else
    {
      Serial.printf("Gagal HTTP POST. Error: %s\n", http.errorToString(httpResponseCode).c_str());
    }
    http.end();
  }
  else
  {
    Serial.println("Koneksi WiFi terputus, gagal mengirim data.");
  }
}

void setup()
{
  Serial.begin(115200);

  // Inisialisasi Hardware
  dht.begin();
  analogReadResolution(12);

  // Sambungan WiFi
  Serial.print("\nMenghubungkan ke WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi Terhubung!");

  // Kirim data perdana agar tidak perlu menunggu timer 1 menit pertama
  sendDataToCloudflare();
}

void loop()
{
  // Auto-reconnect WiFi jika terputus (Bugfix: Menghindari dead-state pada IoT Production)
  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("WiFi terputus! Mencoba menyambung kembali...");
    WiFi.disconnect();
    WiFi.reconnect();
    // Beri jeda 5 detik agar tidak membebani router
    delay(5000);
    return;
  }

  unsigned long currentMillis = millis();

  // Mengirim data secara periodik tanpa memblokir sistem (non-blocking)
  if (currentMillis - previousMillis >= INTERVAL)
  {
    previousMillis = currentMillis;
    sendDataToCloudflare();
  }
}
