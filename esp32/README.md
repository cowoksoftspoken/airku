# AirKu ESP32 Firmware

Folder ini berisi kode C++ *Production-Grade* untuk di-*flash* ke mikrokontroler ESP32 Anda. 
Aplikasi Android AirKu mendukung dua arsitektur *deployment* firmware yang dapat disesuaikan dengan kebutuhan lapangan:

## 1. Mode Direct Local AP (`esp32_direct.ino`)
Gunakan mode ini untuk operasional lapangan yang sepenuhnya *offline* atau di area tanpa akses internet (seperti ruang tertutup/gudang yang susah sinyal).
- **Kelebihan**: Berjalan 100% lokal tanpa router atau internet. Sangat cepat, stabil, dan privasi terjamin.
- **Kekurangan**: Pemantauan hanya dapat dilakukan ketika *smartphone* berada dalam jangkauan sinyal ESP32.
- **Cara Kerja**: ESP32 secara otomatis memancarkan jaringan WiFi sendiri (SoftAP) bernama `AirKu_Sensor_Local`. Aplikasi Android Anda langsung terhubung ke WiFi ini dan menarik data JSON via HTTP GET ke alamat IP lokal ESP32.

## 2. Mode Cloudflare Edge (`esp32_cloudflare.ino`)
Gunakan mode ini untuk memantau sistem secara *real-time* dari mana saja di seluruh dunia.
- **Kelebihan**: Pemantauan jarak jauh tanpa batas geografis. Data disimpan secara permanen di basis data Cloudflare KV.
- **Kekurangan**: Bergantung pada ketersediaan koneksi internet dan router di lokasi alat.
- **Cara Kerja**: ESP32 bertindak sebagai klien WiFi, terhubung ke *router*, lalu mem-POST data telemetri JSON (non-blocking) ke alamat API Cloudflare Worker (contoh: `https://backend.dbgaming679.workers.dev/api/sensor`) setiap 1 menit.

## Persiapan Perangkat Keras Fisik
Sistem ini membutuhkan perangkat keras berikut untuk beroperasi sesuai *pipeline* AI:
1. **Papan Mikrokontroler**: ESP32 (mendukung resolusi ADC 12-bit).
2. **Sensor Kualitas Udara (Gas)**: MQ-135 terhubung ke **PIN ADC 34**. Pastikan telah memasang *load resistor* yang tepat untuk kalibrasi dasar. Firmware akan mengambil nilai *analogRead()* dan mengonversinya ke PPM serta mengestimasi metrik AQI, PM2.5, PM10, CO2, dan VOC.
3. **Sensor Suhu/Kelembapan**: DHT22 terhubung ke **PIN Digital 4**. Firmware telah dilengkapi dengan *failsafe* yang memancarkan nilai *default* (25 Celcius, 60% Humidity) jika sensor ini mengalami disfungsi di tengah jalan, agar *Machine Learning* tidak mengalami *crash*.

## Panduan Instalasi (Flashing)
1. Buka aplikasi **Arduino IDE**.
2. Buka menu **File > Preferences**, tambahkan URL berikut ke kolom *Additional Board Manager URLs*: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3. Masuk ke **Tools > Board > Boards Manager**, cari `esp32` dan instal versi terbarunya.
4. Masuk ke **Sketch > Include Library > Manage Libraries**, lalu cari dan instal:
   - `ArduinoJson` (oleh Benoit Blanchon)
   - `DHT sensor library` (oleh Adafruit)
   - `Adafruit Unified Sensor` (oleh Adafruit)
5. Buka `esp32_cloudflare.ino` (atau `esp32_direct.ino`). Jika menggunakan versi Cloudflare, ubah variabel `ssid` dan `password` sesuai kredensial WiFi gedung.
6. Hubungkan ESP32 ke komputer menggunakan kabel Micro-USB atau USB-C.
7. Pilih Board yang sesuai (misalnya: `DOIT ESP32 DEVKIT V1`) dan Port COM yang benar.
8. Tekan tombol **Upload (Tanda Panah Kanan)**.

## Catatan Produksi
*Firmware* ini telah disesuaikan ketat dengan tipe data (*strict typing*) yang dibutuhkan oleh antarmuka *Cloudflare Backend* dan *parser* Moshi di Android. Kesalahan pengiriman tipe data (*float* vs *int*) dari perangkat IoT dapat menyebabkan penolakan API. Jika Anda ingin menambah metrik sensor baru, pastikan untuk memperbarui deklarasi *interface* TypeScript di `index.ts` pada Cloudflare dan *data class* di aplikasi Android terlebih dahulu.
