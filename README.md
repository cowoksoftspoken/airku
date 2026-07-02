# AirKu - IoT & AI Air Quality Monitoring System

AirKu is a comprehensive IoT and Machine Learning solution designed to monitor indoor and micro-environmental air quality. The system collects physical sensor data, processes it through a multi-model Artificial Intelligence pipeline, and delivers real-time health recommendations to users via a native Android application.

This repository contains the complete ecosystem, including the Machine Learning pipeline, Android application source code, ESP32 firmware, and backend configurations.

## System Architecture

The AirKu ecosystem consists of four main pillars:

1.  **Hardware (ESP32 & Sensors):** Captures raw environmental data including Temperature, Humidity, and Gas concentrations (via MQ-135/DHT sensors).
2.  **Edge AI (TFLite):** Executes a sophisticated 4-stage machine learning pipeline locally on the user's mobile device to ensure data privacy (Edge Computing).
    *   **Model 1 (Classifier):** Categorizes Air Quality Index (AQI) into discrete health classes.
    *   **Model 2 (Autoencoder):** Detects sudden sensor anomalies or hardware drift.
    *   **Model 3 (LSTM Predictor):** Forecasts air quality trends for the next hour.
    *   **Model 4 (Recommender):** Provides actionable health directives based on current states and trends.
3.  **Android Client:** Built with native Kotlin and Jetpack Compose, providing real-time dashboards, historical data tracking, and AI-driven insights.
4.  **Backend (Optional):** A Cloudflare-based edge server for routing multiple ESP32 payloads over wide-area networks.

## Repository Structure

```text
.
├── android/             # Android client source code (Kotlin, Jetpack Compose)
├── backend/             # Edge server backend source code (Cloudflare Workers / Node.js)
├── checkpoints/         # Pre-trained PyTorch weights, ONNX files, and Scaler configs
├── data/                # Synthetic and real-world datasets used for model training
├── design/              # UI/UX design specifications and assets
├── esp32/               # Arduino IDE firmware configurations (.ino)
├── esp32_firmware/      # PlatformIO firmware project for ESP32
├── *.py                 # Machine Learning pipeline scripts
└── README.md            # Project documentation
```

## Prerequisites

To build and run all components of this project, ensure you have the following installed:

*   **Machine Learning Pipeline:** Python 3.9+, PyTorch, TensorFlow, scikit-learn, pandas, numpy, imbalanced-learn.
*   **Android App:** Android Studio (latest version), Java Development Kit (JDK) 11 or 17, Android SDK.
*   **ESP32 Firmware:** PlatformIO IDE or Arduino IDE with ESP32 board manager installed.

## Machine Learning Pipeline Execution

The AI pipeline is designed using a Two-Stage transfer learning approach: Synthetic Pre-training followed by Real-World Fine-Tuning. This mitigates cold-start problems and ensures robustness against real-world sensor noise.

### 1. Data Generation and Preprocessing
To generate the base synthetic dataset mapping ideal physical-chemical relationships:
```bash
python data_generator.py
```
To preprocess the real-world dataset (e.g., from FigShare) for fine-tuning:
```bash
python data_preprocessor.py
```

### 2. Pre-Training (Base Models)
Train the initial models on the synthetic dataset. This step establishes the base physical relationships and safety rules.
```bash
python train.py
```
This will output base `.pt` checkpoints and scaler configurations in the `checkpoints/` directory.

### 3. Fine-Tuning (Domain Adaptation)
Fine-tune the pre-trained models using the real-world dataset to adapt to actual sensor drift and unpredictable environmental anomalies.
```bash
python finetune.py
```
This generates `*_finetuned.pt` weights.

### 4. Model Export (TFLite)
Export the PyTorch models into TensorFlow Lite format optimized for Android Edge deployment.
```bash
# Export the fine-tuned models
python export.py --finetuned
```
The resulting `.tflite` files will be automatically copied to the `android/app/src/main/assets/` directory.

### 5. Verification
Verify that the quantized TFLite models produce results consistent with the original PyTorch models:
```bash
python verify.py
```

### Addressing Synthetic Data Leakage

During the initial synthetic pre-training phase, architectural data leakage (Train-Serving Skew and Deterministic Target Leakage) was discovered and subsequently resolved to ensure production-grade robustness.

**1. Deterministic Target Leakage in Recommendations**
Initially, the synthetic recommendation labels were generated using strict, deterministic rules. This caused the AI to merely reverse-engineer the logic rather than learn complex patterns, leading to artificial 100% accuracy.
*Fix:* We injected 5% stochastic noise into the label generator to simulate human disagreement, edge cases, and dirty data.
```python
# data_generator.py - Injection of stochastic label noise
if np.random.rand() < 0.05:
    recs[i] = np.random.randint(0, 8)
```

**2. Pipeline Leakage (Train-Serving Skew)**
The Recommender model was originally trained using pristine Ground Truth `anomaly` labels. However, in production on the Android device, the system relies on the predicted output from the Autoencoder, which inherently contains False Positives/Negatives.
*Fix:* We simulated an error rate in the anomaly labels during the Recommender's training to ensure the model is robust against prediction noise when deployed.
```python
# train.py - Simulating Autoencoder prediction noise
true_anomaly = df['anomaly'].values
np.random.seed(42)
noise_mask = np.random.rand(len(true_anomaly)) < 0.10
predicted_anomaly = np.where(noise_mask, 1 - true_anomaly, true_anomaly)

recommender_features = np.column_stack([
    df['aqi_class'].values,
    predicted_anomaly,
    trend.values,
    df['hour_of_day'].values
])
```

## Android Application Setup

The Android application acts as the primary user interface and AI inference engine.

1.  Open **Android Studio**.
2.  Select **Open an existing Android Studio project** and navigate to the `android/` directory.
3.  Allow Gradle to sync project dependencies.
4.  Ensure an Android device or emulator (API Level 24+) is connected.
5.  Run the application by clicking the **Run** button (Shift + F10) or via terminal:
    ```bash
    cd android
    ./gradlew assembleRelease
    ```

## ESP32 Firmware Deployment

You can flash the ESP32 using either PlatformIO or Arduino IDE.

**Using PlatformIO:**
1.  Open the `esp32_firmware/` directory in VS Code with the PlatformIO extension.
2.  Connect your ESP32 board via USB.
3.  Click the **Upload** button in the PlatformIO toolbar.

**Using Arduino IDE:**
1.  Navigate to the `esp32/` directory.
2.  Open either `esp32_direct.ino` (for local network direct connection) or `esp32_cloudflare.ino` (for backend-routed connection) depending on your network architecture.
3.  Configure your WiFi credentials within the file.
4.  Select the correct ESP32 board and COM port.
5.  Click **Upload**.

## Responsible AI & Data Privacy

AirKu strictly adheres to Responsible AI principles. 
*   **Privacy-First:** All complex AI inferences (classification, anomaly detection, predictions) are executed locally via Edge Computing. Raw sensor data does not need to be transmitted to external servers for AI processing, protecting user behavior privacy.
*   **Safety Fallbacks:** The system implements strict rule-based bypasses for critical AQI thresholds, ensuring that AI prediction inaccuracies do not suppress critical health warnings.

## Disclaimer

**Medical and Health Disclaimer:** AirKu is an AI-driven experimental tool designed for micro-environmental monitoring. The Artificial Intelligence models (TFLite) provide recommendations based on probabilistic calculations and hardware sensor readings which are subject to drift, inaccuracies, and environmental anomalies. **AirKu is NOT a certified medical device.** The AI's predictions and recommendations can be incorrect. Users must not solely rely on this application for critical health decisions, especially for vulnerable individuals (e.g., asthma patients). Always consult official government air quality reports and seek professional medical advice.

---
*Developed for Air Quality Monitoring and Environmental Intelligence.*
