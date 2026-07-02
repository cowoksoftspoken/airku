import numpy as np
import tensorflow as tf
import time
import os
import json

def verify_tflite_model(model_path, expected_input_shape, expected_output_shape, dummy_input):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
        
    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    act_in_shape = input_details[0]['shape'].tolist()
    act_out_shape = output_details[0]['shape'].tolist()
    
    print(f"\nVerifying {model_path}:")
    print(f"  Input details: {input_details[0]['name']} | shape: {act_in_shape} | dtype: {input_details[0]['dtype']}")
    print(f"  Output details: {output_details[0]['name']} | shape: {act_out_shape} | dtype: {output_details[0]['dtype']}")
    
    # Test batch size match
    # Since dynamic axes are compiled, TFLite models usually have static batch size (like 1) or keep it dynamic
    # Let's adjust dummy_input batch size to match act_in_shape[0] if needed
    if act_in_shape[0] != dummy_input.shape[0] and act_in_shape[0] > 0:
        # Resize inputs to match dummy batch size if TFLite supports dynamic batch
        # Otherwise, adjust dummy input batch size
        dummy_input = np.repeat(dummy_input, act_in_shape[0], axis=0) if act_in_shape[0] > dummy_input.shape[0] else dummy_input[:act_in_shape[0]]
        
    # Warmup
    interpreter.set_tensor(input_details[0]['index'], dummy_input.astype(input_details[0]['dtype']))
    interpreter.invoke()
    
    # Benchmarking
    num_runs = 200
    start = time.perf_counter()
    for _ in range(num_runs):
        interpreter.set_tensor(input_details[0]['index'], dummy_input.astype(input_details[0]['dtype']))
        interpreter.invoke()
        res = interpreter.get_tensor(output_details[0]['index'])
    end = time.perf_counter()
    
    latency_ms = (end - start) * 1000.0 / num_runs
    model_size_kb = os.path.getsize(model_path) / 1024.0
    
    print(f"  Average Inference Latency: {latency_ms:.3f} ms")
    print(f"  Model Size: {model_size_kb:.2f} KB")
    
    return latency_ms, model_size_kb

def main():
    print("--- Starting TFLite Inference Verification ---")
    
    with open('model_manifest.json', 'r') as f:
        manifest = json.load(f)
        
    models_info = manifest['models']
    
    # Verify Classifier
    dummy_cls = np.random.randn(1, 8).astype(np.float32)
    lat_cls, size_cls = verify_tflite_model(
        models_info['classifier']['file'],
        models_info['classifier']['input_shape'],
        models_info['classifier']['output_shape'],
        dummy_cls
    )
    
    # Verify Anomaly
    dummy_ae = np.random.randn(1, 8).astype(np.float32)
    lat_ae, size_ae = verify_tflite_model(
        models_info['anomaly']['file'],
        models_info['anomaly']['input_shape'],
        models_info['anomaly']['output_shape'],
        dummy_ae
    )
    
    # Verify Predictor
    dummy_pred = np.random.randn(1, 12, 8).astype(np.float32)
    lat_pred, size_pred = verify_tflite_model(
        models_info['predictor']['file'],
        models_info['predictor']['input_shape'],
        models_info['predictor']['output_shape'],
        dummy_pred
    )
    
    # Verify Recommender
    dummy_rec = np.random.randn(1, 4).astype(np.float32)
    lat_rec, size_rec = verify_tflite_model(
        models_info['recommender']['file'],
        models_info['recommender']['input_shape'],
        models_info['recommender']['output_shape'],
        dummy_rec
    )
    
    total_size_mb = (size_cls + size_ae + size_pred + size_rec) / 1024.0
    total_latency_ms = lat_cls + lat_ae + lat_pred + lat_rec
    
    print("\n--- FINAL TFLITE PIPELINE PERFORMANCE REPORT ---")
    print(f"Classifier  | Size: {size_cls:.2f} KB | Latency: {lat_cls:.3f} ms")
    print(f"Anomaly     | Size: {size_ae:.2f} KB | Latency: {lat_ae:.3f} ms")
    print(f"Predictor   | Size: {size_pred:.2f} KB | Latency: {lat_pred:.3f} ms")
    print(f"Recommender | Size: {size_rec:.2f} KB | Latency: {lat_rec:.3f} ms")
    print(f"-------------------------------------------------")
    print(f"Total Pipeline Size: {total_size_mb:.3f} MB (Target < 2.5 MB)")
    print(f"Total Pipeline Latency: {total_latency_ms:.3f} ms (Target < 50.0 ms)")
    
    # Write verification results to file
    results = {
        'classifier': {'size_kb': size_cls, 'latency_ms': lat_cls},
        'anomaly': {'size_kb': size_ae, 'latency_ms': lat_ae},
        'predictor': {'size_kb': size_pred, 'latency_ms': lat_pred},
        'recommender': {'size_kb': size_rec, 'latency_ms': lat_rec},
        'total_size_mb': total_size_mb,
        'total_latency_ms': total_latency_ms
    }
    with open('checkpoints/verification_report.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    main()
