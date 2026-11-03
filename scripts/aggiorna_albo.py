#!/usr/bin/env python3
"""
Legge l'Albo Pretorio del Comune di Palestrina e aggiorna:
  docs/data/atti.json              -> dati per il calendario del sito
  docs/calendario.ics              -> tutti gli atti (da aggiungere a Google Calendar)
  docs/calendario-ordinanze.ics    -> solo le ordinanze

Usa solo la libreria standard di Python. Gli atti già salvati restano nello
storico anche quando escono dall'albo, così il calendario si arricchisce ogni giorno.

Uso:
  python scripts/aggiorna_albo.py                 # scarica dal sito del Comune
  python scripts/aggiorna_albo.py --da-file x.csv  # usa un export CSV già scaricato
"""
import csv
import http.cookiejar
import io
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = "https://palestrina.trasparenza-valutazione-merito.it"
# Pagina con l'elenco dell'albo (è quella caricata nel riquadro della pagina ufficiale).
URL_ELENCO = BASE + "/web/trasparenza/papca-ap/-/papca/igrid/30251/19270"
# Pulsante "Esporta in OpenFormat" (CSV) dell'elenco: funziona nella stessa sessione dell'elenco.
URL_CSV = (
    BASE + "/web/trasparenza/papca-ap?p_p_id=jcitygovalbopubblicazioni_WAR_jcitygovalbiportlet"
    "&p_p_lifecycle=2&p_p_state=pop_up&p_p_mode=view&p_p_resource_id=exportList"
    "&p_p_cacheability=cacheLevelPage"
    "&_jcitygovalbopubblicazioni_WAR_jcitygovalbiportlet_format=csv"
    "&_jcitygovalbopubblicazioni_WAR_jcitygovalbiportlet_action=mostraLista"
    "&_jcitygovalbopubblicazioni_WAR_jcitygovalbiportlet_fromAction=eseguiFiltro"
)
UA = "Mozilla/5.0 (calendario albo pretorio Palestrina; aggiornamento giornaliero)"

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DATA_FILE = DOCS / "data" / "atti.json"

# Gruppi di colore (stesse chiavi usate dal sito)
GRUPPI = [
    ("ordinanza", "Ordinanze", ["ORDINANZ"]),
    ("delibera", "Delibere", ["DELIBER"]),
    ("determina", "Determine", ["DETERMIN"]),
    ("autorizzazione", "Autorizzazioni e permessi", ["AUTORIZZ", "PERMESS", "CONCESSION", "VINCOLO", "PAESAGGIST"]),
    ("convocazione", "Convocazioni", ["CONVOCAZ", "COMMISSION", "CONSIGLIO COMUNALE"]),
    ("avviso", "Avvisi e manifesti", ["AVVIS", "MANIFEST", "BANDO", "GARA", "CONCORS"]),
    ("matrimonio", "Pubblicazioni di matrimonio", ["MATRIMONI"]),
    ("altro", "Altri atti", []),
]


SINGOLARE = {"DETERMINE": "Determina", "ORDINANZE": "Ordinanza", "DELIBERE DI GIUNTA": "Delibera di Giunta",
             "DELIBERE DI CONSIGLIO": "Delibera di Consiglio", "PUBBLICAZIONI DI MATRIMONIO": "Pubblicazione di matrimonio",
             "CONVOCAZIONE CONSIGLIO COMUNALE": "Convocazione Consiglio comunale",
             "CONVOCAZIONE COMMISSIONI": "Convocazione commissione", "AUTORIZZAZIONE": "Autorizzazione",
             "VINCOLO IDROGEOLOGICO": "Vincolo idrogeologico", "AVVISO PUBBLICO": "Avviso pubblico",
             "AVVISO DEPOSITO": "Avviso di deposito", "MANIFESTO": "Manifesto"}


def nome_tipo(categoria, sottocategoria):
    t = (sottocategoria or categoria or "Atto").upper()
    return SINGOLARE.get(t, t.capitalize())


def gruppo_di(categoria, sottocategoria):
    testo = f"{sottocategoria} {categoria}".upper()
    for chiave, _, parole in GRUPPI:
        if any(p in testo for p in parole):
            return chiave
    return "altro"


# ---------------------------------------------------------------- download
URL_PAGINA_SUCC = (
    BASE + "/web/trasparenza/papca-ap?p_p_id=jcitygovalbopubblicazioni_WAR_jcitygovalbiportlet"
    "&p_p_lifecycle=0&p_p_state=pop_up&p_p_mode=view"
    "&_jcitygovalbopubblicazioni_WAR_jcitygovalbiportlet_paginationAction=NEXT"
    "&_jcitygovalbopubblicazioni_WAR_jcitygovalbiportlet_action=mostraLista"
)


def nuova_sessione():
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", UA), ("Accept-Language", "it-IT,it;q=0.9")]
    return opener


def scarica_csv(tentativi=3):
    """Metodo principale: apre l'elenco (crea la sessione) e scarica l'export CSV completo."""
    ultimo_errore = None
    for n in range(1, tentativi + 1):
        try:
            opener = nuova_sessione()
            elenco = opener.open(URL_ELENCO, timeout=60).read().decode("utf-8", "replace")
            testo = opener.open(URL_CSV, timeout=60).read().decode("utf-8-sig")
            return testo, elenco, opener
        except Exception as e:                                   # rete, timeout, ecc.
            ultimo_errore = repr(e)
        time.sleep(10 * n)
    raise RuntimeError(f"Impossibile scaricare l'albo: {ultimo_errore}")


RE_RIGA = re.compile(r'<tr class="master-detail-list-line[^"]*" data-id="(\d+)">(.*?)</tr>', re.S)


def _cella(html, classe):
    m = re.search(r'<td[^>]*class="' + classe + r'[^"]*"[^>]*>(.*?)</td>', html, re.S)
    if not m:
        return ""
    t = re.sub(r"<br\s*/?>", "\n", m.group(1))
    t = re.sub(r"<[^>]+>", " ", t)
    import html as _h
    return _h.unescape(t).strip()


def righe_da_elenco(html):
    """Ricava gli atti dalla pagina HTML dell'elenco (metodo di riserva)."""
    righe = []
    for ident, corpo in RE_RIGA.findall(html):
        reg = _cella(corpo, "annonumeroregistrazione")
        cat = [re.sub(r"\s+", " ", x).strip(" /") for x in _cella(corpo, "categoria").split("\n")]
        periodo = re.findall(r"\d{2}/\d{2}/\d{4}", _cella(corpo, "periodo-pubblicazione"))
        anno, _, num = reg.partition("/")
        righe.append({
            "Oggetto": _cella(corpo, "oggetto"),
            "Titolo categoria": cat[0] if cat else "",
            "Titolo sottocategoria": cat[1] if len(cat) > 1 else "",
            "Anno registrazione": anno, "Numero registrazione": num,
            "Data inizio pubblicazione": periodo[0] if periodo else "",
            "Data fine pubblicazione": periodo[1] if len(periodo) > 1 else "",
            "Url atto": f"{BASE}/web/trasparenza/papca-ap/-/papca/display/{ident}",
        })
    return righe


def scarica_da_elenco(elenco, opener, max_pagine=40):
    righe, visti = [], set()
    pagina = elenco
    for _ in range(max_pagine):
        nuove = [r for r in righe_da_elenco(pagina) if r["Url atto"] not in visti]
        if not nuove:
            break
        for r in nuove:
            visti.add(r["Url atto"])
        righe += nuove
        time.sleep(1)
        pagina = opener.open(URL_PAGINA_SUCC, timeout=60).read().decode("utf-8", "replace")
    return righe


def leggi_albo():
    """Restituisce le righe dell'albo: CSV completo se disponibile, altrimenti l'elenco pagina per pagina."""
    testo, elenco, opener = scarica_csv()
    righe = [r for r in csv.DictReader(io.StringIO(testo)) if (r.get("Oggetto") or "").strip()]
    in_elenco = len(righe_da_elenco(elenco))
    # L'elenco mostra 20 atti per pagina: se il CSV ne ha meno di una pagina piena, è incompleto.
    if righe and len(righe) >= in_elenco:
        return righe, "csv"
    print(f"Export CSV incompleto ({len(righe)} atti): leggo l'elenco pagina per pagina.")
    return scarica_da_elenco(elenco, opener), "elenco"


# ---------------------------------------------------------------- pulizia testi
MINUSCOLE = {"di", "del", "della", "dello", "dei", "degli", "delle", "da", "dal", "dalla", "in", "nel",
             "nella", "nei", "e", "ed", "a", "al", "alla", "ai", "agli", "per", "con", "su", "sul",
             "sulla", "tra", "fra", "il", "lo", "la", "i", "gli", "le", "un", "una", "o"}


def frase(testo):
    """MAIUSCOLO -> Maiuscola iniziale, conservando sigle brevi."""
    t = re.sub(r"\s+", " ", (testo or "").replace("’", "'")).strip()
    t = re.sub(r"\s*\[[^\]]*\|[^\]]*\]", "", t)          # codici di protocollo tra parentesi quadre
    t = re.sub(r"[\s.\-–]+$", "", t)
    if not t:
        return ""
    if t.upper() != t:          # già scritto in maiuscolo/minuscolo misto
        return t
    parole = []
    for i, w in enumerate(t.lower().split(" ")):
        parole.append(w)
    out = " ".join(parole)
    out = out[0].upper() + out[1:]
    # Maiuscole dopo il punto e nelle vie/piazze più comuni
    out = re.sub(r"([.;:]\s+)([a-zà-ù])", lambda m: m.group(1) + m.group(2).upper(), out)
    out = re.sub(r"\b(via|viale|piazza|piazzale|largo|vicolo|località|loc\.|corso|parco|frazione di)\s+([a-zà-ù'])",
                 lambda m: m.group(1) + " " + m.group(2).upper(), out)
    out = re.sub(r"\b(palestrina|carchitti|barberini|cingolani|lazio)\b", lambda m: m.group(1).capitalize(), out)
    out = re.sub(r"\b(vta|n\.)\b", lambda m: m.group(1).upper() if m.group(1) == "vta" else m.group(1), out)
    return out


def titolo_breve(oggetto, gruppo, tipo=""):
    """Descrizione parlante e corta per la casella del calendario."""
    o = frase(oggetto)
    if not o:
        return tipo or "Atto senza oggetto"
    if gruppo == "matrimonio":
        m = re.search(r"n\.?\s*(\d+)", o)
        return "Pubblicazione di matrimonio" + (f" (atto n. {m.group(1)})" if m else "")
    if gruppo == "convocazione" and o.lower().startswith("consiglio comunale"):
        return "Convocazione del " + o[0].lower() + o[1:]
    m = re.search(r"^(.*?);\s*nuova disciplina (?:temporanea|permanente) della viabilit[aà]'?\s*(.*)$", o, re.I)
    if m:
        motivo = re.sub(r"\s*-\s*data\s+\d{1,2}/\d{1,2}/\d{4}", "", m.group(1), flags=re.I).strip(" .-")
        dove = m.group(2).strip(" .-")
        dove = re.sub(r"^(in|nel|nella|nei|sulla|sul)\s+", "", dove, flags=re.I)
        if len(dove) < 3:
            return f"Nuova viabilità: {motivo}"
        return f"Viabilità modificata: {dove[:1].upper() + dove[1:]} ({motivo[:1].lower() + motivo[1:]})"
    o = re.sub(r"\.\s*impegno di spesa$", " – impegno di spesa", o, flags=re.I)
    return o


RE_DATA = re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b")


def iso(data_it):
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})", data_it or "")
    if not m:
        return ""
    g, me, a = (int(x) for x in m.groups())
    try:
        return datetime(a, me, g).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def date_citate(oggetto):
    """Date scritte nell'oggetto (es. 'DATA 4/11/2026', 'DAL 5/11/2026 AL 7/11/2026')."""
    trovate = []
    for g, m, a in RE_DATA.findall(oggetto or ""):
        try:
            trovate.append(datetime(int(a), int(m), int(g)))
        except ValueError:
            pass
    giorni = set()
    if len(trovate) == 2 and re.search(r"\bdal\b.*\bal\b", oggetto or "", re.I) and trovate[0] <= trovate[1] \
            and (trovate[1] - trovate[0]).days <= 60:
        d = trovate[0]
        while d <= trovate[1]:
            giorni.add(d.strftime("%Y-%m-%d"))
            d += timedelta(days=1)
    else:
        giorni.update(d.strftime("%Y-%m-%d") for d in trovate)
    return sorted(giorni)


def numero_euro(s):
    try:
        return float((s or "0").replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


def atto_da_riga(r):
    url = (r.get("Url atto") or "").strip()
    m = re.search(r"/display/(\d+)", url)
    ident = m.group(1) if m else f"{r.get('Anno registrazione')}-{r.get('Numero registrazione')}"
    categoria = re.sub(r"\s+", " ", r.get("Titolo categoria") or "").strip()
    sottocat = re.sub(r"\s+", " ", r.get("Titolo sottocategoria") or "").strip()
    g = gruppo_di(categoria, sottocat)
    oggetto = re.sub(r"\s+", " ", r.get("Oggetto") or "").strip()
    return {
        "id": ident,
        "gruppo": g,
        "categoria": categoria,
        "tipo": nome_tipo(categoria, sottocat),
        "numero_atto": (r.get("Numero") or "").strip(),
        "anno_atto": (r.get("Anno") or "").strip(),
        "registro": f"{(r.get('Numero registrazione') or '').strip()}/{(r.get('Anno registrazione') or '').strip()}",
        "titolo": titolo_breve(oggetto, g, nome_tipo(categoria, sottocat)),
        "oggetto": frase(oggetto) or "(oggetto non indicato nell'albo: aprire l'atto)",
        "ufficio": (r.get("Proponente descrizione") or "").strip(),
        "firmatario": (r.get("Dirigente descrizione") or "").strip(),
        "data_atto": iso(r.get("Data atto") or r.get("Data documento")),
        "data_esecutivita": iso(r.get("Data esecutività")),
        "pubblicato_dal": iso(r.get("Data inizio pubblicazione")),
        "pubblicato_al": iso(r.get("Data fine pubblicazione")),
        "allegati": int((r.get("Numero allegati") or "0").strip() or 0),
        "spesa": numero_euro(r.get("Spesa prevista")),
        # Date di eventi citate nell'oggetto (lavori, chiusure, sedute): solo dove hanno senso
        "date_citate": date_citate(oggetto) if g in ("ordinanza", "convocazione", "avviso") else [],
        "url": url,
    }


# ---------------------------------------------------------------- calendari .ics
def ics_testo(s):
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics_riga(riga):
    """Piega le righe a 75 ottetti come richiede lo standard iCalendar."""
    b = riga.encode("utf-8")
    if len(b) <= 75:
        return riga + "\r\n"
    parti, corrente = [], b""
    for ch in riga:
        c = ch.encode("utf-8")
        limite = 75 if not parti else 74
        if len(corrente) + len(c) > limite:
            parti.append(corrente)
            corrente = b""
        corrente += c
    parti.append(corrente)
    return "\r\n ".join(p.decode("utf-8") for p in parti) + "\r\n"


ETICHETTE = {k: n for k, n, _ in GRUPPI}


def scrivi_ics(atti, percorso, nome, solo=None):
    adesso = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    righe = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//albo-palestrina//calendario//IT",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", f"X-WR-CALNAME:{ics_testo(nome)}",
             "X-WR-TIMEZONE:Europe/Rome", "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
             "X-PUBLISHED-TTL:PT6H"]
    for a in atti:
        if solo and a["gruppo"] not in solo:
            continue
        dettagli = [
            f"{a['tipo']} n. {a['numero_atto']}/{a['anno_atto']} (registro albo {a['registro']})",
            a["oggetto"],
            f"Ufficio: {a['ufficio']}" if a["ufficio"] else "",
            f"Firmatario: {a['firmatario']}" if a["firmatario"] else "",
            f"In pubblicazione dal {a['pubblicato_dal']} al {a['pubblicato_al']}",
            f"Atto e documenti: {a['url']}",
        ]
        descr = "\n".join(x for x in dettagli if x)
        eventi = []
        if a["pubblicato_dal"]:
            eventi.append(("pub", a["pubblicato_dal"], f"{a['tipo']}: {a['titolo']}"))
        for d in a["date_citate"]:
            if d != a["pubblicato_dal"]:
                eventi.append((f"g{d}", d, f"In programma ({a['tipo'].lower()}): {a['titolo']}"))
        for suff, giorno, titolo in eventi:
            inizio = giorno.replace("-", "")
            fine = (datetime.strptime(giorno, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d")
            righe += ["BEGIN:VEVENT", f"UID:{a['id']}-{suff}@albo-palestrina", f"DTSTAMP:{adesso}",
                      f"DTSTART;VALUE=DATE:{inizio}", f"DTEND;VALUE=DATE:{fine}",
                      f"SUMMARY:{ics_testo(titolo)}", f"DESCRIPTION:{ics_testo(descr)}",
                      f"URL:{a['url']}", f"CATEGORIES:{ics_testo(ETICHETTE.get(a['gruppo'], 'Altri atti'))}",
                      "TRANSP:TRANSPARENT", "END:VEVENT"]
    righe.append("END:VCALENDAR")
    percorso.write_text("".join(ics_riga(r) for r in righe), encoding="utf-8")


# ---------------------------------------------------------------- main
def main():
    if "--da-file" in sys.argv:
        f = Path(sys.argv[sys.argv.index("--da-file") + 1])
        testo = f.read_text(encoding="utf-8-sig")
        if f.suffix.lower() in (".html", ".htm"):
            righe, metodo = righe_da_elenco(testo), "elenco"
        else:
            righe, metodo = [r for r in csv.DictReader(io.StringIO(testo)) if (r.get("Oggetto") or "").strip()], "csv"
    else:
        righe, metodo = leggi_albo()

    nuovi = [atto_da_riga(r) for r in righe]
    if not nuovi:
        sys.exit("Nessun atto letto: non aggiorno i file per non perdere i dati.")

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    archivio = {}
    if DATA_FILE.exists():
        try:
            archivio = {a["id"]: a for a in json.loads(DATA_FILE.read_text(encoding="utf-8"))["atti"]}
        except Exception:
            archivio = {}
    oggi = datetime.now(timezone(timedelta(hours=1))).strftime("%Y-%m-%d")
    for a in nuovi:
        vecchio = archivio.get(a["id"], {})
        for k, v in vecchio.items():          # se oggi i dati sono meno ricchi, tengo quelli già salvati
            if a.get(k) in ("", None, 0, []) and v not in ("", None, 0, []):
                a[k] = v
        a["visto_la_prima_volta"] = vecchio.get("visto_la_prima_volta", oggi)
        archivio[a["id"]] = a

    atti = sorted(archivio.values(), key=lambda a: (a["pubblicato_dal"], a["registro"]), reverse=True)
    aggiornato = datetime.now(timezone.utc).isoformat(timespec="minutes")
    DATA_FILE.write_text(json.dumps({
        "aggiornato": aggiornato,
        "fonte": URL_ELENCO,
        "gruppi": [{"chiave": k, "nome": n} for k, n, _ in GRUPPI],
        "atti": atti,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    scrivi_ics(atti, DOCS / "calendario.ics", "Albo Pretorio Palestrina – tutti gli atti")
    scrivi_ics(atti, DOCS / "calendario-ordinanze.ics", "Albo Pretorio Palestrina – ordinanze",
               solo={"ordinanza"})
    print(f"OK ({metodo}): {len(nuovi)} atti letti oggi, {len(atti)} nell'archivio.")


if __name__ == "__main__":
    main()
