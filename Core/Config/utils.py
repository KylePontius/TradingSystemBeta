import json
import hashlib

def spec_hash(spec) -> str:
    payload = json.dumps(spec.identity(), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:10]