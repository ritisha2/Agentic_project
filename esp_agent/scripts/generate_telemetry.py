import os
import random
from datetime import datetime, timedelta
import pandas as pd

def generate_esp_telemetry(output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    start_time = datetime(2026, 1, 1, 0, 0, 0)
    asset_id = "ESP-Well-001"
    
    records = []
    
    interval_minutes = 10
    total_steps = (30 * 24 * 60) // interval_minutes
    
    for step in range(total_steps):
        curr_time = start_time + timedelta(minutes=step * interval_minutes)
        day_offset = step * interval_minutes / (24 * 60)
        
        # Default normal ranges
        motor_temp = round(random.uniform(85.0, 115.0), 2)
        intake_press = round(random.uniform(250.0, 450.0), 2)
        discharge_press = round(random.uniform(800.0, 1200.0), 2)
        motor_curr = round(random.uniform(50.0, 70.0), 2)
        radial_vib = round(random.uniform(0.6, 1.4), 2)
        axial_vib = round(random.uniform(0.2, 0.8), 2)
        flow_rate = round(random.uniform(2500.0, 3500.0), 2)
        efficiency = round(random.uniform(75.0, 88.0), 2)
        
        # Day 21 to Day 23: Overheating anomaly
        if 21 <= day_offset < 24:
            motor_temp = round(random.uniform(135.0, 145.0), 2)
            efficiency = round(random.uniform(60.0, 70.0), 2)
            
        # Day 24 to Day 26: Vibration anomaly
        elif 24 <= day_offset < 27:
            radial_vib = round(random.uniform(3.2, 4.0), 2)
            axial_vib = round(random.uniform(1.6, 2.2), 2)

        # Day 27 to 30: Returns to normal operation
        records.append({
            "timestamp": curr_time.isoformat(),
            "asset_id": asset_id,
            "motor_temperature": motor_temp,
            "intake_pressure": intake_press,
            "discharge_pressure": discharge_press,
            "motor_current": motor_curr,
            "radial_vibration": radial_vib,
            "axial_vibration": axial_vib,
            "flow_rate": flow_rate,
            "efficiency": efficiency
        })
        
    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} telemetry rows at {output_path}")

if __name__ == "__main__":
    generate_esp_telemetry("knowledge_bases/esp/telemetry/esp_telemetry.csv")
