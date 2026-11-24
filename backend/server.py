from fastapi import FastAPI
from fastapi.responses import FileResponse
from ollama import chat
import psutil
import httpx
import io
import os
import subprocess
import ctypes
import re
import difflib
import json
import time
import threading
from datetime import datetime, timedelta
from fastapi import UploadFile, File

from memory import (
    get_memories,
    add_memory,
    save_chat_message,
    load_chat_history,
    get_memory_context,
    list_chats,
    new_chat,
    open_chat,
    delete_chat
)
from config import (
    DATA_DIR, FRONTEND_DIR, OLLAMA_MODEL,
    CITY_NAME, LATITUDE, LONGITUDE, TIMEZONE,
)
from modules.websearch import search_web
from modules.voice import router as voice_router

app = FastAPI()
app.include_router(voice_router)

import threading


def scalda_qwen():
    try:
        chat(
            model=OLLAMA_MODEL,
            keep_alive="30m",
            messages=[{"role": "user", "content": "ok"}]
        )
        print("[QWEN] Modello caricato e pronto")
    except Exception as e:
        print("[QWEN] Errore pre-caricamento:", e)


threading.Thread(target=scalda_qwen, daemon=True).start()


@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/style.css")
def style():
    return FileResponse(FRONTEND_DIR / "style.css")


@app.get("/app.js")
def appjs():
    return FileResponse(FRONTEND_DIR / "app.js")


@app.get("/system")
def system_info():
    return {
        "cpu": psutil.cpu_percent(interval=0.3),
        "ram": psutil.virtual_memory().percent
    }


CODICI_METEO = {
    0: "sereno", 1: "prevalentemente sereno", 2: "parzialmente nuvoloso",
    3: "coperto", 45: "nebbia", 48: "nebbia",
    51: "pioggerella", 53: "pioggerella", 55: "pioggerella intensa",
    61: "pioggia leggera", 63: "pioggia", 65: "pioggia forte",
    71: "neve leggera", 73: "neve", 75: "neve forte",
    80: "rovesci leggeri", 81: "rovesci", 82: "rovesci violenti",
    95: "temporale", 96: "temporale con grandine", 99: "temporale con grandine"
}


@app.get("/weather")
def weather():
    try:
        r = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": LATITUDE,
                "longitude": LONGITUDE,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "timezone": TIMEZONE
            },
            timeout=8
        )
        c = r.json()["current"]
        return {
            "luogo": CITY_NAME,
            "temp": round(c["temperature_2m"]),
            "descrizione": CODICI_METEO.get(c["weather_code"], "variabile"),
            "vento": round(c["wind_speed_10m"])
        }
    except Exception as e:
        print("Errore meteo:", e)
        return {"errore": True}


@app.get("/memory-stats")
def memory_stats():
    try:
        mem = get_memories()
        if isinstance(mem, dict):
            ricordi = sum(
                len(v) if isinstance(v, list) else 1
                for v in mem.values()
            )
        else:
            ricordi = len(mem)
        messaggi = len(load_chat_history())
        return {"ricordi": ricordi, "messaggi": messaggi}
    except Exception as e:
        print("Errore memoria:", e)
        return {"errore": True}

DOCUMENTO = {"nome": None, "testo": ""}
MAX_CARATTERI = 12000


def estrai_testo(nome, dati):
    est = os.path.splitext(nome)[1].lower()
    if est == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(dati))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    if est == ".docx":
        from docx import Document
        doc = Document(io.BytesIO(dati))
        return "\n".join(p.text for p in doc.paragraphs)
    if est in (".txt", ".md"):
        return dati.decode("utf-8", errors="ignore")
    return None


@app.post("/upload")
def upload(file: UploadFile = File(...)):
    try:
        testo = estrai_testo(file.filename or "", file.file.read())
    except Exception as e:
        print("Errore upload:", e)
        return {"errore": "Non riesco a leggere questo file."}
    if testo is None:
        return {"errore": "Formato non supportato. Usa PDF, DOCX o TXT."}
    testo = testo.strip()
    if not testo:
        return {"errore": "Nel file non trovo testo (forse è una scansione)."}
    troncato = len(testo) > MAX_CARATTERI
    DOCUMENTO["nome"] = file.filename
    DOCUMENTO["testo"] = testo[:MAX_CARATTERI]
    return {"nome": file.filename, "caratteri": len(DOCUMENTO["testo"]), "troncato": troncato}


@app.post("/upload/clear")
def upload_clear():
    DOCUMENTO["nome"] = None
    DOCUMENTO["testo"] = ""
    return {"ok": True}


def contesto_doc():
    if not DOCUMENTO["testo"]:
        return ""
    return f"""
L'utente ha caricato il documento "{DOCUMENTO['nome']}". Ecco il suo contenuto:
---
{DOCUMENTO['testo']}
---
Quando l'utente fa domande sul documento, rispondi usando questo contenuto.
"""

@app.get("/chats")
def chats_list():
    return list_chats()


@app.post("/chats/new")
def chats_new():
    new_chat()
    return {"ok": True}


@app.post("/chats/{chat_id}/open")
def chats_open(chat_id: str):
    return {"ok": open_chat(chat_id)}


@app.delete("/chats/{chat_id}")
def chats_delete(chat_id: str):
    delete_chat(chat_id)
    return {"ok": True}

def _tasto(codice, volte=1):
    for _ in range(volte):
        ctypes.windll.user32.keybd_event(codice, 0, 0, 0)
        ctypes.windll.user32.keybd_event(codice, 0, 2, 0)


def _apri(programma):
    subprocess.Popen(programma, shell=True)


COMANDI_PC = [
    (["apri chrome", "apri google"],
     lambda: _apri("start chrome"), "Apro Chrome."),
    (["apri il blocco note", "apri blocco note", "apri notepad"],
     lambda: _apri("start notepad"), "Apro il Blocco note."),
    (["apri la calcolatrice", "apri calcolatrice"],
     lambda: _apri("start calc"), "Apro la calcolatrice."),
    (["apri esplora file", "apri risorse del computer"],
     lambda: _apri("start explorer"), "Apro Esplora file."),
    (["apri vs code", "apri visual studio code"],
     lambda: _apri("start code"), "Apro Visual Studio Code."),
    (["alza il volume", "volume su"],
     lambda: _tasto(0xAF, 5), "Volume alzato."),
    (["abbassa il volume", "volume giù", "volume giu"],
     lambda: _tasto(0xAE, 5), "Volume abbassato."),
    (["silenzia", "muta il volume", "togli l'audio"],
     lambda: _tasto(0xAD), "Fatto."),
    (["blocca lo schermo", "blocca il computer"],
     lambda: ctypes.windll.user32.LockWorkStation(), "Blocco lo schermo."),
]

SITI = {
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "google drive": "https://drive.google.com",
    "drive": "https://drive.google.com",
    "google maps": "https://www.google.com/maps",
    "maps": "https://www.google.com/maps",
    "traduttore": "https://translate.google.com",
    "whatsapp web": "https://web.whatsapp.com",
    "telegram web": "https://web.telegram.org",
    "netflix": "https://www.netflix.com",
    "prime video": "https://www.primevideo.com",
    "disney plus": "https://www.disneyplus.com",
    "twitch": "https://www.twitch.tv",
    "amazon": "https://www.amazon.it",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "linkedin": "https://www.linkedin.com",
    "wikipedia": "https://it.wikipedia.org",
    "outlook web": "https://outlook.live.com",
}

PROGRAMMI = {
    "impostazioni": "ms-settings:",
    "gestione attività": "taskmgr",
    "gestione attivita": "taskmgr",
    "prompt dei comandi": "cmd",
    "powershell": "powershell",
    "paint": "mspaint",
    "pannello di controllo": "control",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpoint",
    "outlook": "outlook",
    "microsoft store": "ms-windows-store:",
    "orologio": "ms-clock:",
    "foto": "ms-photos:",
    "cattura schermo": "ms-screenclip:",
    "download": os.path.join(os.path.expanduser("~"), "Downloads"),
    "documenti": os.path.join(os.path.expanduser("~"), "Documents"),
    "desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
}


def _scansiona_start():
    basi = [
        os.path.join(os.environ.get("ProgramData", ""), r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
    ]
    trovati = {}
    for base in basi:
        for radice, _, files in os.walk(base):
            for f in files:
                if not f.lower().endswith(".lnk"):
                    continue
                nome = f[:-4].lower()
                if "uninstall" in nome or "disinstalla" in nome:
                    continue
                trovati[nome] = os.path.join(radice, f)
    return trovati


APP_START = _scansiona_start()
print(f"[PC] Programmi trovati nel menu Start: {len(APP_START)}")


def apri_generico(testo):
    m = re.match(r"^(apri|avvia|lancia)\s+(il |lo |la |l'|i |gli |le )?(.+)$", testo)
    if not m:
        return None
    nome = m.group(3).strip()

    try:
        if nome in SITI:
            os.startfile(SITI[nome])
            return f"Apro {nome}."

        if nome in PROGRAMMI:
            _apri("start " + PROGRAMMI[nome] if ":" in PROGRAMMI[nome] or "\\" not in PROGRAMMI[nome]
                  else "explorer " + PROGRAMMI[nome])
            return f"Apro {nome}."

        scelto = None
        if nome in APP_START:
            scelto = nome
        else:
            contiene = [k for k in APP_START if nome in k]
            if contiene:
                scelto = min(contiene, key=len)
            else:
                simili = difflib.get_close_matches(nome, list(APP_START), n=1, cutoff=0.7)
                if simili:
                    scelto = simili[0]

        if scelto:
            os.startfile(APP_START[scelto])
            return f"Apro {scelto}."
    except Exception as e:
        print("Errore apertura:", e)
        return "Non sono riuscito ad aprirlo."

    return None

# ---------- TIMER E PROMEMORIA ----------

PROMEMORIA_FILE = DATA_DIR / "promemoria.json"
_lock_prom = threading.Lock()

_UNITA = {
    "un": 1, "uno": 1, "una": 1, "due": 2, "tre": 3, "quattro": 4,
    "cinque": 5, "sei": 6, "sette": 7, "otto": 8, "nove": 9,
    "dieci": 10, "undici": 11, "dodici": 12, "tredici": 13,
    "quattordici": 14, "quindici": 15, "sedici": 16,
    "diciassette": 17, "diciotto": 18, "diciannove": 19,
}
_DECINE = {"venti": 20, "trenta": 30, "quaranta": 40, "cinquanta": 50, "sessanta": 60}

NUMERI = dict(_UNITA)
NUMERI.update(_DECINE)
for _d, _v in _DECINE.items():
    for _u in ("uno", "due", "tre", "quattro", "cinque", "sei", "sette", "otto", "nove"):
        NUMERI[_d + _u] = _v + _UNITA[_u]
        NUMERI[_d[:-1] + _u] = _v + _UNITA[_u]


def _numero(parola):
    parola = parola.strip().lower()
    if parola.isdigit():
        return int(parola)
    return NUMERI.get(parola)


def _carica_prom():
    try:
        with open(PROMEMORIA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _salva_prom(lista):
    with open(PROMEMORIA_FILE, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


def _a_parole(sec):
    ore, resto = divmod(int(sec), 3600)
    minuti, secondi = divmod(resto, 60)
    parti = []
    if ore:
        parti.append(f"{ore} {'ora' if ore == 1 else 'ore'}")
    if minuti:
        parti.append(f"{minuti} {'minuto' if minuti == 1 else 'minuti'}")
    if secondi:
        parti.append(f"{secondi} {'secondo' if secondi == 1 else 'secondi'}")
    return " e ".join(parti) or "0 secondi"


def _durata(testo):
    """Cerca una durata (es. 'tra 20 minuti'). Restituisce (secondi, prima, dopo)."""
    t = testo.replace("un'ora", "1 ora").replace("un’ora", "1 ora")
    speciali = [
        ("un quarto d'ora", 900), ("un quarto d’ora", 900),
        ("mezz'ora", 1800), ("mezz’ora", 1800), ("mezzora", 1800),
    ]
    for frase, sec in speciali:
        i = t.find(frase)
        if i != -1:
            return sec, t[:i], t[i + len(frase):]

    m = re.search(r"([\w']+)\s+(second[oi]|minut[oi]|or[ae])\b", t)
    if not m:
        return None
    n = _numero(m.group(1))
    if n is None:
        return None
    unita = m.group(2)
    if unita.startswith("second"):
        sec = n
    elif unita.startswith("minut"):
        sec = n * 60
    else:
        sec = n * 3600
    return sec, t[:m.start()], t[m.end():]


def _pulisci_cosa(s):
    s = re.sub(
        r"\b(ricordami|ricordarmi|ricorda|avvisami|promemoria|imposta|metti|"
        r"un|per favore|puoi|potresti|sveglia)\b", " ", s
    )
    s = s.strip(" ,.;:!?")
    s = re.sub(r"\b(tra|fra|alle)\s*$", "", s).strip(" ,.;:!?")
    s = re.sub(r"^(di|che|a|da|per)\s+", "", s).strip(" ,.;:!?")
    return re.sub(r"\s+", " ", s)


def _aggiungi_prom(quando, etichetta, messaggio):
    with _lock_prom:
        lista = _carica_prom()
        lista.append({
            "quando": quando,
            "etichetta": etichetta,
            "messaggio": messaggio,
        })
        _salva_prom(lista)


def gestisci_promemoria(testo):
    parole_chiave = ("promemoria", "timer", "sveglia", "sveglie")

    # annulla tutto
    if any(k in testo for k in ("cancella", "annulla", "elimina", "togli")) \
            and any(k in testo for k in parole_chiave):
        with _lock_prom:
            _salva_prom([])
        return "Ho cancellato tutti i promemoria."

    # elenco
    if any(k in testo for k in ("quali", "elenca", "mostra", "quanti")) \
            and any(k in testo for k in parole_chiave):
        with _lock_prom:
            lista = _carica_prom()
        if not lista:
            return "Non ha nessun promemoria attivo."
        adesso = time.time()
        voci = [
            f"{p['etichetta']} tra {_a_parole(max(0, p['quando'] - adesso))}"
            for p in sorted(lista, key=lambda p: p["quando"])
        ]
        return f"Ha {len(voci)} promemoria attivi: " + "; ".join(voci) + "."

    # impostazione
    inizi = ("ricordami", "ricordarmi", "avvisami", "imposta", "metti", "mettimi",
             "avvia", "fai partire", "programma", "puoi", "potresti", "timer", "sveglia")
    if not (any(k in testo for k in ("ricordami", "ricordarmi", "avvisami", "timer", "sveglia"))
            and testo.startswith(inizi)):
        return None

    d = _durata(testo)
    if d:
        sec, prima, dopo = d
        if sec <= 0:
            return "La durata non è valida."
        quando = time.time() + sec
        durata_txt = _a_parole(sec)
        if "timer" in testo:
            _aggiungi_prom(quando, "timer", f"Signore, il timer da {durata_txt} è scaduto.")
            return f"Timer di {durata_txt} avviato."
        cosa = _pulisci_cosa(dopo) or _pulisci_cosa(prima)
        if cosa:
            _aggiungi_prom(quando, cosa, f"Signore, le ricordo di {cosa}.")
            return f"Va bene, tra {durata_txt} le ricordo di {cosa}."
        _aggiungi_prom(quando, "promemoria", "Signore, è scaduto il promemoria.")
        return f"Va bene, la avviso tra {durata_txt}."

    m = re.search(r"\balle\s+(\d{1,2})(?:\s*(?:[:.]|e)\s*(\d{2}))?\b", testo)
    if m:
        ore = int(m.group(1))
        minuti = int(m.group(2) or 0)
        if ore > 23 or minuti > 59:
            return "L'orario non è valido."
        adesso = datetime.now()
        quando = adesso.replace(hour=ore, minute=minuti, second=0, microsecond=0)
        if quando <= adesso:
            quando += timedelta(days=1)
        ora_txt = f"{ore} in punto" if minuti == 0 else f"{ore} e {minuti:02d}"
        if "sveglia" in testo:
            _aggiungi_prom(quando.timestamp(), "sveglia", f"Sveglia, Signore. Sono le {ora_txt}.")
            return f"Sveglia impostata per le {ora_txt}."
        cosa = _pulisci_cosa(testo[m.end():]) or _pulisci_cosa(testo[:m.start()])
        if cosa:
            _aggiungi_prom(quando.timestamp(), cosa, f"Signore, le ricordo di {cosa}.")
            return f"Va bene, alle {ora_txt} le ricordo di {cosa}."
        _aggiungi_prom(quando.timestamp(), "promemoria", "Signore, è scaduto il promemoria.")
        return f"Va bene, la avviso alle {ora_txt}."

    return "Non ho capito quando. Può dire, per esempio, tra venti minuti, oppure alle sette e trenta."


@app.get("/reminders/due")
def reminders_due():
    adesso = time.time()
    with _lock_prom:
        lista = _carica_prom()
        scaduti = [p for p in lista if p["quando"] <= adesso]
        if scaduti:
            _salva_prom([p for p in lista if p["quando"] > adesso])
    return {"scaduti": [p["messaggio"] for p in scaduti]}

# ---------- BRIEFING ----------

GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]

FRASI_BRIEFING = ("briefing", "buongiorno jarvis", "buonasera jarvis",
                  "rapporto del mattino", "riassunto della giornata",
                  "com'è la giornata", "cosa c'è oggi")


def _notizie_brevi():
    try:
        risultati = search_web("ultime notizie Italia oggi")
        testo = str(risultati)[:4000]
        r = chat(
            model=OLLAMA_MODEL,
            keep_alive="30m",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sei Jarvis. Dai risultati di una ricerca web, riassumi le "
                        "notizie principali in italiano, in massimo 3 frasi brevi. "
                        "Niente elenchi, niente simboli, niente link, niente JSON. "
                        "Il testo verrà letto ad alta voce."
                    )
                },
                {"role": "user", "content": testo}
            ]
        )
        return r.message.content.strip()
    except Exception as e:
        print("Errore notizie briefing:", e)
        return None


def genera_briefing():
    adesso = datetime.now()
    ora = adesso.hour
    if 5 <= ora < 13:
        apertura = "Buongiorno"
    elif 13 <= ora < 18:
        apertura = "Buon pomeriggio"
    else:
        apertura = "Buonasera"

    parti = [
        f"{apertura}, Signore. Oggi è {GIORNI[adesso.weekday()]} "
        f"{adesso.day} {MESI[adesso.month - 1]}, sono le {adesso.hour} e {adesso.minute:02d}."
    ]

    try:
        w = weather()
        if not w.get("errore"):
            parti.append(
                f"A {w['luogo']} ci sono {w['temp']} gradi, {w['descrizione']}."
            )
    except Exception as e:
        print("Errore meteo briefing:", e)

    with _lock_prom:
        lista = _carica_prom()
    if lista:
        voci = [
            f"{p['etichetta']} tra {_a_parole(max(0, p['quando'] - time.time()))}"
            for p in sorted(lista, key=lambda p: p["quando"])
        ]
        parti.append(f"Ha {len(voci)} promemoria attivi: " + "; ".join(voci) + ".")
    else:
        parti.append("Non ha promemoria attivi.")

    notizie = _notizie_brevi()
    if notizie:
        parti.append("Le notizie principali. " + notizie)

    return " ".join(parti)

def esegui_comando_pc(messaggio):
    testo = messaggio.lower().strip().rstrip(".!?")
    risposta_prom = gestisci_promemoria(testo)
    if risposta_prom:
        return risposta_prom
    if any(f in testo for f in FRASI_BRIEFING):
        return genera_briefing()
    for frasi, azione, risposta in COMANDI_PC:
        if any(testo == f or testo.startswith(f + " ") for f in frasi):
            try:
                azione()
                return risposta
            except Exception as e:
                print("Errore comando PC:", e)
                return "Non sono riuscito a eseguire il comando."
    return apri_generico(testo)

@app.get("/history")
def get_history():
    return {
        "history": load_chat_history()
    }


@app.get("/chat")
def chat_with_jarvis(message: str):
    comando = esegui_comando_pc(message)
    if comando:
        save_chat_message("user", message)
        save_chat_message("assistant", comando)
        return {"response": comando}

    # RICERCA WEB
    if message.lower().startswith("cerca:"):

        query = message[6:].strip()

        risultati = search_web(query)

        testo_ricerca = str(risultati)

        risposta_web = chat(
            model=OLLAMA_MODEL,
            keep_alive="30m",
            messages=[
                {
                    "role": "system",
                    "content": """
Sei Jarvis.

Hai ricevuto risultati da una ricerca web.

Devi:
- riassumere i risultati
- rispondere in italiano
- evidenziare i punti principali
- evitare di mostrare JSON o codice
- indicare brevemente le fonti trovate
"""
                },
                {
                    "role": "user",
                    "content": f"""
Domanda:

{query}

Risultati trovati sul web:

{testo_ricerca}
"""
                }
            ]
        )

        return {
            "response": risposta_web.message.content
        }

    # MEMORIA AUTOMATICA
    memory_keywords = [
        "sto sviluppando",
        "sto creando",
        "mi chiamo",
        "il mio progetto",
        "la mia azienda",
        "lavoro su",
        "voglio realizzare"
    ]

    for keyword in memory_keywords:

        if keyword in message.lower() and "?" not in message:

            add_memory(message)

            return {
                "response": "Capito. Ho salvato questa informazione nella mia memoria."
            }

    contesto = get_memory_context()

    save_chat_message(
        "user",
        message
    )

    # ultimi messaggi, escluso quello appena salvato (lo aggiungiamo sotto)
    storico = [
        {"role": m["role"], "content": m["content"]}
        for m in load_chat_history()[-11:-1]
    ]

    risposta = chat(
        model=OLLAMA_MODEL,
        keep_alive="30m",
        options={"num_ctx": 6144},
        messages=[
            {
                "role": "system",
                "content": f"""
Sei Jarvis.

Assistente personale dell'utente, che chiami Signore.

Queste sono le informazioni che conosci e che devi considerare vere:

{contesto}
{contesto_doc()}

Quando l'utente chiede:
- cosa sai di me
- quali informazioni conosci
- chi sono
- quali progetti ho
- cosa ricordi

devi elencare esplicitamente tutti i ricordi presenti nella memoria.

Non ignorare mai i ricordi presenti nella memoria.
Tieni conto dei messaggi precedenti della conversazione.

Non dire mai di essere Qwen.
Non inventare informazioni.

Rispondi sempre in italiano.
Rispondi in modo breve: massimo 3 frasi, a meno che l'utente chieda più dettagli.
Non usare elenchi, simboli o formattazione: le tue risposte vengono lette ad alta voce.
Usa sempre la memoria quando è rilevante.
"""
            },
            *storico,
            {
                "role": "user",
                "content": message
            }
        ]
    )

    save_chat_message(
        "assistant",
        risposta.message.content
    )

    return {
        "response": risposta.message.content
    }