"""Configurazione di Jarvis: legge le variabili dal file .env (nella radice del progetto).

Le variabili d'ambiente già impostate nel sistema hanno la precedenza sul file .env.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _carica_env(percorso):
    try:
        with open(percorso, "r", encoding="utf-8") as f:
            for riga in f:
                riga = riga.strip()
                if not riga or riga.startswith("#") or "=" not in riga:
                    continue
                chiave, valore = riga.split("=", 1)
                os.environ.setdefault(chiave.strip(), valore.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


_carica_env(BASE_DIR / ".env")

# Modello Ollama
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL") or "qwen2.5:7b"

# Nome dell'utente (usato solo dalla versione a riga di comando, jarvis.py)
USER_NAME = os.environ.get("JARVIS_USER_NAME") or "l'utente"

# Meteo
CITY_NAME = os.environ.get("CITY_NAME") or "Roma"
LATITUDE = float(os.environ.get("LATITUDE") or "41.90")
LONGITUDE = float(os.environ.get("LONGITUDE") or "12.50")
TIMEZONE = os.environ.get("TIMEZONE") or "Europe/Rome"

# Cartelle e file
DATA_DIR = Path(os.environ.get("DATA_DIR") or BASE_DIR / "data")
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Server (SSL facoltativo: serve per usare il microfono da altri dispositivi in LAN)
HOST = os.environ.get("HOST") or "127.0.0.1"
PORT = int(os.environ.get("PORT") or "8000")
SSL_KEYFILE = os.environ.get("SSL_KEYFILE", "")
SSL_CERTFILE = os.environ.get("SSL_CERTFILE", "")
