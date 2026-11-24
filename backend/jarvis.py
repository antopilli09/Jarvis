import json
from ollama import chat

from config import DATA_DIR, OLLAMA_MODEL, USER_NAME

MEMORY_FILE = DATA_DIR / "memory.json"

def carica_memoria():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"ricordi": []}

def salva_memoria(memoria):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memoria, f, ensure_ascii=False, indent=2)

memoria = carica_memoria()

print("Jarvis avviato.")
print("Comandi:")
print("- ricorda: <testo>")
print("- esci\n")

while True:

    domanda = input("Tu: ")

    if domanda.lower() == "esci":
        break

    if domanda.lower().startswith("ricorda:"):
        ricordo = domanda[9:].strip()

        memoria["ricordi"].append(ricordo)
        salva_memoria(memoria)

        print("\nJarvis:")
        print("Memorizzato.")
        print()

        continue

    contesto = "\n".join(memoria["ricordi"])

    risposta = chat(
        model=OLLAMA_MODEL,
        messages=[
            {
                "role": "system",
                "content": f"""
Sei Jarvis, assistente personale di {USER_NAME}.

Non dire mai di essere Qwen.

Questi sono i ricordi che conosci:

{contesto}

Rispondi in italiano.
"""
            },
            {
                "role": "user",
                "content": domanda
            }
        ]
    )

    print("\nJarvis:")
    print(risposta.message.content)
    print()