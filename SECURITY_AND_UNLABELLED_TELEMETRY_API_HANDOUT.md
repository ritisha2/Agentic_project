# 🔐 Security & Access Guide: Unlabelled Telemetry Polling API
**Version:** 1.0.0 | **Author:** ESP APM Infrastructure Team | **Target Audience:** Machine Learning & Model Evaluation Engineers

---

## 📋 1. Overview & Purpose

The **Unlabelled Telemetry Polling API** provides a secure, high-throughput, non-blocking interface for machine learning teams to extract, evaluate, and benchmark predictive AI models against real-time sensor telemetry.

All data served by this API is **pure unlabelled sensor time-series** coming from the live MQTT equity broker injection into `unlabelled.db` (2.68M+ records and continuously streaming), containing the **14 standard Variable Frequency Drive (VFD) and downhole sensor channels**.

---

## 🌐 2. Network Access & Base URLs

The backend server is accessible over the local office network and VPN on port **`8000`**:

| Target Environment | Base URL | Interactive Swagger Docs |
|---|---|---|
| **Local Machine** | `http://localhost:8000` | `http://localhost:8000/docs#/ML%20Telemetry` |
| **Network / LAN** | `http://192.168.1.188:8000` | `http://192.168.1.188:8000/docs#/ML%20Telemetry` |

> [!NOTE]
> If your workstation cannot reach `http://192.168.1.188:8000`, ensure your device is connected to the same subnet/Wi-Fi or ask the host to allow inbound TCP traffic on port `8000` via Windows Firewall.

---

## 🔑 3. Authentication & Security Credentials

Access requires a registered **Broker ID** passed in the HTTP request headers.

### Request Headers
```http
X-Broker-ID: <AUTHORIZED_BROKER_ID>
X-API-Key: <OPTIONAL_SECURITY_TOKEN>
```

### Pre-Authorized Broker IDs for ML Teams
| Broker ID | Environment / Permission Tier | Notes |
|---|---|---|
| **`BROKER-DEMO-001`** | Development & Evaluation | Default demo credentials for sandbox testing |
| **`CCED-ML-TEST-01`** | ML Model Benchmarking | Full read access to live streaming unlabelled.db |
| **`OPG-SECURE-01`** | Production Audit Tier | High-throughput batch queries |
| **`OPG-BROKER-PROD`** | Production Stream Tier | Field-level telemetry access |

*(Any custom Broker ID starting with `BROKER-` or `DEMO-` is also accepted for sandbox automation).*

---

## 📡 4. Available Endpoints

### 1. `GET /api/v1/telemetry/unlabelled` (Polling & Single-Asset Extraction)
Extracts chronological time-series records for all wells or a specific asset directly from `unlabelled.db`.

#### Query Parameters:
| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `asset_id` | `string` | No | `null` | Filter by well name (e.g. `FS-031`, `FSWS-001-A`). If omitted, returns all fleet records. |
| `start_time` | `ISO8601` | No | `null` | Filter records on or after timestamp (e.g. `2026-08-31T00:00:00Z`). |
| `end_time` | `ISO8601` | No | `null` | Filter records on or before timestamp. |
| `limit` | `integer` | No | `500` | Max records per response (min: `1`, max: `10,000`). |
| `offset` | `integer` | No | `0` | Pagination offset index. |
| `format` | `string` | No | `standard` | `standard` (nested JSON list) or `tabular` (flat column vectors for Pandas/NumPy). |

---

### 2. `POST /api/v1/telemetry/unlabelled/query` (Batch Multi-Asset Extraction)
Batch query endpoint accepting multiple asset IDs and timestamp windows in a JSON body.

#### Request Body Example:
```json
{
  "asset_ids": ["FS-031", "FSWS-001-A", "FS-010"],
  "start_time": "2026-08-30T00:00:00Z",
  "end_time": "2026-08-31T23:59:59Z",
  "limit": 500,
  "offset": 0
}
```

---

## 📊 5. The 14 Standard Telemetry Channels

Every returned record contains the normalized 14-parameter vector:

| # | Parameter Key | Physical Meaning | Engineering Unit |
|:---:|---|---|:---:|
| 1 | `intake_pressure_psi` | Pump Intake Pressure (PIP / Inp) | `psi` |
| 2 | `intake_temperature_c` | Downhole Intake Fluid Temperature | `°C` |
| 3 | `motor_temperature_c` | ESP Motor Internal Temperature | `°C` |
| 4 | `discharge_pressure_psi` | Pump Discharge Pressure (PDP / Disch) | `psi` |
| 5 | `vibration_g` | Radial Vibration (X-axis RMS) | `g` |
| 6 | `leak_current_ct` | Motor Insulation Leakage Current | `mA` |
| 7 | `motor_voltage_v` | VFD Bus Output Voltage | `V` |
| 8 | `motor_current_a` | VFD Operating Phase Current (Amps / Load) | `A` |
| 9 | `frequency_hz` | Operating Drive Frequency | `Hz` |
| 10 | `dhg_current` | Downhole Gauge Communication Current | `mA` |
| 11 | `whp_psi` | Wellhead Surface Pressure (WHP) | `psi` |
| 12 | `flp_psi` | Flowline Surface Pressure (FLP) | `psi` |
| 13 | `annulus_pressure_psi` | Casing / Annulus Pressure (AP) | `psi` |
| 14 | `vfd_status` | VFD Operating Status (`1` = Running, `0` = Stopped) | `binary flag` |

---

## 📦 6. Response Formats & Envelope

### Standard Format (`format=standard` — Default)
```json
{
  "status": "SUCCESS",
  "code": 200,
  "broker_id": "BROKER-DEMO-001",
  "source_db": "unlabelled.db",
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total_returned": 20,
    "total_records": 2685771,
    "has_more": true
  },
  "data": [
    {
      "id": 2685770,
      "timestamp": "2026-08-31T07:13:11.751588Z",
      "asset_id": "FS-031 [B400-1050 (204ST/42HP)]",
      "well_id": "FS-031",
      "parameters": {
        "intake_pressure_psi": 237.8575,
        "intake_temperature_c": 79.3752,
        "motor_temperature_c": 79.3752,
        "discharge_pressure_psi": 1878.0241,
        "vibration_g": 0.1845,
        "leak_current_ct": 0.0,
        "motor_voltage_v": 1009.5998,
        "motor_current_a": 18.9769,
        "frequency_hz": 45.9864,
        "dhg_current": 0.0,
        "whp_psi": 0.0,
        "flp_psi": 0.0,
        "annulus_pressure_psi": 0.0,
        "vfd_status": 1
      }
    }
  ],
  "error": null
}
```

---

## 💻 7. Integration Code Samples

### Python 3 + Pandas (1-Line ML Ingestion)
```python
import requests
import pandas as pd

API_URL = "http://192.168.1.188:8000/api/v1/telemetry/unlabelled"
HEADERS = {"X-Broker-ID": "CCED-ML-TEST-01"}

# Request 5,000 tabular records for model evaluation
params = {
    "asset_id": "FS-031",
    "format": "tabular",
    "limit": 5000
}

response = requests.get(API_URL, headers=HEADERS, params=params)
payload = response.json()

# Instantly construct Pandas DataFrame
df = pd.DataFrame(payload["data"])
print(f"Loaded {len(df)} telemetry rows across {len(df.columns)} columns.")
print(df[["timestamp", "intake_pressure_psi", "discharge_pressure_psi", "motor_current_a"]].head())
```

### cURL Extraction Command
```bash
curl -s -H "X-Broker-ID: BROKER-DEMO-001" \
  "http://192.168.1.188:8000/api/v1/telemetry/unlabelled?asset_id=FS-031&limit=10"
```

---

## 🛑 8. Error Codes & Troubleshooting

| HTTP Status | Error Code | Root Cause & Resolution |
|---|---|---|
| **`401 Unauthorized`** | `MISSING_BROKER_ID` | Request header `X-Broker-ID` is missing. Provide `X-Broker-ID: BROKER-DEMO-001`. |
| **`403 Forbidden`** | `UNAUTHORIZED_BROKER` | The supplied Broker ID is not in the authorized whitelist. |
| **`503 Service Unavailable`** | `DATABASE_UNAVAILABLE` | The SQLite database `unlabelled.db` is uninitialized or inaccessible on host. |
