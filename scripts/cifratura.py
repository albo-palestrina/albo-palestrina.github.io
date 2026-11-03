#!/usr/bin/env python3
"""
Cifratura dei dati del calendario e gestione degli accessi.

I dati pubblicati sul sito sono cifrati (AES-256-GCM) con una chiave segreta
custodita su GitHub come segreto ALBO_CHIAVE. Il sito la sblocca solo con
utente e password corretti: per ogni utente, docs/data/accesso.json contiene
la chiave cifrata con una chiave derivata da utente e password (PBKDF2-SHA256).

Aggiungere o cambiare un utente (serve la chiave):
  ALBO_CHIAVE=... python3 scripts/cifratura.py utente "password"
Togliere un utente:
  python3 scripts/cifratura.py --rimuovi utente
"""
import base64
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITERAZIONI = 310000
ACCESSO = Path(__file__).resolve().parent.parent / "docs" / "data" / "accesso.json"


def _b64(b):
    return base64.b64encode(b).decode("ascii")


def _d64(s):
    return base64.b64decode(s)


def chiave_da_ambiente():
    valore = os.environ.get("ALBO_CHIAVE", "").strip()
    if not valore:
        sys.exit("Manca il segreto ALBO_CHIAVE (Settings > Secrets and variables > Actions).")
    chiave = _d64(valore)
    if len(chiave) != 32:
        sys.exit("ALBO_CHIAVE non valida: deve essere una chiave di 32 byte in base64.")
    return chiave


def cifra_json(oggetto, chiave):
    chiaro = gzip.compress(json.dumps(oggetto, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), mtime=0)
    iv = os.urandom(12)
    return {"v": 1, "iv": _b64(iv), "dati": _b64(AESGCM(chiave).encrypt(iv, chiaro, None))}


def decifra_json(scatola, chiave):
    chiaro = AESGCM(chiave).decrypt(_d64(scatola["iv"]), _d64(scatola["dati"]), None)
    return json.loads(gzip.decompress(chiaro).decode("utf-8"))


def _id_utente(utente):
    return hashlib.sha256(utente.strip().lower().encode("utf-8")).hexdigest()


def _segreto(utente, password):
    return (utente.strip().lower() + "\n" + password).encode("utf-8")


def voce_accesso(utente, password, chiave):
    sale = os.urandom(16)
    kek = hashlib.pbkdf2_hmac("sha256", _segreto(utente, password), sale, ITERAZIONI, 32)
    iv = os.urandom(12)
    return {"iterazioni": ITERAZIONI, "sale": _b64(sale), "iv": _b64(iv),
            "chiave": _b64(AESGCM(kek).encrypt(iv, chiave, None))}


def _leggi_accessi():
    if ACCESSO.exists():
        return json.loads(ACCESSO.read_text(encoding="utf-8"))
    return {"v": 1, "utenti": {}}


def _scrivi_accessi(dati):
    ACCESSO.parent.mkdir(parents=True, exist_ok=True)
    ACCESSO.write_text(json.dumps(dati, indent=1), encoding="utf-8")


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--rimuovi":
        dati = _leggi_accessi()
        dati["utenti"].pop(_id_utente(sys.argv[2]), None)
        _scrivi_accessi(dati)
        print(f"Utente rimosso. Utenti attivi: {len(dati['utenti'])}")
        return
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    utente, password = sys.argv[1], sys.argv[2]
    if len(password) < 10:
        sys.exit("Password troppo corta: usarne una di almeno 10 caratteri.")
    dati = _leggi_accessi()
    dati["utenti"][_id_utente(utente)] = voce_accesso(utente, password, chiave_da_ambiente())
    _scrivi_accessi(dati)
    print(f"Accesso salvato. Utenti attivi: {len(dati['utenti'])}")


if __name__ == "__main__":
    main()
