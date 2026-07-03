# AirKu - Enterprise Air Quality Monitoring System

AirKu is a production-grade IoT and Machine Learning ecosystem engineered to monitor indoor and micro-environmental air quality. The system aggregates physical sensor telemetry, processes the data through a localized Edge AI pipeline, and delivers real-time analytical health directives to users via a native Android application.

This repository contains the complete infrastructure, including the multi-stage Machine Learning pipeline, Android application source code, ESP32 microcontroller firmware, and Cloudflare Edge Server configurations.

## System Architecture

The AirKu ecosystem operates across four robust tiers:

1. **Hardware Telemetry (ESP32 & Sensors):** Captures physical environmental data, specifically Temperature, Humidity, and Gas concentrations (via MQ-135 and DHT22 sensors). The firmware is engineered with fallback mechanisms to ensure continuous operation despite individual sensor failures.
2. **Edge AI Processing (TFLite):** Executes a sophisticated four-stage machine learning pipeline locally on the user's mobile device. This Edge Computing approach ensures zero latency and strict data privacy.
    * **Model 1 (Classifier):** Categorizes the Air Quality Index (AQI) into discrete health classifications.
    * **Model 2 (Autoencoder):** Detects abrupt sensor anomalies, hardware drift, or hazardous chemical spikes.
    * **Model 3 (LSTM Predictor):** Forecasts air quality trends using temporal sequential data.
    * **Model 4 (Recommender):** Synthesizes the outputs of the previous models to provide actionable health directives.
3. **Android Client:** Built with native Kotlin and Jetpack Compose. It features real-time telemetry dashboards, historical data visualization, and localized background monitoring.
4. **Cloudflare Gateway (Optional):** A serverless edge backend for routing multiple ESP32 payloads securely across wide-area networks.

## Prerequisites

To build and deploy the components of this project, ensure the following environments are configured:

* **Machine Learning Pipeline:** Python 3.9+, PyTorch, TensorFlow, scikit-learn, pandas, numpy, imbalanced-learn.
* **Android Application:** Android Studio, Java Development Kit (JDK) 11 or 17, Android SDK API Level 24+.
* **ESP32 Firmware:** Arduino IDE (with ESP32 board manager) or PlatformIO.

## Machine Learning Pipeline Execution

The AI architecture employs a Two-Stage Transfer Learning approach: Synthetic Pre-training followed by Real-World Fine-Tuning. This methodology mitigates cold-start problems and guarantees resilience against real-world sensor drift.

### 1. Data Generation and Preprocessing
Generate the foundational synthetic dataset mapping ideal physical-chemical relationships:
```bash
python data_generator.py
```
Preprocess the real-world dataset (e.g., from FigShare) to prepare for fine-tuning:
```bash
python data_preprocessor.py
```

### 2. Pre-Training (Base Models)
Establish the base physical relationships and safety parameters by training on the synthetic dataset.
```bash
python train.py
```
This produces foundational PyTorch checkpoints (`.pt`) and scaler configurations in the `checkpoints/` directory.

### 3. Domain Adaptation (Fine-Tuning)
Fine-tune the pre-trained models using real-world datasets. This phase adapts the models to actual sensor noise and unpredictable environmental conditions.
```bash
python finetune.py
```

### 4. Model Quantization and Export (TFLite)
Export the fine-tuned PyTorch models into TensorFlow Lite format, optimized for deployment on mobile edge devices.
```bash
python export.py --finetuned
```
The resulting `.tflite` binaries are automatically injected into the Android application's assets directory.

### 5. Verification
Ensure the quantized TFLite models maintain parity with the original PyTorch models:
```bash
python verify.py
```

## Addressing Architectural Data Leakage

During the initial development phase, architectural data leakage (Train-Serving Skew and Deterministic Target Leakage) was identified in the synthetic pipeline. These issues were systematically resolved to guarantee production-grade robustness.

**1. Deterministic Target Leakage in Recommendations**
Initially, synthetic recommendation labels were generated using strict, deterministic rules. This caused the AI to reverse-engineer the rulesets rather than learn underlying patterns, leading to artificial 100% accuracy.
*Resolution:* We introduced 5% stochastic noise into the label generator to simulate human disagreement, edge cases, and imperfect data.
```python
# data_generator.py - Injection of stochastic label noise
if np.random.rand() < 0.05:
    recs[i] = np.random.randint(0, 8)
```

**2. Pipeline Leakage (Train-Serving Skew)**
The Recommender model was originally trained using pristine Ground Truth `anomaly` labels. However, in a production environment, the system relies on the predicted output from the Autoencoder, which inherently contains False Positives/Negatives.
*Resolution:* We simulated a 10% error rate in the anomaly labels during the Recommender's training. This ensures the model is thoroughly robust against prediction noise when deployed in the field.
```python
# train.py - Simulating Autoencoder prediction noise
true_anomaly = df['anomaly'].values
np.random.seed(42)
noise_mask = np.random.rand(len(true_anomaly)) < 0.10
predicted_anomaly = np.where(noise_mask, 1 - true_anomaly, true_anomaly)
```

## Application and Hardware Deployment

### Android Application
1. Open Android Studio and load the `android/` directory.
2. Synchronize Gradle dependencies.
3. Build the release APK or deploy directly to a connected physical device:
```bash
cd android
./gradlew assembleRelease
```

### ESP32 Firmware
1. Open the `esp32/` directory in the Arduino IDE.
2. Select the operational mode:
   * `esp32_direct.ino`: For closed-loop, offline deployments (operates as a SoftAP).
   * `esp32_cloudflare.ino`: For cloud-connected, distributed telemetry deployments.
3. Configure the designated SSID and Password variables.
4. Select the correct ESP32 target board and compile/upload the firmware.

## Human-in-the-Loop & Verification

While AirKu utilizes advanced Machine Learning algorithms, it operates as an assistive technology. Certain critical aspects of the system require human oversight, verification, and intervention:

1. **Hardware Calibration:** The MQ-135 and DHT22 sensors require physical calibration with load resistors and controlled environments. Human engineers must periodically verify sensor drift and recalibrate the analog-to-digital (ADC) mappings.
2. **Contextual Decision Making:** If the AI detects an anomaly (e.g., a sudden spike in VOCs), it will alert the user. However, a human must investigate the physical space to determine the root cause (e.g., a gas leak, chemical spill, or simply someone applying perfume) before taking drastic measures.
3. **Severe Health Actions:** The AI Recommender suggests actions like activating purifiers or opening windows. For severe health concerns, users must independently assess the situation rather than relying solely on automated outputs.
4. **Maintenance Verification:** The system cannot detect physical obstructions (e.g., dust covering the sensor module). Routine human inspection of the IoT hardware is mandatory to ensure data integrity.

## Medical and System Disclaimer

AirKu is an AI-enhanced hardware and software system designed to provide localized insights into micro-environmental air quality. The embedded TensorFlow Lite models utilize complex probabilistic calculations based on real-time sensor telemetry to offer health and safety recommendations. 

While the system is fine-tuned to deliver highly accurate and practical guidance, it is important to note that AI models and hardware sensors can occasionally produce anomalies or drift due to unpredictable environmental factors. AirKu serves as a powerful supplementary tool for environmental awareness but is not a certified medical device. Users should exercise practical judgment and, for critical health decisions, consult official government air quality reports and seek professional medical advice.

---
*AirKu - Intelligent Micro-Environmental Telemetry and Analysis.*
