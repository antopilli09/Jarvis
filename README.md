# Jarvis

Assistente personale **locale** in italiano, ispirato a Jarvis di Iron Man. Gira interamente sul tuo PC: il modello linguistico, il riconoscimento vocale e la sintesi vocale non inviano i tuoi dati a servizi cloud, e non servono chiavi API.

## Cosa sa fare

- **Chat con memoria**: conversa in italiano usando un modello LLM locale (via [Ollama](https://ollama.com)), con più conversazioni salvate e cronologia.
- **Memoria a lungo termine**: ricorda informazioni su di te e sui tuoi progetti quando le menzioni ("sto sviluppando…", "mi chiamo…").
- **Voce**: ascolta con il microfono (Whisper) e risponde parlando (Kokoro, voce italiana).
- **Comandi per il PC (Windows)**: apre programmi e siti web, regola il volume, blocca lo schermo (es. "apri calcolatrice", "alza il volume").
- **Timer, sveglie e promemoria**: "ricordami tra venti minuti di chiamare…", "sveglia alle sette e trenta".
- **Briefing**: data, ora, meteo, promemoria attivi e notizie del giorno riassunte a voce.
- **Ricerca web**: scrivi `cerca: <domanda>` e Jarvis riassume i risultati di DuckDuckGo.
- **Analisi di documenti**: carica un PDF, DOCX o TXT e fai domande sul contenuto.
- **Dashboard**: interfaccia web con uso di CPU e RAM e meteo.

## Tecnologie

| Ambito | Strumenti |
|---|---|
| Backend | Python, FastAPI, Uvicorn |
| LLM | Ollama (default `qwen2.5:7b`) |
| Riconoscimento vocale | faster-whisper |
| Sintesi vocale | Kokoro (PyTorch) |
| Ricerca web | ddgs (DuckDuckGo) |
| Meteo | Open-Meteo (gratuito, senza chiave) |
| Documenti | pypdf, python-docx |
| Frontend | HTML, CSS e JavaScript puro |

## Requisiti

- Windows 10/11 (i comandi per il PC usano API di Windows)
- Python 3.10 – 3.12
- [Ollama](https://ollama.com/download) installato
- Facoltativo: una GPU NVIDIA per rendere più veloce la sintesi vocale

## Installazione

```bash
# 1. Clona il repository
git clone https://github.com/<tuo-utente>/jarvis.git
cd jarvis

# 2. Crea l'ambiente virtuale e installa le dipendenze
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r ..\requirements.txt
cd ..

# 3. Scarica il modello linguistico
ollama pull qwen2.5:7b

# 4. Crea la tua configurazione
copy .env.example .env
```

Apri `.env` e inserisci i tuoi valori (città e coordinate per il meteo, nome, ecc.). Tutte le variabili sono spiegate in [.env.example](.env.example).

## Avvio

Assicurati che Ollama sia in esecuzione, poi:

```bash
start_jarvis.bat
```

oppure, a mano:

```bash
cd backend
python run.py
```

Apri <http://localhost:8000> nel browser. Al primo avvio vengono scaricati i modelli Whisper e Kokoro e vengono generati i file audio di avvio: ci vuole qualche minuto.

### Usare il microfono da altri dispositivi (HTTPS)

I browser permettono il microfono solo su `localhost` o in HTTPS. Per usare Jarvis da telefono o da un altro PC della rete:

1. Genera un certificato locale con [mkcert](https://github.com/FiloSottile/mkcert), ad esempio `mkcert 192.168.1.10 localhost`.
2. In `.env` imposta `HOST=0.0.0.0`, `SSL_KEYFILE` e `SSL_CERTFILE` con i percorsi dei file generati.
3. Riavvia e apri `https://<ip-del-tuo-pc>:8000`.

> Non pubblicare mai i file `.pem` né il tuo `.env`: sono esclusi dal repository tramite `.gitignore`.

## Struttura del progetto

```
jarvis/
├── backend/
│   ├── server.py        # API FastAPI, comandi PC, promemoria, briefing
│   ├── memory.py        # memoria e cronologia delle chat
│   ├── config.py        # lettura delle impostazioni da .env
│   ├── run.py           # avvio del server
│   ├── jarvis.py        # versione a riga di comando
│   └── modules/
│       ├── voice.py     # riconoscimento e sintesi vocale
│       └── websearch.py # ricerca web
├── frontend/            # interfaccia web
├── data/                # dati locali generati (chat, memoria): non versionati
├── .env.example
└── requirements.txt
```

## Privacy

Chat, memoria e promemoria sono salvati in locale nella cartella `data/` e non vengono mai caricati sul repository. L'unico traffico verso Internet riguarda la ricerca web (DuckDuckGo), il meteo (Open-Meteo) e il download iniziale dei modelli.

## Note

Progetto personale a scopo di studio e portfolio. I comandi vocali sono pensati per Windows e in italiano.
