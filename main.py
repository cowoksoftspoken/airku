import os
import subprocess
import json

def run_script(script_name):
    print(f"\n==================================================")
    print(f"RUNNING: {script_name}")
    print(f"==================================================")
    res = subprocess.run(["python", script_name], capture_output=False)
    if res.returncode != 0:
        raise RuntimeError(f"Script {script_name} failed with return code {res.returncode}")

def main():
    # 1. Generate Dataset
    run_script("data_generator.py")
    
    # 2. Train Models
    run_script("train.py")
    
    # 3. Export Models to TFLite
    run_script("export.py")
    
    # 4. Verify Models
    run_script("verify.py")
    
    # 5. Print Final Summary Metrics Report
    print("\n==================================================")
    print("ALL PIPELINE STAGES COMPLETED SUCCESSFULLY!")
    print("==================================================")
    
    # Read training metrics
    with open('checkpoints/training_metrics.json', 'r') as f:
        train_metrics = json.load(f)
        
    # Read verification report
    with open('checkpoints/verification_report.json', 'r') as f:
        verify_report = json.load(f)
        
    print("\nAirKu ML Models Pipeline Metrics Summary:")
    print("----------------------------------------------------------------------")
    print(f"Model 1: Classifier   | Accuracy: {train_metrics['classifier_test_acc']*100:.2f}% | Latency: {verify_report['classifier']['latency_ms']:.3f} ms | Size: {verify_report['classifier']['size_kb']:.1f} KB")
    print(f"Model 2: Anomaly      | Val F1: {train_metrics['anomaly_val_f1']*100:.2f}%     | Latency: {verify_report['anomaly']['latency_ms']:.3f} ms | Size: {verify_report['anomaly']['size_kb']:.1f} KB")
    print(f"Model 3: Predictor    | MAE: {train_metrics['predictor_test_mae']:.2f} AQI      | Latency: {verify_report['predictor']['latency_ms']:.3f} ms | Size: {verify_report['predictor']['size_kb']:.1f} KB")
    print(f"Model 4: Recommender  | Accuracy: {train_metrics['recommender_test_acc']*100:.2f}% | Latency: {verify_report['recommender']['latency_ms']:.3f} ms | Size: {verify_report['recommender']['size_kb']:.1f} KB")
    print("----------------------------------------------------------------------")
    print(f"Total Pipeline Latency: {verify_report['total_latency_ms']:.3f} ms (Target < 50ms)")
    print(f"Total Pipeline Size: {verify_report['total_size_mb']:.3f} MB (Target < 2.5MB)")
    print("==================================================")

if __name__ == '__main__':
    main()
