# Real-World Scenario Testing Report

## Scenario A (Kondisi Bersih - Siang Hari)

Timeline Pengujian:
```
Min 05 | Sensor: 887 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.02083 (Anomali: 0.0) | Prediksi 1j: 22.2 AQI | Rekomendasi: Aman Beraktivitas Luar (safe_outdoor)
Min 10 | Sensor: 915 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.02253 (Anomali: 1.0) | Prediksi 1j: 24.4 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
Min 20 | Sensor: 906 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.02327 (Anomali: 1.0) | Prediksi 1j: 29.8 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
Min 30 | Sensor: 904 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.02501 (Anomali: 1.0) | Prediksi 1j: 38.3 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
Min 45 | Sensor: 901 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.02584 (Anomali: 1.0) | Prediksi 1j: 56.5 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
Min 59 | Sensor: 887 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.02767 (Anomali: 1.0) | Prediksi 1j: 77.3 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
```

## Scenario B (Aktivitas Memasak Dapur)

Timeline Pengujian:
```
Min 05 | Sensor: 1499 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.01994 (Anomali: 0.0) | Prediksi 1j: 43.9 AQI | Rekomendasi: Aman Beraktivitas Luar (safe_outdoor)
Min 10 | Sensor: 1498 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.01993 (Anomali: 0.0) | Prediksi 1j: 35.6 AQI | Rekomendasi: Aman Beraktivitas Luar (safe_outdoor)
Min 20 | Sensor: 1811 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.02412 (Anomali: 1.0) | Prediksi 1j: 22.0 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
Min 21 | Sensor: 1801 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.02411 (Anomali: 1.0) | Prediksi 1j: 19.6 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
Min 30 | Sensor: 1800 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.02425 (Anomali: 1.0) | Prediksi 1j: 5.3 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
Min 45 | Sensor: 1508 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.02053 (Anomali: 0.0) | Prediksi 1j: 5.6 AQI | Rekomendasi: Aman Beraktivitas Luar (safe_outdoor)
Min 59 | Sensor: 1500 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.02077 (Anomali: 0.0) | Prediksi 1j: 4.6 AQI | Rekomendasi: Aman Beraktivitas Luar (safe_outdoor)
```

## Scenario C (Kebocoran Gas Mendadak - Anomali)

Timeline Pengujian:
```
Min 05 | Sensor: 922 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.02064 (Anomali: 0.0) | Prediksi 1j: 42.9 AQI | Rekomendasi: Aman Beraktivitas Luar (safe_outdoor)
Min 10 | Sensor: 906 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.02053 (Anomali: 0.0) | Prediksi 1j: 42.8 AQI | Rekomendasi: Udara Optimal (all_clear)
Min 16 | Sensor: 2892 raw (1146 ppm) | Klasifikasi: Sedang (Class 1) | Error AE: 0.06163 (Anomali: 1.0) | Prediksi 1j: 55.1 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
Min 20 | Sensor: 2892 raw (1145 ppm) | Klasifikasi: Sedang (Class 1) | Error AE: 0.06149 (Anomali: 1.0) | Prediksi 1j: 65.4 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
Min 30 | Sensor: 890 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.01863 (Anomali: 0.0) | Prediksi 1j: 41.5 AQI | Rekomendasi: Udara Optimal (all_clear)
Min 45 | Sensor: 896 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.01777 (Anomali: 0.0) | Prediksi 1j: 41.9 AQI | Rekomendasi: Udara Optimal (all_clear)
Min 59 | Sensor: 900 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.01668 (Anomali: 0.0) | Prediksi 1j: 41.5 AQI | Rekomendasi: Udara Optimal (all_clear)
```

## Scenario D (Polusi Udara Berat & Panas)

Timeline Pengujian:
```
Min 05 | Sensor: 1958 raw (360 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.01159 (Anomali: 0.0) | Prediksi 1j: 11.8 AQI | Rekomendasi: Kurangi Memasak (reduce_cooking)
Min 10 | Sensor: 1990 raw (374 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.01098 (Anomali: 0.0) | Prediksi 1j: 14.2 AQI | Rekomendasi: Kurangi Memasak (reduce_cooking)
Min 20 | Sensor: 1995 raw (376 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.00980 (Anomali: 0.0) | Prediksi 1j: 18.2 AQI | Rekomendasi: Aman Beraktivitas Luar (safe_outdoor)
Min 30 | Sensor: 1978 raw (369 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.00899 (Anomali: 0.0) | Prediksi 1j: 22.4 AQI | Rekomendasi: Aman Beraktivitas Luar (safe_outdoor)
Min 45 | Sensor: 1978 raw (369 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.01003 (Anomali: 0.0) | Prediksi 1j: 27.9 AQI | Rekomendasi: Buka Jendela (open_window)
Min 59 | Sensor: 2001 raw (379 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.01266 (Anomali: 0.0) | Prediksi 1j: 33.8 AQI | Rekomendasi: Buka Jendela (open_window)
```

## Scenario E (Udara Membaik Setelah Buka Jendela)

Timeline Pengujian:
```
Min 05 | Sensor: 905 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.03682 (Anomali: 1.0) | Prediksi 1j: 214.7 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
Min 10 | Sensor: 890 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.03769 (Anomali: 1.0) | Prediksi 1j: 212.1 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
Min 18 | Sensor: 1350 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.03896 (Anomali: 1.0) | Prediksi 1j: 212.0 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
Min 20 | Sensor: 1167 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.03782 (Anomali: 1.0) | Prediksi 1j: 204.6 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
Min 30 | Sensor: 728 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.04155 (Anomali: 1.0) | Prediksi 1j: 166.4 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
Min 45 | Sensor: 621 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.04108 (Anomali: 1.0) | Prediksi 1j: 118.9 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
Min 59 | Sensor: 599 raw (350 ppm) | Klasifikasi: Baik (Class 0) | Error AE: 0.04029 (Anomali: 1.0) | Prediksi 1j: 80.7 AQI | Rekomendasi: Nyalakan Purifier (use_air_purifier)
```
