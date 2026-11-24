const bootMessages = [
    "Inizializzazione sistemi completata.",
    "Rete neurale online.",
    "Collegamento al cervello riuscito.",
    "Memoria online.",
    "Ricerca web online.",
    "Sintesi vocale pronta."
];

function saluto() {
    const ora = new Date().getHours();
    let apertura = "Buonasera";

    if (ora >= 5 && ora < 13) {
        apertura = "Buongiorno";
    } else if (ora >= 13 && ora < 18) {
        apertura = "Buon pomeriggio";
    }

    return apertura + ", Signore... Tutti i sistemi sono operativi. Come posso assisterla oggi?";
}


// Scarica da Kokoro l'audio di una frase (senza riprodurlo)
async function caricaAudio(text) {
    try {
        const r = await fetch("/api/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text })
        });
        if (!r.ok || r.status === 204) return null;
        return URL.createObjectURL(await r.blob());
    } catch (err) {
        console.log("Errore voce:", err);
        return null;
    }
}

// Riproduce un audio e aspetta che finisca
let audioCorrente = null;
let vocePausata = false;

function riproduci(url) {
    return new Promise(resolve => {
        if (!url || vocePausata) { resolve(); return; }
        const audio = new Audio(url);
        audioCorrente = audio;
        audio.onended = () => { URL.revokeObjectURL(url); resolve(); };
        audio.onerror = () => resolve();
        audio.play().catch(() => resolve());
    });
}

function fermaVoce() {
    vocePausata = true;
    if (audioCorrente) {
        audioCorrente.pause();
        audioCorrente.dispatchEvent(new Event("ended"));
    }
    setStatus("ONLINE");
    setTimeout(() => { vocePausata = false; }, 600);
}

function nomeSaluto() {
    const ora = new Date().getHours();
    if (ora >= 5 && ora < 13) return "saluto_mattina";
    if (ora >= 13 && ora < 18) return "saluto_pomeriggio";
    return "saluto_sera";
}

// Scarica un audio del boot già pronto sul server
async function caricaBoot(nome) {
    try {
        const r = await fetch("/api/boot/" + nome);
        if (!r.ok) return null;
        return URL.createObjectURL(await r.blob());
    } catch (err) {
        console.log("Errore audio boot:", err);
        return null;
    }
}

async function bootJarvis() {
    const log = document.getElementById("boot-log");

    const bottone = document.createElement("button");
    bottone.innerText = "AVVIA SISTEMA";
    bottone.style.cssText =
        "margin-top:30px;padding:14px 32px;font-size:18px;letter-spacing:3px;" +
        "background:transparent;color:#00e5ff;border:2px solid #00e5ff;" +
        "border-radius:8px;cursor:pointer;";
    log.appendChild(bottone);

    bottone.onclick = async () => {
        bottone.remove();
        setStatus("BOOT");

        // gli audio sono file già pronti: arrivano subito
        const nomi = [...bootMessages.map((_, i) => "boot" + i), nomeSaluto()];
        const audio = await Promise.all(nomi.map(caricaBoot));

        for (let i = 0; i < bootMessages.length; i++) {
            log.innerHTML += bootMessages[i] + "<br>";
            await riproduci(audio[i]);
        }

        document.getElementById("boot-screen").style.display = "none";
        setStatus("SPEAKING");
        await riproduci(audio[audio.length - 1]);
        setStatus("ONLINE");
    };
}


function setStatus(text) {
    const status = document.getElementById("jarvis-status");
    if (status) {
        status.innerText = text;
    }
    document.body.dataset.stato = text;
}

// Divide il testo in pezzi corti: il primo suono parte prima
function dividiTesto(testo) {
    const frasi = (testo.match(/[^.!?\n]+[.!?]*/g) || [])
        .map(s => s.trim())
        .filter(s => s.length > 1);

    const pezzi = [];
    for (const f of frasi) {
        if (f.length <= 70) {
            pezzi.push(f);
            continue;
        }
        // le frasi lunghe vengono spezzate alle virgole
        const parti = f.split(/(?<=[,;:])\s+/);
        let corrente = "";
        for (const p of parti) {
            if (corrente && (corrente + " " + p).length > 70) {
                pezzi.push(corrente.trim());
                corrente = p;
            } else {
                corrente = (corrente + " " + p).trim();
            }
        }
        if (corrente) pezzi.push(corrente.trim());
    }
    return pezzi;
}

// ---------- VOCE DI JARVIS (Kokoro) ----------

async function speak(text) {
    // toglie i simboli che la voce leggerebbe male
    const pulito = text.replace(/[*#_`]/g, "").trim();
    if (!pulito) {
        setStatus("ONLINE");
        return;
    }

    setStatus("SPEAKING");

    // divide il testo in frasi
    const frasi = dividiTesto(pulito);

    // prepara l'audio una frase alla volta, in fila, mentre si ascolta
    let catena = Promise.resolve();
    const audio = frasi.map(f => {
        const p = catena.then(() => caricaAudio(f));
        catena = p;
        return p;
    });

    for (const a of audio) {
        if (vocePausata) break;
        await riproduci(await a);
    }

    setStatus("ONLINE");
}


// ---------- CRONOLOGIA ----------

async function caricaCronologia() {
    let r = await fetch("/history");
    let dati = await r.json();
    let chat = document.getElementById("chat");

    chat.innerHTML = "";

    dati.history.forEach(msg => {
        if (msg.role === "user") {
            chat.innerHTML +=
                '<div class="user"><div class="bubble-user">'
                + msg.content +
                '</div></div>';
        } else {
            chat.innerHTML +=
                '<div class="jarvis"><div class="bubble-jarvis">'
                + msg.content +
                '</div></div>';
        }
    });

    chat.scrollTop = chat.scrollHeight;
}


// ---------- INVIO MESSAGGIO ----------

function scendiChat() {
    const chat = document.getElementById("chat");
    if (!chat) return;
    chat.scrollTop = chat.scrollHeight;
    requestAnimationFrame(() => {
        chat.scrollTop = chat.scrollHeight;
    });
}


async function invia() {
    let input = document.getElementById("msg");
    let testo = input.value;

    if (testo.trim() === "") {
        return;
    }

    let chat = document.getElementById("chat");

    chat.insertAdjacentHTML(
        "beforeend",
        '<div class="user"><div class="bubble-user">' + testo + '</div></div>'
    );
    scendiChat();

    input.value = "";
    setStatus("PROCESSING");

    let r = await fetch("/chat?message=" + encodeURIComponent(testo));
    let dati = await r.json();

    chat.insertAdjacentHTML(
        "beforeend",
        '<div class="jarvis"><div class="bubble-jarvis">' + dati.response + '</div></div>'
    );
    scendiChat();
    caricaLista();
    rimuoviDocumento();

    await speak(dati.response);
        finestraAscolto();
}


document.addEventListener("DOMContentLoaded", () => {
    bootJarvis();
    caricaCronologia();

    const input = document.getElementById("msg");

    if (input) {
        input.addEventListener("keypress", function (event) {
            if (event.key === "Enter") {
                invia();
            }
        });
    }
});


// ---------- ORECCHIO DI JARVIS (Whisper) ----------
// Primo click sul microfono: inizia a registrare.
// Secondo click: smette, trascrive e Jarvis risponde.

let mediaRecorder = null;
let audioChunks = [];
let registrando = false;

async function startListening() {

    if (!registrando) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = e => audioChunks.push(e.data);

            mediaRecorder.onstop = async () => {
                stream.getTracks().forEach(t => t.stop());
                const blob = new Blob(audioChunks, { type: "audio/webm" });
                await trascrivi(blob);
            };

            mediaRecorder.start();
            registrando = true;
            setStatus("LISTENING");

        } catch (err) {
            console.log(err);
            alert("Errore microfono: " + err.name);
            setStatus("ONLINE");
        }

    } else {
        mediaRecorder.stop();
        registrando = false;
        setStatus("PROCESSING");
    }
}


async function trascrivi(blob) {
    try {
        const form = new FormData();
        form.append("audio", blob, "voce.webm");

        const r = await fetch("/api/stt", { method: "POST", body: form });
        const dati = await r.json();

        if (!dati.text) {
            setStatus("ONLINE");
            return;
        }

        document.getElementById("msg").value = dati.text;
        await invia();

    } catch (err) {
        console.log("Errore trascrizione:", err);
        setStatus("ONLINE");
    }
}

// ---------- DATI DI SISTEMA ----------

async function aggiornaSistema() {
    try {
        const r = await fetch("/system");
        const d = await r.json();
        document.getElementById("cpu-val").innerText = Math.round(d.cpu) + " %";
        document.getElementById("ram-val").innerText = Math.round(d.ram) + " %";
    } catch (err) {
        console.log("Errore dati sistema:", err);
    }
}

setInterval(aggiornaSistema, 3000);
aggiornaSistema();

// ---------- ORA E METEO ----------

function aggiornaOra() {
    const adesso = new Date();
    const ora = adesso.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
    const data = adesso.toLocaleDateString("it-IT", { weekday: "short", day: "numeric", month: "short" });
    const el = document.getElementById("ora-val");
    if (el) el.innerText = ora + " · " + data;
}

async function aggiornaMeteo() {
    try {
        const r = await fetch("/weather");
        const d = await r.json();
        if (d.errore) return;
        document.getElementById("meteo-val").innerText =
            d.luogo + " · " + d.temp + "°C · " + d.descrizione;
    } catch (err) {
        console.log("Errore meteo:", err);
    }
}

setInterval(aggiornaOra, 10000);
aggiornaOra();

setInterval(aggiornaMeteo, 600000);
aggiornaMeteo();

// ---------- NEURONI ORBITANTI ----------

function creaNeuroni() {
    const core = document.querySelector(".jarvis-core");
    if (!core) return;

    const quanti = 14;
    const distanze = [-40, -25, -10, 15, 30, 55, 80];

    for (let i = 0; i < quanti; i++) {
        const orbita = document.createElement("div");
        orbita.className = "orbita";
        orbita.style.inset = distanze[i % distanze.length] + "px";

        const durata = 10 + Math.random() * 20;
        orbita.style.animationDuration = durata + "s";
        orbita.style.animationDelay = (-Math.random() * durata) + "s";
        if (i % 2) orbita.style.animationDirection = "reverse";

        const pallino = document.createElement("div");
        pallino.className = "neurone";
        orbita.appendChild(pallino);
        core.appendChild(orbita);
    }
}

creaNeuroni();

// ---------- STATO MEMORIA ----------

async function aggiornaMemoria() {
    try {
        const r = await fetch("/memory-stats");
        const d = await r.json();
        if (d.errore) return;
        document.getElementById("mem-val").innerText =
            d.ricordi + " ricordi · " + d.messaggi + " messaggi";
    } catch (err) {
        console.log("Errore memoria:", err);
    }
}

setInterval(aggiornaMemoria, 5000);
aggiornaMemoria();

// ---------- DOCUMENTI ----------

async function caricaDocumento(input) {
    const file = input.files[0];
    if (!file) return;

    const chip = document.getElementById("doc-chip");
    chip.style.display = "block";
    chip.innerText = "Leggo " + file.name + "...";

    try {
        const form = new FormData();
        form.append("file", file);
        const r = await fetch("/upload", { method: "POST", body: form });
        const d = await r.json();

        if (d.errore) {
            chip.innerText = d.errore;
            setTimeout(() => { chip.style.display = "none"; }, 4000);
        } else {
            chip.innerHTML = "📄 " + d.nome
                + (d.troncato ? " (letta solo la prima parte)" : "")
                + ' <span onclick="rimuoviDocumento()">✖</span>';
        }
    } catch (err) {
        console.log("Errore upload:", err);
        chip.innerText = "Errore nel caricamento.";
    }
    input.value = "";
}

async function rimuoviDocumento() {
    await fetch("/upload/clear", { method: "POST" });
    document.getElementById("doc-chip").style.display = "none";
}

// ---------- CONVERSAZIONI ----------

function toggleLista() {
    const lista = document.getElementById("chat-list");
    lista.style.display = (lista.style.display === "none") ? "block" : "none";
    if (lista.style.display === "block") caricaLista();
}

async function caricaLista() {
    try {
        const r = await fetch("/chats");
        const d = await r.json();
        const lista = document.getElementById("chat-list");
        lista.innerHTML = "";

        d.chats.forEach(c => {
            const riga = document.createElement("div");
            riga.className = "chat-item" + (c.id === d.attiva ? " attiva" : "");

            const titolo = document.createElement("span");
            titolo.textContent = c.titolo;
            titolo.onclick = () => apriChat(c.id);

            const cestino = document.createElement("button");
            cestino.textContent = "🗑";
            cestino.onclick = (e) => {
                e.stopPropagation();
                eliminaChat(c.id);
            };

            riga.appendChild(titolo);
            riga.appendChild(cestino);
            lista.appendChild(riga);
        });

        const att = d.chats.find(c => c.id === d.attiva);
        document.getElementById("chat-titolo").textContent =
            att ? att.titolo : "Nuova chat";
    } catch (err) {
        console.log("Errore lista chat:", err);
    }
}

async function cambiaChat() {
    document.getElementById("chat-list").style.display = "none";
    await caricaCronologia();
    await caricaLista();
}

async function apriChat(id) {
    await fetch("/chats/" + id + "/open", { method: "POST" });
    await cambiaChat();
}

async function nuovaChat() {
    await fetch("/chats/new", { method: "POST" });
    await rimuoviDocumento();
    await cambiaChat();
}

async function eliminaChat(id) {
    if (!confirm("Eliminare questa conversazione?")) return;
    await fetch("/chats/" + id, { method: "DELETE" });
    await cambiaChat();
}

caricaLista();

// ---------- WAKE WORD "Ciao Jarvis" ----------

let wakeAttivo = false;
let wakeRec = null;
let inAttesaComando = false;
let timerComando = null;

const WAKE = /(ciao|ehi|hey|ei)\s+(jarvis|giarvis|garvis|iarvis|jarves|jarvi)/;

function normalizza(t) {
    return t.toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-z0-9 ]/g, " ");
}

function inviaComandoVocale(testo) {
    inAttesaComando = false;
    clearTimeout(timerComando);
    document.getElementById("msg").value = testo.trim();
    invia();
}

function toggleWake() {
    const bottone = document.getElementById("wake-btn");

    if (wakeAttivo) {
        wakeAttivo = false;
        inAttesaComando = false;
        if (wakeRec) wakeRec.stop();
        bottone.classList.remove("attivo");
        bottone.innerText = "👂 Wake word: OFF";
        return;
    }

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
        alert("Questo browser non supporta il riconoscimento vocale. Usa Chrome.");
        return;
    }

    wakeRec = new SR();
    wakeRec.lang = "it-IT";
    wakeRec.continuous = true;
    wakeRec.interimResults = false;

    wakeRec.onresult = (e) => {
                const stato = document.body.dataset.stato;
        const ultimo = normalizza(e.results[e.results.length - 1][0].transcript).trim();
        if (stato === "SPEAKING" && /^(basta|stop|fermati|zitto|silenzio)\b/.test(ultimo)) {
            fermaVoce();
            return;
        }
        if (stato === "SPEAKING" || stato === "PROCESSING" || registrando) return;

        const originale = e.results[e.results.length - 1][0].transcript;
        const frase = normalizza(originale);

        // dopo "Ciao Jarvis" da solo: la frase successiva è il comando
        if (inAttesaComando) {
            if (originale.trim().length > 1) inviaComandoVocale(originale);
            return;
        }

        const m = frase.match(WAKE);
        if (!m) return;

        const resto = originale.slice(m.index + m[0].length).replace(/^[\s,.:;!?-]+/, "");
        if (resto.length > 2) {
            inviaComandoVocale(resto);
        } else {
            inAttesaComando = true;
            setStatus("LISTENING");
            timerComando = setTimeout(() => {
                inAttesaComando = false;
                setStatus("ONLINE");
            }, 8000);
        }
    };

    wakeRec.onerror = (e) => {
        if (e.error === "not-allowed" || e.error === "service-not-allowed") {
            wakeAttivo = false;
            bottone.classList.remove("attivo");
            bottone.innerText = "👂 Wake word: OFF";
            alert("Permesso microfono negato per la wake word.");
        }
    };

    // Chrome chiude l'ascolto dopo un po' di silenzio: lo riavviamo
    wakeRec.onend = () => {
        if (wakeAttivo) {
            setTimeout(() => {
                try { wakeRec.start(); } catch (err) {}
            }, 300);
        }
    };

    wakeAttivo = true;
    try { wakeRec.start(); } catch (err) {}
    bottone.classList.add("attivo");
    bottone.innerText = "👂 Wake word: ON";
}

// ---------- MICROFONO: TIENI PREMUTO ----------

(function collegaMic() {
    const vecchio = document.getElementById("mic-btn");
    if (!vecchio) return;

    // sostituisce il pulsante con una copia pulita: elimina ogni gestore doppio
    const mic = vecchio.cloneNode(true);
    mic.removeAttribute("onclick");
    vecchio.replaceWith(mic);

    let premuto = false;
    let avvio = false;   // il microfono si sta ancora aprendo

    mic.addEventListener("pointerdown", async (e) => {
        e.preventDefault();
        if (premuto || avvio || registrando) return;
        premuto = true;
        avvio = true;
        try { mic.setPointerCapture(e.pointerId); } catch (err) {}
        await startListening();          // apre il microfono e inizia a registrare
        avvio = false;
        // se hai già rilasciato mentre si apriva, ferma subito
        if (!premuto && registrando) startListening();
    });

    function rilascia() {
        if (!premuto) return;
        premuto = false;
        if (avvio) return;               // lo ferma il codice sopra, appena pronto
        if (registrando) startListening();   // ferma, trascrive, risponde
    }

    mic.addEventListener("pointerup", rilascia);
    mic.addEventListener("pointercancel", rilascia);
    mic.addEventListener("click", (e) => e.preventDefault());
    mic.addEventListener("contextmenu", (e) => e.preventDefault());
})();

// ---------- PROMEMORIA SCADUTI ----------

function beep() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.frequency.value = 880;
        gain.gain.value = 0.15;
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.4);
    } catch (err) {}
}

async function controllaPromemoria() {
    const boot = document.getElementById("boot-screen");
    if (boot && boot.style.display !== "none") return;

    const stato = document.body.dataset.stato;
    if (stato === "SPEAKING" || stato === "PROCESSING" ||
        stato === "LISTENING" || stato === "BOOT") return;

    try {
        const r = await fetch("/reminders/due");
        const d = await r.json();
        for (const testo of d.scaduti) {
            beep();
            const chat = document.getElementById("chat");
            chat.insertAdjacentHTML(
                "beforeend",
                '<div class="jarvis"><div class="bubble-jarvis">' + testo + '</div></div>'
            );
            scendiChat();
            await speak(testo);
        }
    } catch (err) {
        console.log("Errore promemoria:", err);
    }
}

setInterval(controllaPromemoria, 5000);

// ---------- CONVERSAZIONE CONTINUA ----------

function finestraAscolto() {
    // dopo una risposta, per 8 secondi la wake word non serve
    if (!wakeAttivo) return;
    inAttesaComando = true;
    clearTimeout(timerComando);
    timerComando = setTimeout(() => {
        inAttesaComando = false;
        if (document.body.dataset.stato === "ONLINE") setStatus("ONLINE");
    }, 8000);
}