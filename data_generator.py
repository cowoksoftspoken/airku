import numpy as np
import pandas as pd
import json
import os

def generate_synthetic_data(num_samples=50000, num_anomalies=2000, seed=42):
    np.random.seed(seed)
    
    # 1. Base time variables
    minutes = np.arange(num_samples)
    hours = (minutes // 60) % 24
    days = (minutes // (60 * 24)) % 7
    
    # Cyclical encoding
    hour_sin = np.sin(2 * np.pi * hours / 24.0)
    hour_cos = np.cos(2 * np.pi * hours / 24.0)
    day_sin = np.sin(2 * np.pi * days / 7.0)
    day_cos = np.cos(2 * np.pi * days / 7.0)
    
    # 2. Temperature and Humidity simulation
    # Base diurnal cycles
    temp_base = 25.0 + 8.0 * np.sin(2 * np.pi * (hours - 8) / 24.0)
    humidity_base = 65.0 - 25.0 * np.sin(2 * np.pi * (hours - 8) / 24.0)
    
    # Add noise
    temp = temp_base + np.random.normal(0, 0.5, num_samples)
    humidity = humidity_base + np.random.normal(0, 2.0, num_samples)
    temp = np.clip(temp, 15.0, 45.0)
    humidity = np.clip(humidity, 20.0, 95.0)
    
    # 3. Baseline MQ-135 raw sensor simulator
    # Gas base level depends on diurnal cycle and weekday/weekend
    gas_base = np.zeros(num_samples)
    for i in range(num_samples):
        h = hours[i]
        d = days[i]
        is_weekend = d >= 5
        
        # Diurnal pattern
        # Night (22:00-05:00): lower activity, lower base
        if h >= 22 or h < 5:
            base = 600.0
        # Morning peak (06:00-09:00): people waking up, commuting
        elif 6 <= h < 9:
            base = 1200.0 if not is_weekend else 800.0
        # Cooking peak 1 (11:00-13:00)
        elif 11 <= h < 13:
            base = 1500.0
        # Cooking peak 2 (17:00-19:00)
        elif 17 <= h < 19:
            base = 1800.0
        else:
            base = 900.0
            
        # Hot + humid dispersion: temp > 32 and humidity > 80 accelerates dispersion
        if temp[i] > 32.0 and humidity[i] > 80.0:
            base *= 0.7  # Gas disperses 30% faster
            
        gas_base[i] = base
        
    # Add noise
    mq135_raw = gas_base + np.random.normal(0, 30.0, num_samples)
    mq135_raw = np.clip(mq135_raw, 300.0, 4095.0).astype(int)
    
    # 4. Calibration: MQ-135 raw to PPM
    # Rs_Ro = (4095 - adc) / adc
    # ppm = 400 * (Rs_Ro) ^ -1.2
    # To avoid division by zero:
    adc_val = np.clip(mq135_raw, 1, 4094)
    rs_ro = (4095.0 - adc_val) / adc_val
    mq135_ppm = 400.0 * np.power(rs_ro + 1e-5, -1.2)
    mq135_ppm = np.clip(mq135_ppm, 350.0, 6000.0)
    
    # 5. Anomaly simulation
    # Anomaly events: sudden 3x spike lasting 5-15 mins
    anomaly_labels = np.zeros(num_samples, dtype=int)
    anomaly_indices = np.random.choice(np.arange(60, num_samples - 60), num_anomalies, replace=False)
    
    for idx in anomaly_indices:
        duration = np.random.randint(5, 16)
        # 3x spike in raw value (capped at 4095)
        spike_multiplier = np.random.uniform(2.5, 3.5)
        mq135_raw[idx : idx + duration] = np.clip(mq135_raw[idx : idx + duration] * spike_multiplier, 300, 4095)
        # Update PPM for anomaly window
        adc_segment = np.clip(mq135_raw[idx : idx + duration], 1, 4094)
        rs_ro_segment = (4095.0 - adc_segment) / adc_segment
        mq135_ppm[idx : idx + duration] = np.clip(400.0 * np.power(rs_ro_segment + 1e-5, -1.2), 350.0, 6000.0)
        anomaly_labels[idx : idx + duration] = 1

    # 6. Calculate ground truth AQI
    # Simple physical-chemical approximation mapping PPM to AQI
    # Class 0: Baik (AQI 0-50), Class 1: Sedang (AQI 51-100), Class 2: Tidak Sehat (AQI 101-150), Class 3: Berbahaya (151+)
    # Clean air PPM is ~400. Let's define AQI as:
    aqi_base = (mq135_ppm - 350.0) / 12.0
    # Add temperature & humidity effects on air quality perception
    temp_effect = np.maximum(0.0, temp - 30.0) * 1.5
    humid_effect = np.maximum(0.0, humidity - 70.0) * 0.5
    aqi = aqi_base + temp_effect + humid_effect + np.random.normal(0, 2.0, num_samples)
    aqi = np.clip(aqi, 0.0, 500.0)
    
    # 7. Compute rolling averages
    # Convert to pandas series for rolling calculations
    aqi_series = pd.Series(aqi)
    aqi_rolling_1h = aqi_series.rolling(window=60, min_periods=1).mean().values
    aqi_rolling_6h = aqi_series.rolling(window=360, min_periods=1).mean().values
    
    # Calculate classes based on current AQI
    aqi_class = np.zeros(num_samples, dtype=int)
    aqi_class[aqi > 50.0] = 1
    aqi_class[aqi > 100.0] = 2
    aqi_class[aqi > 150.0] = 3
    
    # 8. Create DataFrame
    df = pd.DataFrame({
        'temperature': temp,
        'humidity': humidity,
        'mq135_raw': mq135_raw,
        'mq135_ppm': mq135_ppm,
        'hour_of_day_sin': hour_sin,
        'hour_of_day_cos': hour_cos,
        'aqi_rolling_1h': aqi_rolling_1h,
        'aqi_rolling_6h': aqi_rolling_6h,
        'hour_of_day': hours,
        'day_of_week': days,
        'aqi': aqi,
        'aqi_class': aqi_class,
        'anomaly': anomaly_labels
    })
    
    # 9. Recommendation labels mapping
    # Inputs for Model 4: aqi_class (0-3), anomaly (0-1), trend (aqi_rolling_1h - aqi_rolling_6h), hour_of_day (0-23)
    # Target: 0 to 7 recommendation classes
    # 0 = open_window, 1 = close_window, 2 = use_air_purifier, 3 = avoid_outdoor, 
    # 4 = safe_outdoor, 5 = reduce_cooking, 6 = check_ventilation, 7 = all_clear
    
    # Generate recommendations rule-based for training
    trend = df['aqi_rolling_1h'] - df['aqi_rolling_6h']
    recs = np.zeros(num_samples, dtype=int)
    
    for i in range(num_samples):
        ac = aqi_class[i]
        anom = anomaly_labels[i]
        tr = trend[i]
        h = hours[i]
        
        # If hazardous, avoid outdoor and close window/purifier
        if ac == 3:
            recs[i] = 3 # avoid_outdoor
        elif anom == 1:
            recs[i] = 2 # use_air_purifier (immediate anomaly / spike)
        elif ac == 2:
            recs[i] = 1 # close_window (unhealthy outdoors/indoors)
        elif ac == 1:
            if tr > 5.0: # AQI rising rapidly
                recs[i] = 2 # use_air_purifier
            else:
                recs[i] = 6 # check_ventilation
        else: # ac == 0 (Baik)
            if 11 <= h < 13 or 17 <= h < 19:
                recs[i] = 5 # reduce_cooking (active hours)
            elif tr < -5.0: # quality improving
                recs[i] = 0 # open_window
            elif h >= 22 or h < 5:
                recs[i] = 7 # all_clear
            else:
                recs[i] = 4 # safe_outdoor
                
        # Inject 5% random label noise to prevent 100% deterministic target leakage
        if np.random.rand() < 0.05:
            recs[i] = np.random.randint(0, 8)
                
    df['recommendation'] = recs
    return df

if __name__ == '__main__':
    print("Generating synthetic data...")
    df = generate_synthetic_data()
    print("Data summary:")
    print(df['aqi_class'].value_counts())
    print("Anomaly counts:", df['anomaly'].sum())
    print("Recommendation distribution:")
    print(df['recommendation'].value_counts())
    
    # Save to workspace
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/air_quality_dataset.csv', index=False)
    print("Dataset saved to data/air_quality_dataset.csv")
