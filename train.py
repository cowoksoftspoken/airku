import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np
import json
import os
from models import AQIClassifier, AnomalyDetector, AQIPredictor, AQIRecommender

class AirKuDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32 if len(y.shape) > 1 and y.shape[1] == 1 else torch.long)
        
    def __len__(self):
        return len(self.X)
        
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

class TimeSeriesDataset(Dataset):
    def __init__(self, data, target, seq_len=12, lead_time=60):
        self.data = torch.tensor(data, dtype=torch.float32)
        self.target = torch.tensor(target, dtype=torch.float32)
        self.seq_len = seq_len
        self.lead_time = lead_time
        
    def __len__(self):
        return len(self.data) - self.seq_len - self.lead_time + 1
        
    def __getitem__(self, idx):
        x = self.data[idx : idx + self.seq_len]
        y = self.target[idx + self.seq_len - 1 + self.lead_time]
        return x, y.unsqueeze(0)

def train_model(model, train_loader, val_loader, criterion, optimizer, scheduler, device, epochs=100, is_reconstruction=False):
    scaler = torch.amp.GradScaler('cuda')
    best_loss = float('inf')
    best_weights = None
    
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            
            with torch.amp.autocast('cuda'):
                outputs = model(X_batch)
                loss = criterion(outputs, X_batch if is_reconstruction else y_batch)
                
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            
            train_loss += loss.item() * X_batch.size(0)
            
        scheduler.step()
        
        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                with torch.amp.autocast('cuda'):
                    outputs = model(X_batch)
                    loss = criterion(outputs, X_batch if is_reconstruction else y_batch)
                val_loss += loss.item() * X_batch.size(0)
                
        epoch_train_loss = train_loss / len(train_loader.dataset)
        epoch_val_loss = val_loss / len(val_loader.dataset)
        
        if epoch_val_loss < best_loss:
            best_loss = epoch_val_loss
            best_weights = model.state_dict().copy()
            
    # Load best weights
    model.load_state_dict(best_weights)
    return best_loss

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    if device.type == 'cuda':
        print("GPU:", torch.cuda.get_device_name(0))
        
    # Load dataset
    df = pd.read_csv('data/air_quality_dataset.csv')
    n = len(df)
    
    # Define features and targets
    feature_cols = [
        'temperature', 'humidity', 'mq135_raw', 'mq135_ppm',
        'hour_of_day_sin', 'hour_of_day_cos', 'aqi_rolling_1h', 'aqi_rolling_6h'
    ]
    
    # Calculate fit limits on training set (70% split)
    train_size = int(0.7 * n)
    val_size = int(0.15 * n)
    
    df_train = df.iloc[:train_size]
    
    # MinMax Scaler construction
    min_vals = df_train[feature_cols].min().values
    max_vals = df_train[feature_cols].max().values
    
    # Normalize features
    X_scaled = (df[feature_cols].values - min_vals) / (max_vals - min_vals + 1e-8)
    
    # Recommender inputs: [aqi_class, anomaly, trend, hour_of_day]
    trend = df['aqi_rolling_1h'] - df['aqi_rolling_6h']
    # Simulate predicted anomaly from Model 2 (with ~10% error) to prevent pipeline leakage
    # In production, we don't have perfect ground truth for anomalies.
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
    
    rec_train = recommender_features[:train_size]
    rec_min = rec_train.min(axis=0)
    rec_max = rec_train.max(axis=0)
    
    X_rec_scaled = (recommender_features - rec_min) / (rec_max - rec_min + 1e-8)
    
    # Target AQI limits for predictor
    y_aqi = df['aqi'].values
    aqi_min = float(y_aqi[:train_size].min())
    aqi_max = float(y_aqi[:train_size].max())
    y_aqi_scaled = (y_aqi - aqi_min) / (aqi_max - aqi_min + 1e-8)
    
    # Save Scaler Config
    os.makedirs('checkpoints', exist_ok=True)
    scaler_config = {
        'features_min': min_vals.tolist(),
        'features_max': max_vals.tolist(),
        'recommender_min': rec_min.tolist(),
        'recommender_max': rec_max.tolist(),
        'aqi_min': aqi_min,
        'aqi_max': aqi_max
    }
    with open('checkpoints/aqi_scaler.json', 'w') as f:
        json.dump(scaler_config, f, indent=2)
    print("Scaler config saved to checkpoints/aqi_scaler.json")
    
    # Splits indices
    train_idx = train_size
    val_idx = train_size + val_size
    
    # --- MODEL 1: AQI Classifier ---
    print("\n--- Training Model 1: AQI Classifier ---")
    y_cls = df['aqi_class'].values
    
    train_dataset = AirKuDataset(X_scaled[:train_idx], y_cls[:train_idx])
    val_dataset = AirKuDataset(X_scaled[train_idx:val_idx], y_cls[train_idx:val_idx])
    test_dataset = AirKuDataset(X_scaled[val_idx:], y_cls[val_idx:])
    
    train_loader = DataLoader(train_dataset, batch_size=256, shuffle=True, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=256, shuffle=False, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=256, shuffle=False, pin_memory=True)
    
    model_cls = AQIClassifier().to(device)
    optimizer = torch.optim.AdamW(model_cls.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50)
    criterion = nn.CrossEntropyLoss()
    
    best_val_loss = train_model(model_cls, train_loader, val_loader, criterion, optimizer, scheduler, device, epochs=80)
    
    # Test Evaluation
    model_cls.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            outputs = model_cls(X_batch)
            _, predicted = torch.max(outputs, 1)
            total += y_batch.size(0)
            correct += (predicted == y_batch).sum().item()
    test_acc = correct / total
    print(f"Model 1 Val Loss: {best_val_loss:.4f} | Test Accuracy: {test_acc * 100:.2f}%")
    
    torch.save({
        'model_state_dict': model_cls.state_dict(),
        'test_acc': test_acc
    }, 'checkpoints/model_1_classifier.pt')
    
    # --- MODEL 2: Anomaly Detector ---
    print("\n--- Training Model 2: Anomaly Detector (Autoencoder) ---")
    # Train only on normal samples (anomaly == 0) in training set
    train_normal_mask = df['anomaly'].values[:train_idx] == 0
    X_train_normal = X_scaled[:train_idx][train_normal_mask]
    
    # Validation uses normal + anomaly validation sets to establish threshold
    val_normal_mask = df['anomaly'].values[train_idx:val_idx] == 0
    X_val_normal = X_scaled[train_idx:val_idx][val_normal_mask]
    
    train_ae_dataset = AirKuDataset(X_train_normal, X_train_normal) # Self-reconstruction
    val_ae_dataset = AirKuDataset(X_val_normal, X_val_normal)
    
    train_ae_loader = DataLoader(train_ae_dataset, batch_size=256, shuffle=True, pin_memory=True)
    val_ae_loader = DataLoader(val_ae_dataset, batch_size=256, shuffle=False, pin_memory=True)
    
    model_ae = AnomalyDetector().to(device)
    optimizer = torch.optim.AdamW(model_ae.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50)
    criterion_ae = nn.MSELoss()
    
    best_ae_val_loss = train_model(model_ae, train_ae_loader, val_ae_loader, criterion_ae, optimizer, scheduler, device, epochs=80, is_reconstruction=True)
    
    # Determine Anomaly Threshold on validation set (normal + anomalies)
    model_ae.eval()
    val_all_dataset = AirKuDataset(X_scaled[train_idx:val_idx], df['anomaly'].values[train_idx:val_idx])
    val_all_loader = DataLoader(val_all_dataset, batch_size=256, shuffle=False)
    
    reconstruction_errors = []
    val_anoms = []
    with torch.no_grad():
        for X_batch, y_batch in val_all_loader:
            X_batch = X_batch.to(device)
            outputs = model_ae(X_batch)
            errors = torch.mean((outputs - X_batch) ** 2, dim=1).cpu().numpy()
            reconstruction_errors.extend(errors)
            val_anoms.extend(y_batch.numpy())
            
    reconstruction_errors = np.array(reconstruction_errors)
    val_anoms = np.array(val_anoms)
    
    # Set threshold to maximize F1-score or default to 98th percentile of normal reconstruction errors
    normal_errors = reconstruction_errors[val_anoms == 0]
    anomaly_threshold = float(np.percentile(normal_errors, 97.5))
    
    # Validate F1
    preds = (reconstruction_errors > anomaly_threshold).astype(int)
    tp = np.sum((preds == 1) & (val_anoms == 1))
    fp = np.sum((preds == 1) & (val_anoms == 0))
    fn = np.sum((preds == 0) & (val_anoms == 1))
    precision = tp / (tp + fp + 1e-8)
    recall = tp / (tp + fn + 1e-8)
    f1 = 2 * precision * recall / (precision + recall + 1e-8)
    print(f"Model 2 Val Loss: {best_ae_val_loss:.6f} | Selected Threshold: {anomaly_threshold:.6f} | Val F1: {f1 * 100:.2f}%")
    
    torch.save({
        'model_state_dict': model_ae.state_dict(),
        'anomaly_threshold': anomaly_threshold
    }, 'checkpoints/model_2_anomaly.pt')
    
    # --- MODEL 3: AQI Trend Predictor ---
    print("\n--- Training Model 3: AQI Trend Predictor (LSTM) ---")
    train_ts_dataset = TimeSeriesDataset(X_scaled[:train_idx], y_aqi_scaled[:train_idx])
    val_ts_dataset = TimeSeriesDataset(X_scaled[train_idx:val_idx], y_aqi_scaled[train_idx:val_idx])
    test_ts_dataset = TimeSeriesDataset(X_scaled[val_idx:], y_aqi_scaled[val_idx:])
    
    train_ts_loader = DataLoader(train_ts_dataset, batch_size=256, shuffle=True, pin_memory=True)
    val_ts_loader = DataLoader(val_ts_dataset, batch_size=256, shuffle=False, pin_memory=True)
    test_ts_loader = DataLoader(test_ts_dataset, batch_size=256, shuffle=False, pin_memory=True)
    
    model_ts = AQIPredictor().to(device)
    optimizer = torch.optim.AdamW(model_ts.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50)
    criterion_ts = nn.HuberLoss()
    
    best_ts_val_loss = train_model(model_ts, train_ts_loader, val_ts_loader, criterion_ts, optimizer, scheduler, device, epochs=80)
    
    # Test Evaluation (MAE) in original scale
    model_ts.eval()
    mae_sum = 0.0
    total_samples = 0
    with torch.no_grad():
        for X_batch, y_batch in test_ts_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            outputs = model_ts(X_batch)
            pred_rescaled = outputs * (aqi_max - aqi_min) + aqi_min
            target_rescaled = y_batch * (aqi_max - aqi_min) + aqi_min
            mae_sum += torch.abs(pred_rescaled - target_rescaled).sum().item()
            total_samples += y_batch.size(0)
    test_mae = mae_sum / total_samples
    print(f"Model 3 Val Huber Loss: {best_ts_val_loss:.4f} | Test MAE: {test_mae:.2f} AQI points")
    
    torch.save({
        'model_state_dict': model_ts.state_dict(),
        'test_mae': test_mae
    }, 'checkpoints/model_3_predictor.pt')
    
    # --- MODEL 4: Recommendation Engine ---
    print("\n--- Training Model 4: Recommendation Engine ---")
    y_rec = df['recommendation'].values
    
    train_rec_dataset = AirKuDataset(X_rec_scaled[:train_idx], y_rec[:train_idx])
    val_rec_dataset = AirKuDataset(X_rec_scaled[train_idx:val_idx], y_rec[train_idx:val_idx])
    test_rec_dataset = AirKuDataset(X_rec_scaled[val_idx:], y_rec[val_idx:])
    
    train_rec_loader = DataLoader(train_rec_dataset, batch_size=256, shuffle=True, pin_memory=True)
    val_rec_loader = DataLoader(val_rec_dataset, batch_size=256, shuffle=False, pin_memory=True)
    test_rec_loader = DataLoader(test_rec_dataset, batch_size=256, shuffle=False, pin_memory=True)
    
    model_rec = AQIRecommender().to(device)
    optimizer = torch.optim.AdamW(model_rec.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50)
    criterion_rec = nn.CrossEntropyLoss()
    
    best_rec_val_loss = train_model(model_rec, train_rec_loader, val_rec_loader, criterion_rec, optimizer, scheduler, device, epochs=80)
    
    # Test Evaluation
    model_rec.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for X_batch, y_batch in test_rec_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            outputs = model_rec(X_batch)
            _, predicted = torch.max(outputs, 1)
            total += y_batch.size(0)
            correct += (predicted == y_batch).sum().item()
    test_rec_acc = correct / total
    print(f"Model 4 Val Loss: {best_rec_val_loss:.4f} | Test Accuracy: {test_rec_acc * 100:.2f}%")
    
    torch.save({
        'model_state_dict': model_rec.state_dict(),
        'test_acc': test_rec_acc
    }, 'checkpoints/model_4_recommender.pt')
    
    # Output metrics reports
    metrics = {
        'classifier_val_loss': float(best_val_loss),
        'classifier_test_acc': float(test_acc),
        'anomaly_val_loss': float(best_ae_val_loss),
        'anomaly_threshold': float(anomaly_threshold),
        'anomaly_val_f1': float(f1),
        'predictor_val_loss': float(best_ts_val_loss),
        'predictor_test_mae': float(test_mae),
        'recommender_val_loss': float(best_rec_val_loss),
        'recommender_test_acc': float(test_rec_acc)
    }
    with open('checkpoints/training_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)

if __name__ == '__main__':
    main()
