"""
data_preprocessor.py
--------------------
Downloads the Figshare Indoor Air Quality dataset and preprocesses it into
the exact same feature format used by the synthetic training data.

Output: data/air_quality_real.csv
Columns (in order):
    temperature, humidity, mq135_raw, mq135_ppm,
    hour_of_day_sin, hour_of_day_cos,
    aqi_rolling_1h, aqi_rolling_6h,
    hour_of_day, day_of_week,
    aqi, aqi_class, anomaly, recommendation
"""

import os
import io
import math
import requests
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Figshare dataset info
# ---------------------------------------------------------------------------
FIGSHARE_ARTICLE_ID = 27280983
FIGSHARE_API_URL = f"https://api.figshare.com/v2/articles/{FIGSHARE_ARTICLE_ID}/files"

OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "air_quality_real.csv")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _download_csv_from_figshare() -> pd.DataFrame:
    """Fetch all file listings for the article and download the first CSV."""
    print(f"Fetching file list from Figshare article {FIGSHARE_ARTICLE_ID}...")
    resp = requests.get(FIGSHARE_API_URL, timeout=60)
    resp.raise_for_status()
    files = resp.json()

    csv_files = [f for f in files if f["name"].lower().endswith(".csv")]
    if not csv_files:
        raise RuntimeError("No CSV files found in Figshare article.")

    for file_info in csv_files:
        url = file_info["download_url"]
        name = file_info["name"]
        print(f"Downloading: {name}  ({file_info['size'] / 1024:.1f} KB)")
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        df = pd.read_csv(io.BytesIO(r.content), sep=";", decimal=",", on_bad_lines="skip")
        print(f"  -> Loaded {len(df):,} rows, columns: {list(df.columns)}")
        return df

    raise RuntimeError("Could not download any CSV from Figshare.")

# ---------------------------------------------------------------------------
# Main preprocessing pipeline
# ---------------------------------------------------------------------------

def preprocess(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Full preprocessing pipeline that converts raw Figshare data into the
    exact same column format as the synthetic training data.
    """
    
    # ------------------------------------------------------------------
    # Step 1: Load & map columns
    # ------------------------------------------------------------------
    df_raw.columns = [str(c).strip().lower() for c in df_raw.columns]

    col_map = {
        "temperature (°c)": "temperature",
        "temperature": "temperature",
        "humidity (%)": "humidity",
        "humidity": "humidity",
        "co2 (ppm)": "mq135_ppm",
        "co2": "mq135_ppm",
        "timestamp": "timestamp",
        "time": "timestamp",
    }

    rename = {}
    for raw_col in df_raw.columns:
        stripped = raw_col.strip().lower()
        if stripped in col_map:
            rename[raw_col] = col_map[stripped]
        elif "temperature" in stripped and "category" not in stripped:
            rename[raw_col] = "temperature"
        elif "humidity" in stripped and "category" not in stripped:
            rename[raw_col] = "humidity"
        elif "co2" in stripped and "category" not in stripped:
            rename[raw_col] = "mq135_ppm"
        elif stripped == "timestamp" or "time" in stripped:
            rename[raw_col] = "timestamp"

    df = df_raw.rename(columns=rename).copy()
    print(f"  Column mapping applied: {rename}")

    # Ensure timestamp exists for resampling
    has_timestamp = "timestamp" in df.columns
    if has_timestamp:
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed", errors="coerce")
        df = df.dropna(subset=["timestamp"])

    # ------------------------------------------------------------------
    # Step 3: Clip values to valid sensor ranges
    # ------------------------------------------------------------------
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce").clip(15.0, 45.0)
    df["humidity"] = pd.to_numeric(df["humidity"], errors="coerce").clip(20.0, 95.0)
    df["mq135_ppm"] = pd.to_numeric(df["mq135_ppm"], errors="coerce").clip(350.0, 6000.0)

    df.dropna(subset=["temperature", "humidity", "mq135_ppm"], inplace=True)

    # ------------------------------------------------------------------
    # Step 7 (Moved Up): Resample to 1-min interval (match data_generator.py)
    # ------------------------------------------------------------------
    if has_timestamp and len(df) > 0:
        print("  Resampling to 1-minute intervals...")
        df = df.set_index("timestamp")
        # Ensure we only resample numeric columns, avoid categorical warnings
        numeric_cols = ["temperature", "humidity", "mq135_ppm"]
        df = df[numeric_cols].resample("1min").mean().dropna().reset_index()
        df["hour_of_day"] = df["timestamp"].dt.hour.astype(int)
        df["day_of_week"] = df["timestamp"].dt.dayofweek.astype(int)
    else:
        print("  No valid timestamps, assuming 1-minute intervals for index...")
        minutes = df.index
        df["hour_of_day"] = (minutes // 60).astype(int) % 24
        df["day_of_week"] = (minutes // (60 * 24)).astype(int) % 7

    # ------------------------------------------------------------------
    # Step 4: Reconstruct mq135_raw from PPM (inverse MQ-135 formula)
    # ------------------------------------------------------------------
    ppm = df["mq135_ppm"].values
    rs_ro = np.power(400.0 / ppm, 1.0 / 1.2)
    adc = 4095.0 / (rs_ro + 1.0)
    df["mq135_raw"] = np.clip(adc, 300, 4095).astype(int)

    # ------------------------------------------------------------------
    # Step 5: Cyclical encoding
    # ------------------------------------------------------------------
    hours = df["hour_of_day"].values
    df["hour_of_day_sin"] = np.sin(2 * np.pi * hours / 24.0)
    df["hour_of_day_cos"] = np.cos(2 * np.pi * hours / 24.0)

    # ------------------------------------------------------------------
    # Step 6: AQI calculation
    # ------------------------------------------------------------------
    temp = df["temperature"].values
    humidity = df["humidity"].values
    mq135_ppm = df["mq135_ppm"].values

    aqi_base = (mq135_ppm - 350.0) / 12.0
    temp_effect = np.maximum(0.0, temp - 30.0) * 1.5
    humid_effect = np.maximum(0.0, humidity - 70.0) * 0.5
    np.random.seed(42)
    aqi = aqi_base + temp_effect + humid_effect + np.random.normal(0.0, 2.0, len(df))
    aqi = np.clip(aqi, 0.0, 500.0)
    df["aqi"] = aqi

    # ------------------------------------------------------------------
    # Step 7 (Rolling): Rolling averages (1h=60, 6h=360) match synthetic
    # ------------------------------------------------------------------
    window_1h = 60
    window_6h = 360
    
    aqi_series = pd.Series(aqi)
    df["aqi_rolling_1h"] = aqi_series.rolling(window=window_1h, min_periods=1).mean().values
    df["aqi_rolling_6h"] = aqi_series.rolling(window=window_6h, min_periods=1).mean().values

    # ------------------------------------------------------------------
    # Step 8: AQI class thresholds
    # ------------------------------------------------------------------
    aqi_class = np.zeros(len(df), dtype=int)
    aqi_class[aqi > 50.0] = 1
    aqi_class[aqi > 100.0] = 2
    aqi_class[aqi > 150.0] = 3
    df["aqi_class"] = aqi_class

    # ------------------------------------------------------------------
    # Step 9: Anomaly detection via z-score
    # ------------------------------------------------------------------
    mq135_raw_series = pd.Series(df["mq135_raw"].values.astype(float))
    rolling_mean = mq135_raw_series.rolling(window=20, min_periods=1).mean()
    rolling_std = mq135_raw_series.rolling(window=20, min_periods=1).std().fillna(1.0)
    z_score = (mq135_raw_series - rolling_mean) / rolling_std
    df["anomaly"] = (z_score.abs() > 3.0).astype(int)

    # ------------------------------------------------------------------
    # Step 10: Recommendation labels
    # ------------------------------------------------------------------
    trend = df["aqi_rolling_1h"].values - df["aqi_rolling_6h"].values
    recs = np.zeros(len(df), dtype=int)

    for i in range(len(df)):
        ac = int(df["aqi_class"].iloc[i])
        anom = int(df["anomaly"].iloc[i])
        tr = float(trend[i])
        h = int(df["hour_of_day"].iloc[i])

        if ac == 3:
            recs[i] = 3
        elif anom == 1:
            recs[i] = 2
        elif ac == 2:
            recs[i] = 1
        elif ac == 1:
            if tr > 5.0:
                recs[i] = 2
            else:
                recs[i] = 6
        else:
            if (11 <= h < 13) or (17 <= h < 19):
                recs[i] = 5
            elif tr < -5.0:
                recs[i] = 0
            elif h >= 22 or h < 5:
                recs[i] = 7
            else:
                recs[i] = 4

    df["recommendation"] = recs

    # ------------------------------------------------------------------
    # Assemble final DataFrame
    # ------------------------------------------------------------------
    final_cols = [
        "temperature", "humidity", "mq135_raw", "mq135_ppm",
        "hour_of_day_sin", "hour_of_day_cos",
        "aqi_rolling_1h", "aqi_rolling_6h",
        "hour_of_day", "day_of_week",
        "aqi", "aqi_class", "anomaly", "recommendation",
    ]
    df_out = df[final_cols].copy()

    df_out["mq135_raw"] = df_out["mq135_raw"].astype(int)
    df_out["aqi_class"] = df_out["aqi_class"].astype(int)
    df_out["anomaly"] = df_out["anomaly"].astype(int)
    df_out["recommendation"] = df_out["recommendation"].astype(int)
    df_out["hour_of_day"] = df_out["hour_of_day"].astype(int)
    df_out["day_of_week"] = df_out["day_of_week"].astype(int)

    return df_out


def main():
    print("=" * 60)
    print("AirKu - Real Data Preprocessor (1-min Resampled)")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    df_raw = _download_csv_from_figshare()

    print("\nRunning preprocessing pipeline...")
    df_out = preprocess(df_raw)

    df_out.to_csv(OUTPUT_FILE, index=False)
    print(f"\n[OK] Saved {len(df_out):,} rows -> {OUTPUT_FILE}")

    aqi_dist = df_out["aqi_class"].value_counts().sort_index().to_dict()
    rec_dist = df_out["recommendation"].value_counts().sort_index().to_dict()
    aqi_dist_full = {k: aqi_dist.get(k, 0) for k in range(4)}
    rec_dist_full = {k: rec_dist.get(k, 0) for k in range(8)}

    print("\n" + "-" * 50)
    print(f"Total rows     : {len(df_out):,}")
    print(f"AQI class dist : {aqi_dist_full}")
    print(f"Anomaly count  : {df_out['anomaly'].sum()}")
    print(f"Rec dist       : {rec_dist_full}")
    print(f"Interval       : 60s (fixed 1-min resampled)")
    print("-" * 50)

    import json
    meta = {"interval_seconds": 60}
    with open(os.path.join(OUTPUT_DIR, "real_data_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


if __name__ == "__main__":
    main()
