# AirKu ESP32 Firmware

Folder ini berisi kode C++ untuk di-*flash* ke mikrokontroler ESP32 Anda. 
Aplikasi Android AirKu mendukung dua arsitektur berbeda:

## 1. Mode Direct IP (`esp32_direct.ino`)
Gunakan kode ini jika Anda ingin aplikasi Android berkomunikasi **langsung** ke alamat IP ESP32 di jaringan WiFi lokal yang sama. 
- **Kelebihan**: Sangat cepat, tidak butuh internet (sepenuhnya offline/lokal), privasi data 100% aman.
- **Kekurangan**: Anda tidak bisa memantau polusi rumah Anda ketika sedang berada di luar rumah (jaringan berbeda).
- **Cara Kerja**: ESP32 bertindak sebagai Web Server mikro di port 80. Aplikasi Android mengirim HTTP GET `http://<IP_ESP>/api/reading` setiap kali menarik data.

## 2. Mode Cloudflare Backend (`esp32_cloudflare.ino`)
Gunakan kode ini jika Anda telah membuat API Gateway (Cloudflare Worker) dan ingin ESP32 menyetor datanya ke Cloudflare.
- **Kelebihan**: Anda bisa memantau kondisi rumah dari mana saja di seluruh dunia asalkan ada internet. Aplikasi akan mengambil data dari Cloudflare.
- **Kekurangan**: Memerlukan koneksi internet yang stabil di rumah Anda dan di ponsel Anda.
- **Cara Kerja**: ESP32 bertindak sebagai HTTP Client, melakukan HTTP POST berisikan JSON ke URL Worker Anda (misal: `https://backend.dbgaming679.workers.dev/api/sensor`) setiap 5 menit sekali.

## Persiapan Perangkat Keras
1. **Papan Mikrokontroler**: ESP32 (NodeMCU, Wemos, dll).
2. **Sensor Suhu/Kelembaban**: DHT22 atau DHT11 (terhubung ke PIN Digital 4).
3. **Sensor Kualitas Udara**: (Contoh: MQ135 untuk kualitas udara umum). Saat ini kode `ino` masih mensimulasikan sebagian pembacaan metrik polusi (AQI, PM2.5, CO2, VOC) menggunakan fungsi `random()`. Anda wajib menggantinya dengan logika pembacaan *analog read* dari sensor MQ asli Anda jika sudah siap (menggunakan `analogRead(PIN)` dan pustaka kalibrasi MQ).

## Panduan Instalasi (Flashing)
1. Buka aplikasi **Arduino IDE**.
2. Masuk ke **File > Preferences**, tambahkan URL berikut ke *Additional Board Manager URLs*: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3. Masuk ke **Tools > Board > Boards Manager**, cari `esp32` dan instal versi terbarunya.
4. Masuk ke **Sketch > Include Library > Manage Libraries**, lalu cari dan instal:
   - `ArduinoJson` (oleh Benoit Blanchon)
   - `DHT sensor library` (oleh Adafruit)
   - `Adafruit Unified Sensor` (oleh Adafruit)
5. Ubah variabel `ssid` dan `password` di baris atas kode sesuai dengan WiFi rumah Anda.
6. Hubungkan ESP32 menggunakan kabel Micro-USB/USB-C ke komputer.
7. Pilih Board yang sesuai (misal: `DOIT ESP32 DEVKIT V1`) dan Port COM yang benar.
8. Tekan tombol **Upload (Tanda Panah Kanan)**.

## Catatan Produksi
Data metrik polutan (*dummy*) di *firmware* ini diletakkan pada variabel global (seperti `currentAqi`). Pastikan untuk mengganti *dummy* tersebut dengan hasil ekstraksi nilai voltase aktual dari sensor debu (Sharp/Winsen) atau gas (MQ-135) yang sudah dikonversi ke indeks standar!
