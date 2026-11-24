import io
import os
import tempfile
import threading

import numpy as np
import soundfile as sf
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from faster_whisper import WhisperModel
from kokoro import KPipeline

from config import DATA_DIR

router = APIRouter(prefix="/api")

print("[VOICE] Carico Whisper...")
stt_model = WhisperModel("small", device="cpu", compute_type="int8")
print("[VOICE] Carico Kokoro...")
import torch
_device = "cuda" if torch.cuda.is_available() else "cpu"
print("[VOICE] Kokoro su", _device)
tts_pipeline = KPipeline(lang_code="i", repo_id="hexgrad/Kokoro-82M", device=_device)
tts_lock = threading.Lock()


def sintetizza(text, voice="im_nicola", speed=1.0):
    chunks = []
    with tts_lock:
        for _, _, a in tts_pipeline(text, voice=voice, speed=speed):
            chunks.append(a.numpy() if hasattr(a, "numpy") else a)
    if not chunks:
        return None
    return np.concatenate(chunks)


# ---------- AUDIO DEL BOOT (creato una volta sola) ----------

BOOT_DIR = str(DATA_DIR / "boot")

BOOT_FRASI = {
    "boot0": "Inizializzazione sistemi completata.",
    "boot1": "Rete neurale online.",
    "boot2": "Collegamento al cervello riuscito.",
    "boot3": "Memoria online.",
    "boot4": "Ricerca web online.",
    "boot5": "Sintesi vocale pronta.",
    "saluto_mattina": "Buongiorno, Signore... Tutti i sistemi sono operativi. Come posso assisterla oggi?",
    "saluto_pomeriggio": "Buon pomeriggio, Signore... Tutti i sistemi sono operativi. Come posso assisterla oggi?",
    "saluto_sera": "Buonasera, Signore... Tutti i sistemi sono operativi. Come posso assisterla oggi?",
}

print("[VOICE] Scaldo Kokoro...")
sintetizza("Prova di avvio.")

def prepara_boot():
    os.makedirs(BOOT_DIR, exist_ok=True)
    for nome, testo in BOOT_FRASI.items():
        path = os.path.join(BOOT_DIR, nome + ".wav")
        if os.path.exists(path):
            continue
        print("[VOICE] Creo audio boot:", nome)
        wav = sintetizza(testo)
        if wav is not None:
            sf.write(path, wav, 24000)


prepara_boot()
print("[VOICE] Voice Engine Online")


@router.get("/boot/{nome}")
def boot_audio(nome: str):
    path = os.path.join(BOOT_DIR, nome + ".wav")
    if nome not in BOOT_FRASI or not os.path.exists(path):
        return Response(status_code=404)
    return FileResponse(path, media_type="audio/wav")


# ---------- ORECCHIO E VOCE ----------

class TTSRequest(BaseModel):
    text: str
    voice: str = "im_nicola"
    speed: float = 1.0


FRASI_FANTASMA = [
    "sottotitoli", "qtss", "amara.org",
    "grazie per la visione", "iscriviti al canale"
]


@router.post("/stt")
def stt(audio: UploadFile = File(...)):
    import traceback
    suffix = os.path.splitext(audio.filename or "")[1] or ".webm"
    dati = audio.file.read()
    print(f"[STT] ricevuti {len(dati)} byte")

    if len(dati) < 2000:
        return {"text": ""}

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(dati)
        path = f.name
    try:
        segments, _ = stt_model.transcribe(
            path,
            language="it",
            vad_filter=True,
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            temperature=0.0,
            initial_prompt="Jarvis. Ciao Jarvis, buongiorno Jarvis, dammi il briefing."
        )
        text = " ".join(s.text.strip() for s in segments).strip()
    except Exception:
        traceback.print_exc()
        return {"text": ""}
    finally:
        os.remove(path)

    if any(f in text.lower() for f in FRASI_FANTASMA):
        print(f"[STT] scartato (audio vuoto): {text!r}")
        return {"text": ""}

    print(f"[STT] testo: {text!r}")
    return {"text": text}


@router.post("/tts")
def tts(req: TTSRequest):
    wav = sintetizza(req.text, req.voice, req.speed)
    if wav is None:
        return Response(status_code=204)
    buf = io.BytesIO()
    sf.write(buf, wav, 24000, format="WAV")
    return Response(buf.getvalue(), media_type="audio/wav")


@router.get("/voice/status")
def voice_status():
    return {"stt": True, "tts": True}