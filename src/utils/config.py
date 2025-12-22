import json
import sys
from pathlib import Path

# ---------- DETERMINA LA BASE_DIR ----------
# Se il programma è "frozen" (eseguibile compilato), la base è dove si trova l'eseguibile.
# Se siamo in sviluppo (VS Code), la base è calcolata relativa a questo file sorgente.
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------- CONFIGURAZIONE PATH ----------
CONFIG_FILE = BASE_DIR / "data" / "config.json"

# Assicuriamoci che la cartella 'data' esista, altrimenti save_config fallisce al primo avvio
CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "INPUT_DIR": "input_pdf",
    "DOP_DIR": "DOP",
    "CERTIFICATI_DIR": "Certificati"
}

INVALID_CHARS = r'\/:*?"<>|'


def load_config():
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        # file vuoto o corrotto → ripristina default
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    # assicura chiavi mancanti
    changed = False
    for key, value in DEFAULT_CONFIG.items():
        if key not in data:
            data[key] = value
            changed = True

    if changed:
        save_config(data)

    return data

def _resolve_path(p):
    if not p:
        raise ValueError("Percorso di configurazione non valido (None o vuoto)")
    p = Path(p)
    return p if p.is_absolute() else BASE_DIR / p

def save_config(data: dict):
    # La cartella genitore è già garantita dalla mkdir fatta all'inizio
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# ---------- CARICA CONFIG E CREA CARTELLE ----------
_cfg = load_config()

INPUT_DIR = _resolve_path(_cfg["INPUT_DIR"])
DOP_DIR = _resolve_path(_cfg["DOP_DIR"])
CERTIFICATI_DIR = _resolve_path(_cfg["CERTIFICATI_DIR"])

FORNITORI_FILE = BASE_DIR / "data" / "fornitori.txt"

# Creazione cartelle operative
INPUT_DIR.mkdir(parents=True, exist_ok=True) # parents=True è più sicuro
DOP_DIR.mkdir(parents=True, exist_ok=True)
CERTIFICATI_DIR.mkdir(parents=True, exist_ok=True)

if not FORNITORI_FILE.exists():
    FORNITORI_FILE.touch()