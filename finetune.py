"""
finetune.py
-----------
Fine-tunes all 4 AirKu PyTorch models from their existing checkpoints using
the real preprocessed dataset (data/air_quality_real.csv).

Key differences from train.py:
  - Lower LR (1e-5) to prevent catastrophic forgetting
  - Fewer epochs (20)
  - Class-weighted CrossEntropyLoss for imbalanced real data
  - Batch-level noise augmentation (sigma=0.005)
  - Saves to *_finetuned.pt - never overwrites originals
  - Side-by-side before/after metrics summary
"""

import os
import json
import math
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from imblearn.over_sampling import SMOTE
from models import AQIClassifier, AnomalyDetector, AQIPredictor, AQIRecommender

# ---------------------------------------------------------------------------
# Hyperparameters
# ---------------------------------------------------------------------------
LR_FINETUNE = 1e-5
EPOCHS = 20
BATCH_SIZE = 128
SEQ_LEN = 12        # LSTM sequence length (must match train.py)
LEAD_TIME = 60      # prediction lead-time in timesteps (must match train.py)
SEED = 42

torch.manual_seed(SEED)
np.random.seed(SEED)


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

class AirKuDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        dtype = (torch.float32
                 if (len(y.shape) > 1 and y.shape[1] == 1)
                 else torch.long)
        self.y = torch.tensor(y, dtype=dtype)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


class TimeSeriesDataset(Dataset):
    def __init__(self, data, target, seq_len=SEQ_LEN, lead_time=LEAD_TIME):
        self.data = torch.tensor(data, dtype=torch.float32)
        self.target = torch.tensor(target, dtype=torch.float32)
        self.seq_len = seq_len
        self.lead_time = lead_time

    def __len__(self):
        return max(0, len(self.data) - self.seq_len - self.lead_time + 1)

    def __getitem__(self, idx):
        x = self.data[idx: idx + self.seq_len]
        y = self.target[idx + self.seq_len - 1 + self.lead_time]
        return x, y.unsqueeze(0)


# ---------------------------------------------------------------------------
# Augmentation
# ---------------------------------------------------------------------------

def augment_batch(x: torch.Tensor) -> torch.Tensor:
    """Very small Gaussian noise (0.5 %) to regularise fine-tuning."""
    noise = torch.randn_like(x) * 0.005
    return x + noise


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def finetune_model(
    model,
    train_loader,
    val_loader,
    criterion,
    optimizer,
    device,
    epochs=EPOCHS,
    is_reconstruction=False,
    use_augment=True,
):
    best_loss = float("inf")
    best_weights = None

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            if use_augment:
                X_batch = augment_batch(X_batch)
            optimizer.zero_grad()
            outputs = model(X_batch)
            target = X_batch if is_reconstruction else y_batch
            loss = criterion(outputs, target)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * X_batch.size(0)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                outputs = model(X_batch)
                target = X_batch if is_reconstruction else y_batch
                loss = criterion(outputs, target)
                val_loss += loss.item() * X_batch.size(0)

        epoch_val_loss = val_loss / max(1, len(val_loader.dataset))
        if epoch_val_loss < best_loss:
            best_loss = epoch_val_loss
            best_weights = {k: v.clone() for k, v in model.state_dict().items()}

        if (epoch + 1) % 5 == 0 or epoch == 0:
            epoch_train_loss = train_loss / max(1, len(train_loader.dataset))
            print(f"    Epoch [{epoch+1:2d}/{epochs}] "
                  f"train_loss={epoch_train_loss:.5f}  val_loss={epoch_val_loss:.5f}")

    if best_weights is not None:
        model.load_state_dict(best_weights)
    return best_loss


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def eval_accuracy(model, loader, device):
    model.eval()
    correct, total = 0, 0
    with torch.no_grad():
        for X_batch, y_batch in loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            outputs = model(X_batch)
            _, predicted = torch.max(outputs, 1)
            total += y_batch.size(0)
            correct += (predicted == y_batch).sum().item()
    return correct / max(1, total)


def eval_recon_error(model, loader, device):
    model.eval()
    total_error, total = 0.0, 0
    with torch.no_grad():
        for X_batch, y_batch in loader:
            X_batch = X_batch.to(device)
            outputs = model(X_batch)
            errors = torch.mean((outputs - X_batch) ** 2, dim=1)
            total_error += errors.sum().item()
            total += X_batch.size(0)
    return total_error / max(1, total)


def eval_mae(model, loader, device, aqi_min, aqi_max):
    model.eval()
    mae_sum, total = 0.0, 0
    with torch.no_grad():
        for X_batch, y_batch in loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            outputs = model(X_batch)
            pred_rescaled = outputs * (aqi_max - aqi_min) + aqi_min
            true_rescaled = y_batch * (aqi_max - aqi_min) + aqi_min
            mae_sum += torch.abs(pred_rescaled - true_rescaled).sum().item()
            total += y_batch.size(0)
    return mae_sum / max(1, total)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("AirKu - Fine-tuning Pipeline")
    print("=" * 60)

    # GPU info
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    if device.type == "cuda":
        try:
            print(f"GPU: {torch.cuda.get_device_name(0)}")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Load real data
    # ------------------------------------------------------------------
    real_csv = "data/air_quality_real.csv"
    if not os.path.exists(real_csv):
        raise FileNotFoundError(
            f"{real_csv} not found. Run python data_preprocessor.py first."
        )

    df_real = pd.read_csv(real_csv)
    print(f"Loaded real data: {len(df_real):,} rows")

    # Read auto-detected interval from preprocessor output
    meta_path = "data/real_data_meta.json"
    interval_seconds = 60  # default for resampled
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        interval_seconds = int(meta.get("interval_seconds", 60))
    print(f"Dataset interval: {interval_seconds}s")

    # ------------------------------------------------------------------
    # Load scaler from original training (MUST use same normalisation)
    # ------------------------------------------------------------------
    scaler_path = "checkpoints/aqi_scaler.json"
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(
            "checkpoints/aqi_scaler.json not found. Run python train.py first."
        )
    with open(scaler_path) as f:
        scaler = json.load(f)

    min_vals = np.array(scaler["features_min"])
    max_vals = np.array(scaler["features_max"])
    rec_min = np.array(scaler["recommender_min"])
    rec_max = np.array(scaler["recommender_max"])
    aqi_min = float(scaler["aqi_min"])
    aqi_max = float(scaler["aqi_max"])

    # ------------------------------------------------------------------
    # Feature engineering (same as train.py)
    # ------------------------------------------------------------------
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

    y_aqi = df_real["aqi"].values
    y_aqi_scaled = (y_aqi - aqi_min) / (aqi_max - aqi_min + 1e-8)

    # ------------------------------------------------------------------
    # Stratified 70/15/15 split by aqi_class
    # ------------------------------------------------------------------
    indices = np.arange(len(df_real))
    train_idx, temp_idx = train_test_split(
        indices, test_size=0.30, stratify=df_real["aqi_class"].values, random_state=SEED
    )
    val_idx, test_idx = train_test_split(
        temp_idx, test_size=0.50, stratify=df_real["aqi_class"].values[temp_idx], random_state=SEED
    )

    print(f"Split: train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}")

    # ------------------------------------------------------------------
    # Load original checkpoints & compute BEFORE metrics
    # ------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("Computing BEFORE metrics from original checkpoints...")
    print("-" * 50)

    checkpoint_names = {
        1: "checkpoints/model_1_classifier.pt",
        2: "checkpoints/model_2_anomaly.pt",
        3: "checkpoints/model_3_predictor.pt",
        4: "checkpoints/model_4_recommender.pt",
    }
    finetuned_names = {
        1: "checkpoints/model_1_finetuned.pt",
        2: "checkpoints/model_2_finetuned.pt",
        3: "checkpoints/model_3_finetuned.pt",
        4: "checkpoints/model_4_finetuned.pt",
    }

    # -- Model 1 before ----------------------------------------------
    y_cls = df_real["aqi_class"].values
    val_cls_ds = AirKuDataset(X_scaled[val_idx], y_cls[val_idx])
    val_cls_loader = DataLoader(val_cls_ds, batch_size=BATCH_SIZE, shuffle=False)

    model1 = AQIClassifier().to(device)
    ckpt1 = torch.load(checkpoint_names[1], map_location=device)
    model1.load_state_dict(ckpt1["model_state_dict"])
    epoch_info = ckpt1.get("epoch", "N/A")
    val_loss_info = ckpt1.get("val_loss", ckpt1.get("classifier_val_loss", "N/A"))
    print(f"Loaded Model 1 checkpoint: epoch={epoch_info}, "
          f"stored_metric={val_loss_info}")
    before_m1_acc = eval_accuracy(model1, val_cls_loader, device)
    print(f"  Before val_acc: {before_m1_acc*100:.2f}%")

    # -- Model 2 before ----------------------------------------------
    train_normal_mask = df_real["anomaly"].values[train_idx] == 0
    X_train_normal = X_scaled[train_idx][train_normal_mask]
    val_ae_ds = AirKuDataset(X_scaled[val_idx], X_scaled[val_idx])
    val_ae_loader = DataLoader(val_ae_ds, batch_size=BATCH_SIZE, shuffle=False)

    model2 = AnomalyDetector().to(device)
    ckpt2 = torch.load(checkpoint_names[2], map_location=device)
    model2.load_state_dict(ckpt2["model_state_dict"])
    print(f"Loaded Model 2 checkpoint: epoch={ckpt2.get('epoch','N/A')}, "
          f"threshold={float(ckpt2.get('anomaly_threshold', 0)):.6f}")
    before_m2_err = eval_recon_error(model2, val_ae_loader, device)
    print(f"  Before recon_error: {before_m2_err:.6f}")

    # -- Model 3 before ----------------------------------------------
    # Adjust sequence lead_time for real data interval vs original (1-min synthetic)
    prediction_horizon_seconds = LEAD_TIME * 60
    real_lead_time = max(1, int(round(prediction_horizon_seconds / interval_seconds)))
    print(f"  LSTM lead_time: {real_lead_time} steps "
          f"(= {real_lead_time * interval_seconds}s ahead)")

    val_ts_ds = TimeSeriesDataset(X_scaled[val_idx], y_aqi_scaled[val_idx],
                                  seq_len=SEQ_LEN, lead_time=real_lead_time)
    val_ts_loader = DataLoader(val_ts_ds, batch_size=BATCH_SIZE, shuffle=False)

    model3 = AQIPredictor().to(device)
    ckpt3 = torch.load(checkpoint_names[3], map_location=device)
    model3.load_state_dict(ckpt3["model_state_dict"])
    print(f"Loaded Model 3 checkpoint: epoch={ckpt3.get('epoch','N/A')}, "
          f"stored_mae={ckpt3.get('test_mae', 'N/A')}")
    before_m3_mae = eval_mae(model3, val_ts_loader, device, aqi_min, aqi_max)
    print(f"  Before MAE: {before_m3_mae:.2f}")

    # -- Model 4 before ----------------------------------------------
    y_rec = df_real["recommendation"].values
    val_rec_ds = AirKuDataset(X_rec_scaled[val_idx], y_rec[val_idx])
    val_rec_loader = DataLoader(val_rec_ds, batch_size=BATCH_SIZE, shuffle=False)

    model4 = AQIRecommender().to(device)
    ckpt4 = torch.load(checkpoint_names[4], map_location=device)
    model4.load_state_dict(ckpt4["model_state_dict"])
    print(f"Loaded Model 4 checkpoint: epoch={ckpt4.get('epoch','N/A')}, "
          f"stored_metric={ckpt4.get('val_loss', ckpt4.get('test_acc', 'N/A'))}")
    before_m4_acc = eval_accuracy(model4, val_rec_loader, device)
    print(f"  Before val_acc: {before_m4_acc*100:.2f}%")

    # ------------------------------------------------------------------
    # Fine-tune Model 1: AQI Classifier
    # ------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("Fine-tuning Model 1: AQI Classifier (SMOTE Augmented)")
    print("-" * 50)

    y_train_cls = y_cls[train_idx]
    
    # Check minimum class size for SMOTE k_neighbors
    min_class_samples = np.min(np.bincount(y_train_cls))
    k_neighbors_cls = min(5, max(1, min_class_samples - 1))
    print(f"Applying SMOTE to Model 1 (k_neighbors={k_neighbors_cls})")
    smote_cls = SMOTE(k_neighbors=k_neighbors_cls, random_state=SEED)
    X_train_cls_sm, y_train_cls_sm = smote_cls.fit_resample(X_scaled[train_idx], y_train_cls)
    
    print(f"Original train size: {len(X_scaled[train_idx])}")
    print(f"Augmented train size: {len(X_train_cls_sm)}")

    # Class weights are 1.0 now since SMOTE perfectly balances them
    class_weights_cls = compute_class_weight(
        class_weight="balanced",
        classes=np.unique(y_train_cls_sm),
        y=y_train_cls_sm,
    )
    criterion_cls = nn.CrossEntropyLoss(
        weight=torch.FloatTensor(class_weights_cls).to(device)
    )
    optimizer1 = torch.optim.AdamW(model1.parameters(), lr=LR_FINETUNE, weight_decay=1e-4)

    train_cls_ds = AirKuDataset(X_train_cls_sm, y_train_cls_sm)
    train_cls_loader = DataLoader(train_cls_ds, batch_size=BATCH_SIZE, shuffle=True)

    finetune_model(model1, train_cls_loader, val_cls_loader,
                   criterion_cls, optimizer1, device)
    after_m1_acc = eval_accuracy(model1, val_cls_loader, device)
    print(f"  After val_acc: {after_m1_acc*100:.2f}%")

    torch.save({
        "model_state_dict": model1.state_dict(),
        "epoch": EPOCHS,
        "val_acc": after_m1_acc,
        "val_loss": float(criterion_cls(
            model1(torch.tensor(X_scaled[val_idx], dtype=torch.float32).to(device)),
            torch.tensor(y_cls[val_idx]).to(device)
        ).item()) if len(val_idx) > 0 else 0.0,
    }, finetuned_names[1])
    print(f"  [OK] Saved -> {finetuned_names[1]}")

    # ------------------------------------------------------------------
    # Fine-tune Model 2: Anomaly Detector (Autoencoder)
    # ------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("Fine-tuning Model 2: Anomaly Detector")
    print("-" * 50)

    criterion_ae = nn.MSELoss()
    optimizer2 = torch.optim.AdamW(model2.parameters(), lr=LR_FINETUNE, weight_decay=1e-4)

    train_ae_ds = AirKuDataset(X_train_normal, X_train_normal)
    train_ae_loader = DataLoader(train_ae_ds, batch_size=BATCH_SIZE, shuffle=True)

    finetune_model(model2, train_ae_loader, val_ae_loader,
                   criterion_ae, optimizer2, device,
                   is_reconstruction=True)
    after_m2_err = eval_recon_error(model2, val_ae_loader, device)
    print(f"  After recon_error: {after_m2_err:.6f}")

    # Recompute threshold on val set
    model2.eval()
    val_all_ds = AirKuDataset(X_scaled[val_idx], df_real["anomaly"].values[val_idx])
    val_all_loader = DataLoader(val_all_ds, batch_size=BATCH_SIZE, shuffle=False)
    recon_errors, val_anoms = [], []
    with torch.no_grad():
        for Xb, yb in val_all_loader:
            Xb = Xb.to(device)
            out = model2(Xb)
            err = torch.mean((out - Xb) ** 2, dim=1).cpu().numpy()
            recon_errors.extend(err)
            val_anoms.extend(yb.numpy())
    recon_errors = np.array(recon_errors)
    val_anoms = np.array(val_anoms)
    normal_errors = recon_errors[val_anoms == 0]
    new_threshold = float(np.percentile(normal_errors, 97.5)) if len(normal_errors) > 0 else float(ckpt2["anomaly_threshold"])

    torch.save({
        "model_state_dict": model2.state_dict(),
        "epoch": EPOCHS,
        "anomaly_threshold": new_threshold,
        "val_recon_error": after_m2_err,
    }, finetuned_names[2])
    print(f"  [OK] Saved -> {finetuned_names[2]}  (new threshold={new_threshold:.6f})")

    # ------------------------------------------------------------------
    # Fine-tune Model 3: AQI Predictor (LSTM)
    # ------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("Fine-tuning Model 3: AQI Predictor (LSTM)")
    print("-" * 50)

    criterion_ts = nn.HuberLoss()
    optimizer3 = torch.optim.AdamW(model3.parameters(), lr=LR_FINETUNE, weight_decay=1e-4)

    train_ts_ds = TimeSeriesDataset(X_scaled[train_idx], y_aqi_scaled[train_idx],
                                    seq_len=SEQ_LEN, lead_time=real_lead_time)
    train_ts_loader = DataLoader(train_ts_ds, batch_size=BATCH_SIZE, shuffle=True)

    finetune_model(model3, train_ts_loader, val_ts_loader,
                   criterion_ts, optimizer3, device, use_augment=True)
    after_m3_mae = eval_mae(model3, val_ts_loader, device, aqi_min, aqi_max)
    print(f"  After MAE: {after_m3_mae:.2f}")

    torch.save({
        "model_state_dict": model3.state_dict(),
        "epoch": EPOCHS,
        "val_mae": after_m3_mae,
        "sequence_interval_seconds": interval_seconds,
    }, finetuned_names[3])
    print(f"  [OK] Saved -> {finetuned_names[3]}")

    # ------------------------------------------------------------------
    # Fine-tune Model 4: Recommendation Engine
    # ------------------------------------------------------------------
    print("\n" + "-" * 50)
    print("Fine-tuning Model 4: Recommendation Engine (SMOTE Augmented)")
    print("-" * 50)

    y_train_rec = y_rec[train_idx]
    
    # Apply SMOTE
    min_rec_samples = np.min(np.bincount(y_train_rec))
    k_neighbors_rec = min(5, max(1, min_rec_samples - 1))
    print(f"Applying SMOTE to Model 4 (k_neighbors={k_neighbors_rec})")
    smote_rec = SMOTE(k_neighbors=k_neighbors_rec, random_state=SEED)
    X_train_rec_sm, y_train_rec_sm = smote_rec.fit_resample(X_rec_scaled[train_idx], y_train_rec)
    
    print(f"Original train size: {len(X_rec_scaled[train_idx])}")
    print(f"Augmented train size: {len(X_train_rec_sm)}")

    # Ensure all classes present for class_weight computation
    unique_classes = np.unique(y_train_rec_sm)
    class_weights_rec = compute_class_weight(
        class_weight="balanced",
        classes=unique_classes,
        y=y_train_rec_sm,
    )
    # Expand to full 8 classes if some are absent (shouldn't happen with SMOTE if all were in training data originally)
    full_weights = np.ones(8, dtype=np.float32)
    for ci, cw in zip(unique_classes, class_weights_rec):
        full_weights[int(ci)] = cw

    criterion_rec = nn.CrossEntropyLoss(
        weight=torch.FloatTensor(full_weights).to(device)
    )
    optimizer4 = torch.optim.AdamW(model4.parameters(), lr=LR_FINETUNE, weight_decay=1e-4)

    train_rec_ds = AirKuDataset(X_train_rec_sm, y_train_rec_sm)
    train_rec_loader = DataLoader(train_rec_ds, batch_size=BATCH_SIZE, shuffle=True)

    finetune_model(model4, train_rec_loader, val_rec_loader,
                   criterion_rec, optimizer4, device)
    after_m4_acc = eval_accuracy(model4, val_rec_loader, device)
    print(f"  After val_acc: {after_m4_acc*100:.2f}%")

    torch.save({
        "model_state_dict": model4.state_dict(),
        "epoch": EPOCHS,
        "val_acc": after_m4_acc,
    }, finetuned_names[4])
    print(f"  [OK] Saved -> {finetuned_names[4]}")

    # ------------------------------------------------------------------
    # Final Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 46)
    print("Fine-tuning Results Summary")
    print("=" * 46)
    print(f"Model 1 (Classifier):")
    print(f"  Before: val_acc = {before_m1_acc*100:.2f}%")
    print(f"  After:  val_acc = {after_m1_acc*100:.2f}%  <- should be >= 85%")
    print()
    print(f"Model 2 (Anomaly):")
    print(f"  Before: recon_error = {before_m2_err:.6f}")
    print(f"  After:  recon_error = {after_m2_err:.6f}")
    print()
    print(f"Model 3 (Predictor):")
    print(f"  Before: MAE = {before_m3_mae:.2f}")
    print(f"  After:  MAE = {after_m3_mae:.2f}  <- should be < 10")
    print()
    print(f"Model 4 (Recommender):")
    print(f"  Before: val_acc = {before_m4_acc*100:.2f}%")
    print(f"  After:  val_acc = {after_m4_acc*100:.2f}%  <- should be >= 80%")
    print("=" * 46)
    print("Fine-tuned checkpoints saved to checkpoints/*_finetuned.pt")
    print("Run export.py --finetuned to export updated TFLite models.")

    # Persist metrics
    ft_metrics = {
        "classifier_before_val_acc": float(before_m1_acc),
        "classifier_after_val_acc": float(after_m1_acc),
        "anomaly_before_recon_error": float(before_m2_err),
        "anomaly_after_recon_error": float(after_m2_err),
        "anomaly_new_threshold": float(new_threshold),
        "predictor_before_mae": float(before_m3_mae),
        "predictor_after_mae": float(after_m3_mae),
        "recommender_before_val_acc": float(before_m4_acc),
        "recommender_after_val_acc": float(after_m4_acc),
    }
    with open("checkpoints/finetune_metrics.json", "w") as f:
        json.dump(ft_metrics, f, indent=2)
    print("\n[OK] Fine-tune metrics saved -> checkpoints/finetune_metrics.json")


if __name__ == "__main__":
    main()
