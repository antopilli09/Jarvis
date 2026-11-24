"""Avvia il server di Jarvis usando le impostazioni del file .env."""
import os

import uvicorn

from config import BASE_DIR, HOST, PORT, SSL_CERTFILE, SSL_KEYFILE


def _percorso(p):
    if not p:
        return None
    return p if os.path.isabs(p) else str(BASE_DIR / p)


if __name__ == "__main__":
    key, cert = _percorso(SSL_KEYFILE), _percorso(SSL_CERTFILE)
    uvicorn.run(
        "server:app",
        host=HOST,
        port=PORT,
        ssl_keyfile=key if key and cert else None,
        ssl_certfile=cert if key and cert else None,
    )
