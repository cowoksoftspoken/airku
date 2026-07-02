"""
test_intensive.py
-----------------
Intensively tests the exported TFLite models on the real dataset.
Calculates rigorous metrics: Accuracy, Precision, Recall, F1, MAE, RMSE.
"""

import os
import json
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, mean_absolute_error, mean_squared_error, confusion_matrix

def run_inference(interpreter, input_data):
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    # Ensure shape is correct (TFLite expects specific float32 shape)
    input_data = np.array(input_data, dtype=np.float32)
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    return interpreter.get_tensor(output_details[0]['index'])

def main():
    print("============================================================")
    print("AirKu - Intensive TFLite Model Verification on Real Data")
    print("============================================================")

    # 1. Load Real Data
    real_csv = "data/air_quality_real.csv"
    if not os.path.exists(real_csv):
        raise FileNotFoundError(f"{real_csv} not found.")
    df_real = pd.read_csv(real_csv)
    print(f"Loaded real dataset: {len(df_real)} samples")

    # 2. Load Scaler
    scaler_path = "checkpoints/aqi_scaler.json"
    with open(scaler_path) as f:
        scaler = json.load(f)

    min_vals = np.array(scaler["features_min"])
    max_vals = np.array(scaler["features_max"])
    rec_min = np.array(scaler["recommender_min"])
    rec_max = np.array(scaler["recommender_max"])
    aqi_min = float(scaler["aqi_min"])
    aqi_max = float(scaler["aqi_max"])

    # 3. Feature Engineering
    feature_cols = [
        "temperature", "humidity", "mq135_raw", "mq135_ppm",
        "hour_of_day_sin", "hour_of_day_cos", "aqi_rolling_1h", "aqi_rolling_6h",
    ]
    X_scaled = (df_real[feature_cols].values - min_vals) / (max_vals - min_vals + 1e-8)
    
    trend = df_real["aqi_rolling_1h"] - df_real["aqi_rolling_6h"]
    recommender_features = np.column_stack([
        df_real["aqi_class"].values,
        df_real["anomaly"].values,
        trend.values,
        df_real["hour_of_day"].values,
    ])
    X_rec_scaled = (recommender_features - rec_min) / (rec_max - rec_min + 1e-8)
    
    y_cls = df_real["aqi_class"].values
    y_ae = df_real["anomaly"].values
    y_aqi = df_real["aqi"].values
    y_rec = df_real["recommendation"].values

    # Load thresholds and intervals
    meta_path = "data/real_data_meta.json"
    interval_seconds = 60
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            interval_seconds = int(json.load(f).get("interval_seconds", 60))
            
    finetune_meta = "checkpoints/finetune_metrics.json"
    anomaly_threshold = 0.05
    if os.path.exists(finetune_meta):
        with open(finetune_meta) as f:
            anomaly_threshold = float(json.load(f).get("anomaly_new_threshold", 0.05))

    # --- MODEL 1: Classifier ---
    print("\n--- Evaluating Model 1: AQI Classifier ---")
    interpreter1 = tf.lite.Interpreter(model_path="model_1_classifier.tflite")
    interpreter1.allocate_tensors()
    
    preds1 = []
    for i in range(len(X_scaled)):
        out = run_inference(interpreter1, [X_scaled[i]])
        preds1.append(np.argmax(out[0]))
    
    acc1 = accuracy_score(y_cls, preds1)
    p1, r1, f1, _ = precision_recall_fscore_support(y_cls, preds1, average='weighted', zero_division=0)
    print(f"Accuracy : {acc1*100:.2f}%")
    print(f"Precision: {p1:.4f}")
    print(f"Recall   : {r1:.4f}")
    print(f"F1-Score : {f1:.4f}")
    
    # --- MODEL 2: Anomaly Detector ---
    print("\n--- Evaluating Model 2: Anomaly Detector ---")
    interpreter2 = tf.lite.Interpreter(model_path="model_2_anomaly.tflite")
    interpreter2.allocate_tensors()
    
    preds2 = []
    recon_errors = []
    for i in range(len(X_scaled)):
        out = run_inference(interpreter2, [X_scaled[i]])
        error = np.mean((out[0] - X_scaled[i])**2)
        recon_errors.append(error)
        preds2.append(1 if error > anomaly_threshold else 0)
        
    acc2 = accuracy_score(y_ae, preds2)
    p2, r2, f2, _ = precision_recall_fscore_support(y_ae, preds2, average='binary', zero_division=0)
    print(f"Anomaly Threshold: {anomaly_threshold:.6f}")
    print(f"Accuracy : {acc2*100:.2f}%")
    print(f"Precision: {p2:.4f}")
    print(f"Recall   : {r2:.4f}")
    print(f"F1-Score : {f2:.4f}")
    
    # --- MODEL 3: AQI Predictor ---
    print("\n--- Evaluating Model 3: AQI Predictor (LSTM) ---")
    interpreter3 = tf.lite.Interpreter(model_path="model_3_predictor.tflite")
    interpreter3.allocate_tensors()
    
    SEQ_LEN = 12
    LEAD_TIME = 60
    real_lead_time = max(1, int(round((LEAD_TIME * 60) / interval_seconds)))
    
    preds3 = []
    trues3 = []
    for i in range(len(X_scaled) - SEQ_LEN - real_lead_time + 1):
        seq = X_scaled[i : i + SEQ_LEN]
        out = run_inference(interpreter3, [seq])
        pred_scaled = out[0][0]
        pred_val = pred_scaled * (aqi_max - aqi_min) + aqi_min
        true_val = y_aqi[i + SEQ_LEN - 1 + real_lead_time]
        
        preds3.append(pred_val)
        trues3.append(true_val)
        
    if len(preds3) > 0:
        mae3 = mean_absolute_error(trues3, preds3)
        rmse3 = np.sqrt(mean_squared_error(trues3, preds3))
        print(f"Tested sequences: {len(preds3)}")
        print(f"MAE  : {mae3:.2f}")
        print(f"RMSE : {rmse3:.2f}")
    else:
        print("Not enough data to form sequences for testing.")
        
    # --- MODEL 4: Recommender ---
    print("\n--- Evaluating Model 4: Recommendation Engine ---")
    interpreter4 = tf.lite.Interpreter(model_path="model_4_recommender.tflite")
    interpreter4.allocate_tensors()
    
    preds4 = []
    for i in range(len(X_rec_scaled)):
        out = run_inference(interpreter4, [X_rec_scaled[i]])
        preds4.append(np.argmax(out[0]))
        
    acc4 = accuracy_score(y_rec, preds4)
    p4, r4, f4, _ = precision_recall_fscore_support(y_rec, preds4, average='weighted', zero_division=0)
    print(f"Accuracy : {acc4*100:.2f}%")
    print(f"Precision: {p4:.4f}")
    print(f"Recall   : {r4:.4f}")
    print(f"F1-Score : {f4:.4f}")

    print("\n============================================================")
    print("Intensive Test Completed Successfully!")
    print("============================================================")

if __name__ == "__main__":
    main()
