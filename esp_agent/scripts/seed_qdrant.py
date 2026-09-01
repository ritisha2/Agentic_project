import os
import glob
import json
import uuid
import hashlib
import math
import urllib.request
import urllib.error

QDRANT_HOST = os.getenv('QDRANT_HOST', 'http://localhost:6333')
COLLECTION_NAME = 'esp_kb'
VECTOR_DIM = 768

def create_collection():
    url = f'{QDRANT_HOST}/collections/{COLLECTION_NAME}'
    payload = {'vectors': {'size': VECTOR_DIM, 'distance': 'Cosine'}}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='PUT'
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(f'[+] Created/verified Qdrant collection: {COLLECTION_NAME}')
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if 'already exists' in body.lower():
            print(f'[*] Collection {COLLECTION_NAME} already exists.')
            return True
        print(f'[-] HTTP error creating collection: {e.code} - {body}')
        return False
    except Exception as e:
        print(f'[-] Failed to connect to Qdrant: {e}')
        return False

def collect_chunks():
    chunks = []
    root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
    base_kb = os.path.join(root_dir, 'esp_agent', 'knowledge_bases', 'esp', 'documents')
    if os.path.exists(base_kb):
        for fpath in glob.glob(os.path.join(base_kb, '*.txt')):
            fname = os.path.basename(fpath)
            doc_type = 'troubleshooting' if 'troubleshoot' in fname else ('maintenance_sop' if 'sop' in fname or 'maint' in fname else 'manual')
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            paras = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 30]
            for idx, p in enumerate(paras):
                chunks.append({
                    'id': f'{fname}_{idx}',
                    'title': fname.replace('.txt', '').replace('_', ' ').title(),
                    'doc_type': doc_type,
                    'source': fname,
                    'text': p
                })

    expert_points = [
        ('sop_gas_interference', 'Gas Interference SOP', 'When intake pressure fluctuates with motor current drop, increase intake pressure by choking back or reduce VSD frequency by 2-4 Hz to clear gas pocket.', 'troubleshooting'),
        ('sop_underload_trip', 'Underload Trip Response SOP', 'Check for broken shaft, dry well pump-off, or gas lock. Verify fluid level and PIP before attempting restart.', 'maintenance_sop'),
        ('sop_thermal_elevation', 'Motor Thermal Elevation Limit SOP', 'Max allowable motor temperature is 120°C for Class F insulation. Immediate trip threshold is 140°C.', 'maintenance_sop'),
        ('sop_vibration_limits', 'ISO 10816 Vibration Severity Limits', 'Good: < 0.18 G rms, Alert/Caution: 0.18 - 0.28 G rms, Critical Trip: > 0.35 G rms indicating severe mechanical bearing wear.', 'maintenance_sop'),
        ('rules_torque_proxy', 'Torque Proxy Physics Derivation', 'Torque proxy tau = I / f (Current / Frequency). An increase above 3.5 A/Hz indicates fluid viscosity rise, scale buildup, or mechanical drag.', 'rules')
    ]

    for kid, title, text, dtype in expert_points:
        chunks.append({
            'id': kid,
            'title': title,
            'doc_type': dtype,
            'source': 'field_sop_playbook.md',
            'text': text
        })
    return chunks

def seed_qdrant():
    if not create_collection():
        return
    chunks = collect_chunks()
    points = []
    for c in chunks:
        text = c['text']
        h = hashlib.sha256(text.encode()).digest()
        vec = [math.sin(h[i % len(h)] + i * 0.1) for i in range(VECTOR_DIM)]
        norm = math.sqrt(sum(x*x for x in vec)) or 1.0
        vec = [round(x/norm, 6) for x in vec]
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, c['id']))
        points.append({
            'id': point_id,
            'vector': vec,
            'payload': {
                'knowledge_id': c['id'],
                'title': c['title'],
                'doc_type': c['doc_type'],
                'source_file': c['source'],
                'text': c['text'],
                'category': 'ESP_KNOWLEDGE_BASE'
            }
        })

    upload_req = urllib.request.Request(
        f'{QDRANT_HOST}/collections/{COLLECTION_NAME}/points?wait=true',
        data=json.dumps({'points': points}).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='PUT'
    )
    try:
        with urllib.request.urlopen(upload_req) as resp:
            print(f'[+] Successfully seeded {len(points)} knowledge points to Qdrant ({COLLECTION_NAME})')
    except Exception as e:
        print(f'[-] Error uploading points: {e}')

if __name__ == '__main__':
    seed_qdrant()
