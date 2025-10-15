import os
import time
import tempfile
import base64
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from nudenet import NudeDetector
from typing import Optional
from pathlib import Path
from cryptography.fernet import Fernet
import pytesseract

# --- CORRECTED: Point directly to the Tesseract-OCR folder ---
ROOT_PROJECT_DIR = Path(__file__).parent.resolve()
TESSERACT_DIR = ROOT_PROJECT_DIR / "Tesseract-OCR"  # Use the correct folder name
pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_DIR / "tesseract.exe")

# This is the crucial line that tells pytesseract where the 'tessdata' is
TESSDATA_CONFIG = f'--tessdata-dir "{str(TESSERACT_DIR / "tessdata")}"'
# --- END CORRECTION ---

# --- Configuration ---
APP_DIR = Path(os.getenv("PROGRAMDATA", "C:\\ProgramData")) / "AntiWebNSFW"
APP_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR = APP_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = APP_DIR / "config.json"
KEY_PATH = APP_DIR / "key.bin"
LOCK_STATE_PATH = APP_DIR / "lock_state.json"

detector = NudeDetector(str(MODEL_DIR))

if not KEY_PATH.exists():
    key = Fernet.generate_key()
    KEY_PATH.write_bytes(key)
else:
    key = KEY_PATH.read_bytes()
fernet = Fernet(key)

default_cfg = {"expiry_ts": int(time.time()) + 365*24*3600, "nsfw_threshold": 0.5, "nsfw_classes": []}

def read_config():
    if not CONFIG_PATH.exists():
        save_config(default_cfg)
        return default_cfg
    try:
        enc = CONFIG_PATH.read_bytes()
        data = json.loads(fernet.decrypt(enc).decode())
        return data
    except Exception:
        return default_cfg

def save_config(cfg):
    CONFIG_PATH.write_bytes(fernet.encrypt(json.dumps(cfg).encode()))

def read_lock_state():
    if LOCK_STATE_PATH.exists() and LOCK_STATE_PATH.stat().st_size > 0:
        return json.loads(LOCK_STATE_PATH.read_text())
    return {"locked_until": 0}

def save_lock_state(state):
    LOCK_STATE_PATH.write_text(json.dumps(state))

cfg = read_config()
app = FastAPI()

class AnalyzeRequest(BaseModel):
    text: Optional[str] = None
    image_base64: Optional[str] = None

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    if req.text:
        txt = req.text.lower()
        for w in ["porn","sex","xxx","nude","hentai","erotic"]:
            if f" {w} " in f" {txt} ":
                return {"nsfw": True, "reason": "explicit_word", "word": w}
    if req.image_base64:
        try:
            b = base64.b64decode(req.image_base64.split(",",1)[-1])
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(b)
                tmp_path = tmp.name
            
            detections = detector.detect(tmp_path)
            
            # --- ADDED OCR SCANNING LOGIC ---
            text_from_image = pytesseract.image_to_string(tmp_path)
            if any(w in text_from_image.lower() for w in ["porn","sex","xxx","nude","hentai","erotic"]):
                os.unlink(tmp_path)
                return {"nsfw": True, "reason": "explicit_word_in_image"}
            # --- END ADDED LOGIC ---

            os.unlink(tmp_path)
            
            for d in detections:
                if d["class"].upper() in [c.upper() for c in cfg.get("nsfw_classes", [])] and d["score"]>=cfg.get("nsfw_threshold",0.5):
                    return {"nsfw": True, "reason": d["class"], "score": d["score"], "detections": detections}
            return {"nsfw": False, "detections": detections}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {"nsfw": False}

@app.post("/lock")
def lock_for(hours: int = 1):
    now = int(time.time())
    locked_until = now + int(hours*3600)
    state = {"locked_until": locked_until}
    save_lock_state(state)
    return {"locked_until": locked_until}

@app.get("/status")
def status():
    return read_lock_state()

if __name__ == "__main__":
    print("Detector initialized. If this is the first run, it will download the model.")
    print("Once the download is complete, you can stop this script with Ctrl+C.")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)