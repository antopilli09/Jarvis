import json
import time
import uuid

from config import DATA_DIR

MEMORY_FILE = DATA_DIR / "memory.json"
CHAT_FILE = DATA_DIR / "chat_history.json"      # vecchio file, resta come copia
CHATS_FILE = DATA_DIR / "chats.json"            # nuove conversazioni


# ---------- MEMORIA ----------

def load_memory():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "progetti": [],
            "aziende": [],
            "obiettivi": []
        }


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def add_memory(text):

    memory = load_memory()

    if "ricordi" not in memory:
        memory["ricordi"] = []

    if text not in memory["ricordi"]:
        memory["ricordi"].append(text)

    save_memory(memory)


def get_memories():

    memory = load_memory()
    risultati = []

    for progetto in memory.get("progetti", []):
        risultati.append(f"Progetto: {progetto}")

    for azienda in memory.get("aziende", []):
        risultati.append(f"Azienda: {azienda}")

    for obiettivo in memory.get("obiettivi", []):
        risultati.append(f"Obiettivo: {obiettivo}")

    for ricordo in memory.get("ricordi", []):
        risultati.append(ricordo)

    return risultati


def get_memory_context():
    return "\n".join(get_memories())


# ---------- CONVERSAZIONI ----------

def _nuovo_id():
    return uuid.uuid4().hex[:8]


def _titolo(messaggi):
    for m in messaggi:
        if m.get("role") == "user":
            t = m.get("content", "").strip().replace("\n", " ")
            return t[:40] if t else "Nuova chat"
    return "Nuova chat"


def _salva_chats(dati):
    with open(CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=2)


def _carica_chats():
    try:
        with open(CHATS_FILE, "r", encoding="utf-8") as f:
            dati = json.load(f)
        if "chats" in dati and "attiva" in dati:
            return dati
    except:
        pass

    # prima volta: la vecchia cronologia diventa la prima conversazione
    dati = {"chats": {}, "attiva": None}
    vecchia = []
    try:
        with open(CHAT_FILE, "r", encoding="utf-8") as f:
            vecchia = json.load(f)
    except:
        pass

    if vecchia:
        cid = _nuovo_id()
        dati["chats"][cid] = {
            "id": cid,
            "titolo": _titolo(vecchia),
            "messaggi": vecchia,
            "aggiornata": time.time()
        }
        dati["attiva"] = cid

    _salva_chats(dati)
    return dati


def _crea_chat(dati):
    cid = _nuovo_id()
    dati["chats"][cid] = {
        "id": cid,
        "titolo": "Nuova chat",
        "messaggi": [],
        "aggiornata": time.time()
    }
    dati["attiva"] = cid
    return cid


def load_chat_history():
    dati = _carica_chats()
    att = dati.get("attiva")
    if att in dati["chats"]:
        return dati["chats"][att]["messaggi"]
    return []


def save_chat_message(role, content):

    dati = _carica_chats()

    if dati.get("attiva") not in dati["chats"]:
        _crea_chat(dati)

    chat = dati["chats"][dati["attiva"]]
    chat["messaggi"].append({
        "role": role,
        "content": content
    })

    if role == "user" and chat["titolo"] == "Nuova chat":
        chat["titolo"] = _titolo(chat["messaggi"])

    chat["aggiornata"] = time.time()
    _salva_chats(dati)


def list_chats():
    dati = _carica_chats()
    elenco = sorted(
        dati["chats"].values(),
        key=lambda c: c["aggiornata"],
        reverse=True
    )
    return {
        "chats": [{"id": c["id"], "titolo": c["titolo"]} for c in elenco],
        "attiva": dati.get("attiva")
    }


def new_chat():
    dati = _carica_chats()
    att = dati.get("attiva")

    # se quella attiva è già vuota, non ne crea un'altra
    if att in dati["chats"] and not dati["chats"][att]["messaggi"]:
        return att

    cid = _crea_chat(dati)
    _salva_chats(dati)
    return cid


def open_chat(chat_id):
    dati = _carica_chats()
    if chat_id in dati["chats"]:
        dati["attiva"] = chat_id
        _salva_chats(dati)
        return True
    return False


def delete_chat(chat_id):
    dati = _carica_chats()
    if chat_id in dati["chats"]:
        del dati["chats"][chat_id]
        if dati.get("attiva") == chat_id:
            resto = sorted(
                dati["chats"].values(),
                key=lambda c: c["aggiornata"],
                reverse=True
            )
            dati["attiva"] = resto[0]["id"] if resto else None
        _salva_chats(dati)