import subprocess
import time
import json
import os
import sys
import logging
import base64
from pathlib import Path
import psutil
import threading
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from nudenet import NudeDetector
from typing import Optional
import tempfile
from cryptography.fernet import Fernet
import pytesseract

# --- Configuration ---
# APP_DIR = Path(os.getenv("PROGRAMDATA", "C:\\ProgramData")) / "AntiWebNSFW"
# APP_DIR = Path(os.getenv("LOCALAPPDATA")) / "AntiWebNSFW"
APP_DIR = Path(__file__).parent.resolve() / "data"
APP_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR = APP_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

log_path = APP_DIR / "main_launcher.log"
logging.basicConfig(
    handlers=[logging.FileHandler(log_path, 'w', 'utf-8'), logging.StreamHandler()],
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# --- Tesseract Configuration ---
ROOT_PROJECT_DIR = Path(__file__).parent.resolve()
TESSERACT_DIR = ROOT_PROJECT_DIR / "Tesseract-OCR"
pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_DIR / "tesseract.exe")
TESSDATA_CONFIG = f'--tessdata-dir "{str(TESSERACT_DIR / "tessdata")}"'

# --- Paths ---
LOCK_STATE_PATH = APP_DIR / "lock_state.json"
KEY_PATH = APP_DIR / "key.bin"
CONFIG_PATH = APP_DIR / "config.json" # --- THIS WAS THE MISSING LINE ---
PYTHON_EXE = ROOT_PROJECT_DIR / "venv311" / "Scripts" / "python.exe"
UVICORN_EXE = ROOT_PROJECT_DIR / "venv311" / "Scripts" / "uvicorn.exe"
MITMDUMP_EXE = ROOT_PROJECT_DIR / "venv311" / "Scripts" / "mitmdump.exe"
OVERLAY_SCRIPT = ROOT_PROJECT_DIR / "overlay_lock.py"
PROXY_ADDON_SCRIPT = ROOT_PROJECT_DIR / "nsfw_proxy_addon.py"

# --- Initialize Detector ---
try:
    logging.info(f"Initializing NudeDetector from model path: {MODEL_DIR}")
    detector = NudeDetector(str(MODEL_DIR))
    logging.info("NudeDetector initialized successfully.")
except Exception as e:
    logging.critical(f"FATAL: Could not initialize NudeDetector. Error: {e}")
    sys.exit(1)

# --- FastAPI App & Helper Functions (Merged from detector_service.py) ---
app = FastAPI()

if not KEY_PATH.exists(): key = Fernet.generate_key(); KEY_PATH.write_bytes(key)
else: key = KEY_PATH.read_bytes()
fernet = Fernet(key)

# --- THESE HELPER FUNCTIONS WERE ALSO MISSING ---
default_cfg = {"expiry_ts": int(time.time()) + 365*24*3600, "nsfw_threshold": 0.5, "nsfw_classes": ["FEMALE_GENITALIA_EXPOSED", "FEMALE_BREAST_EXPOSED", "BUTTOCKS_EXPOSED", "ANUS_EXPOSED", "MALE_GENITALIA_EXPOSED"]}
def read_config():
    if not os.path.exists(CONFIG_PATH): save_config(default_cfg); return default_cfg
    try:
        enc = CONFIG_PATH.read_bytes(); data = json.loads(fernet.decrypt(enc).decode()); return data
    except Exception: return default_cfg
def save_config(cfg): CONFIG_PATH.write_bytes(fernet.encrypt(json.dumps(cfg).encode()))
def read_lock_state():
    if LOCK_STATE_PATH.exists() and LOCK_STATE_PATH.stat().st_size > 0: return json.loads(LOCK_STATE_PATH.read_text())
    return {"locked_until": 0}
def save_lock_state(state): LOCK_STATE_PATH.write_text(json.dumps(state))
# --- END MISSING FUNCTIONS ---

cfg = read_config()

class AnalyzeRequest(BaseModel):
    text: Optional[str] = None; image_base64: Optional[str] = None

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    if req.text:
        txt = req.text.lower()
        for w in ["porn","sex","xxx","nude","hentai","erotic"]:
            if f" {w} " in f" {txt} ": return {"nsfw": True, "reason": "explicit_word", "word": w}
    if req.image_base64:
        try:
            b = base64.b64decode(req.image_base64.split(",",1)[-1])
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp: tmp.write(b); tmp_path = tmp.name
            detections = detector.detect(tmp_path)
            text_from_image = pytesseract.image_to_string(tmp_path, config=TESSDATA_CONFIG)
            os.unlink(tmp_path)
            if any(w in text_from_image.lower() for w in ["porn","sex","xxx","nude","hentai","erotic"]): return {"nsfw": True, "reason": "explicit_word_in_image"}
            for d in detections:
                if d["class"].upper() in [c.upper() for c in cfg.get("nsfw_classes", [])] and d["score"]>=cfg.get("nsfw_threshold",0.5):
                    return {"nsfw": True, "reason": d["class"], "score": d["score"], "detections": detections}
            return {"nsfw": False, "detections": detections}
        except Exception as e: raise HTTPException(status_code=400, detail=str(e))
    return {"nsfw": False}
@app.post("/lock")
def lock_for(hours: int = 1):
    now = int(time.time()); locked_until = now + int(hours*3600)
    state = {"locked_until": locked_until}; save_lock_state(state)
    return {"locked_until": locked_until}
@app.get("/status")
def status(): return read_lock_state()

def run_fastapi_server():
    uvicorn.run(app, host="127.0.0.1", port=5000, log_config=None)

# --- Main Launcher Logic ---
proxy_proc = None
overlay_proc = None

def start_proxy():
    global proxy_proc
    logging.info("Starting proxy service...")
    try:
        proxy_proc = subprocess.Popen([str(MITMDUMP_EXE), "-s", str(PROXY_ADDON_SCRIPT), "--set", "block_global=false"], cwd=ROOT_PROJECT_DIR, creationflags=subprocess.CREATE_NO_WINDOW)
        logging.info(f"Proxy service started with PID: {proxy_proc.pid}")
    except Exception as e: logging.error(f"Failed to start proxy process: {e}")

def start_overlay():
    global overlay_proc
    logging.info("Lock is active. Starting overlay process.")
    try:
        overlay_proc = subprocess.Popen([str(PYTHON_EXE), str(OVERLAY_SCRIPT)], creationflags=subprocess.CREATE_NO_WINDOW)
        logging.info(f"Overlay process started with PID: {overlay_proc.pid}")
    except Exception as e: logging.error(f"Failed to start overlay process: {e}")

def stop_process_by_pid(pid):
    if pid is None: return
    try:
        parent = psutil.Process(pid); [child.kill() for child in parent.children(recursive=True)]; parent.kill()
        logging.info(f"Process tree for PID {pid} terminated.")
    except psutil.NoSuchProcess: pass
    except Exception as e: logging.error(f"Error stopping process {pid}: {e}")

def main_loop():
    global proxy_proc, overlay_proc
    
    detector_thread = threading.Thread(target=run_fastapi_server, daemon=True)
    detector_thread.start()
    logging.info("Detector service running in a background thread.")
    
    start_proxy()
    
    while True:
        try:
            state = read_lock_state()
            now = int(time.time())
            is_locked = state.get("locked_until", 0) > now
            overlay_is_running = overlay_proc and overlay_proc.poll() is None
            
            if is_locked and not overlay_is_running: start_overlay()
            elif not is_locked and overlay_is_running:
                logging.info("Lock expired. Stopping overlay.")
                stop_process_by_pid(overlay_proc.pid); overlay_proc = None
            if proxy_proc is None or proxy_proc.poll() is not None:
                logging.warning("Proxy service is not running. Restarting..."); start_proxy()
            
            time.sleep(2)
        except Exception as e:
            logging.error(f"Error in main loop: {e}"); time.sleep(5)

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        logging.info("Shutdown requested. Stopping all processes...")
        if overlay_proc: stop_process_by_pid(overlay_proc.pid)
        if proxy_proc: stop_process_by_pid(proxy_proc.pid)
        logging.info("Shutdown complete.")
        sys.exit(0)