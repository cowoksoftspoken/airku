import torch
import os
import json
import shutil
import argparse
import subprocess
from models import AQIClassifier, AnomalyDetector, AQIPredictor, AQIRecommender

def export_to_onnx(model, dummy_input, onnx_path):
    torch.onnx.export(
        model, dummy_input, onnx_path,
        input_names=["input"],
        output_names=["output"],
        opset_version=17
    )
    print(f"Exported to ONNX: {onnx_path}")

def run_onnx2tf(onnx_path, output_dir, extra_args=None):
    print(f"Running onnx2tf for {onnx_path}...")
    cmd = ["onnx2tf", "-i", onnx_path, "-o", output_dir, "-b", "1"]
    if extra_args:
        cmd.extend(extra_args)
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Failed to convert {onnx_path} to TF/TFLite!")
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
        raise RuntimeError(f"onnx2tf failed for {onnx_path}")
    print(f"Successfully converted {onnx_path} to TF/TFLite!")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--finetuned", action="store_true",
                        help="Export from finetuned checkpoints instead of original")
    args = parser.parse_args()

    os.makedirs('checkpoints', exist_ok=True)
    device = torch.device("cpu") # Export can be done on CPU safely
    
    # 1. Export Model 1: Classifier
    print("\n--- Exporting Model 1: AQI Classifier ---")
    model_cls = AQIClassifier(export=True)
    ckpt1_name = 'checkpoints/model_1_finetuned.pt' if args.finetuned else 'checkpoints/model_1_classifier.pt'
    chk1 = torch.load(ckpt1_name, map_location=device)
    model_cls.load_state_dict(chk1['model_state_dict'])
    model_cls.eval()
    dummy1 = torch.randn(1, 8)
    export_to_onnx(model_cls, dummy1, 'checkpoints/model_1_classifier.onnx')
    run_onnx2tf('checkpoints/model_1_classifier.onnx', 'checkpoints/model_1_savedmodel')
    shutil.copy(
        'checkpoints/model_1_savedmodel/model_1_classifier_float16.tflite',
        'model_1_classifier.tflite'
    )
    
    # 2. Export Model 2: Anomaly Detector
    print("\n--- Exporting Model 2: Anomaly Detector ---")
    model_ae = AnomalyDetector()
    ckpt2_name = 'checkpoints/model_2_finetuned.pt' if args.finetuned else 'checkpoints/model_2_anomaly.pt'
    chk2 = torch.load(ckpt2_name, map_location=device)
    model_ae.load_state_dict(chk2['model_state_dict'])
    model_ae.eval()
    dummy2 = torch.randn(1, 8)
    export_to_onnx(model_ae, dummy2, 'checkpoints/model_2_anomaly.onnx')
    run_onnx2tf('checkpoints/model_2_anomaly.onnx', 'checkpoints/model_2_savedmodel')
    shutil.copy(
        'checkpoints/model_2_savedmodel/model_2_anomaly_float16.tflite',
        'model_2_anomaly.tflite'
    )
    anomaly_threshold = float(chk2['anomaly_threshold'])
    
    # 3. Export Model 3: Predictor
    print("\n--- Exporting Model 3: AQI Predictor ---")
    model_ts = AQIPredictor()
    ckpt3_name = 'checkpoints/model_3_finetuned.pt' if args.finetuned else 'checkpoints/model_3_predictor.pt'
    chk3 = torch.load(ckpt3_name, map_location=device)
    model_ts.load_state_dict(chk3['model_state_dict'])
    model_ts.eval()
    dummy3 = torch.randn(1, 12, 8)
    export_to_onnx(model_ts, dummy3, 'checkpoints/model_3_predictor.onnx')
    run_onnx2tf('checkpoints/model_3_predictor.onnx', 'checkpoints/model_3_savedmodel', extra_args=["-kat", "input"])
    shutil.copy(
        'checkpoints/model_3_savedmodel/model_3_predictor_float16.tflite',
        'model_3_predictor.tflite'
    )
    
    # 4. Export Model 4: Recommender
    print("\n--- Exporting Model 4: Recommendation Engine ---")
    model_rec = AQIRecommender(export=True)
    ckpt4_name = 'checkpoints/model_4_finetuned.pt' if args.finetuned else 'checkpoints/model_4_recommender.pt'
    chk4 = torch.load(ckpt4_name, map_location=device)
    model_rec.load_state_dict(chk4['model_state_dict'])
    model_rec.eval()
    dummy4 = torch.randn(1, 4)
    export_to_onnx(model_rec, dummy4, 'checkpoints/model_4_recommender.onnx')
    run_onnx2tf('checkpoints/model_4_recommender.onnx', 'checkpoints/model_4_savedmodel')
    shutil.copy(
        'checkpoints/model_4_savedmodel/model_4_recommender_float16.tflite',
        'model_4_recommender.tflite'
    )
    
    # Copy scaler config
    shutil.copy('checkpoints/aqi_scaler.json', 'aqi_scaler.json')
    
    # Write recommendation_labels.json
    rec_labels = {
        "0": {
            "action": "open_window",
            "title": "Buka Jendela",
            "message": "Ventilasi ruangan perlu ditingkatkan. Buka jendela untuk sirkulasi udara yang lebih baik.",
            "icon": "window"
        },
        "1": {
            "action": "close_window",
            "title": "Tutup Jendela",
            "message": "Kualitas udara memburuk. Tutup jendela untuk mencegah udara kotor masuk.",
            "icon": "window-closed"
        },
        "2": {
            "action": "use_air_purifier",
            "title": "Nyalakan Purifier",
            "message": "Terdeteksi polutan atau anomali udara. Nyalakan pembersih udara (air purifier).",
            "icon": "purifier"
        },
        "3": {
            "action": "avoid_outdoor",
            "title": "Hindari Aktivitas Luar",
            "message": "Kualitas udara berbahaya. Batasi aktivitas di luar ruangan.",
            "icon": "alert"
        },
        "4": {
            "action": "safe_outdoor",
            "title": "Aman Beraktivitas Luar",
            "message": "Kualitas udara bersih. Sangat aman untuk beraktivitas di luar ruangan.",
            "icon": "check"
        },
        "5": {
            "action": "reduce_cooking",
            "title": "Kurangi Memasak",
            "message": "Terdeteksi akumulasi gas dapur. Kurangi memasak atau nyalakan exhaust fan.",
            "icon": "cook"
        },
        "6": {
            "action": "check_ventilation",
            "title": "Periksa Ventilasi",
            "message": "Sirkulasi udara kurang ideal. Periksa ventilasi ruangan Anda.",
            "icon": "vent"
        },
        "7": {
            "action": "all_clear",
            "title": "Udara Optimal",
            "message": "Kualitas udara dalam kondisi terbaik. Pertahankan kondisi ventilasi saat ini.",
            "icon": "check"
        }
    }
    with open('recommendation_labels.json', 'w') as f:
        json.dump(rec_labels, f, indent=2)
    print("Saved recommendation_labels.json")
    
    # Write model_manifest.json
    manifest = {
        "version": "1.0.0",
        "models": {
            "classifier":   { "file": "model_1_classifier.tflite",  "input_shape": [1, 8],     "output_shape": [1, 4]  },
            "anomaly":      { "file": "model_2_anomaly.tflite",     "input_shape": [1, 8],     "output_shape": [1, 8]  },
            "predictor":    { "file": "model_3_predictor.tflite",   "input_shape": [1, 12, 8], "output_shape": [1, 1]  },
            "recommender":  { "file": "model_4_recommender.tflite", "input_shape": [1, 4],     "output_shape": [1, 8]  }
        },
        "anomaly_threshold": anomaly_threshold,
        "aqi_classes": ["Baik", "Sedang", "Tidak Sehat", "Berbahaya"],
        "aqi_colors":  ["#16A34A", "#D97706", "#DC2626", "#7C3AED"]
    }
    with open('model_manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    print("Saved model_manifest.json")
    print("\n--- Export Completed Successfully! ---")

if __name__ == '__main__':
    main()
