# Calendario Albo Pretorio – Comune di Palestrina

Consultazione a calendario degli atti dell'Albo Pretorio online del Comune di Palestrina (ordinanze, delibere, determine, convocazioni, autorizzazioni, avvisi, pubblicazioni di matrimonio), ognuno con il suo colore. Selezionando un giorno si apre la pagina con i dettagli degli atti e il link all'atto originale con gli allegati.

Indirizzo: **https://albo-palestrina.github.io/**

Strumento di consultazione non ufficiale: per ogni effetto di legge fa fede la pubblicazione sull'[Albo Pretorio online del Comune di Palestrina](https://palestrina.trasparenza-valutazione-merito.it/web/trasparenza/dettaglio-albo-pretorio).

## Accesso

Il sito chiede utente e password. I dati pubblicati sono cifrati (AES-256-GCM): senza credenziali valide non sono leggibili, nemmeno aprendo direttamente i file.

Con *Ricorda l'accesso su questo dispositivo* il browser resta collegato finché non si preme **Esci**. Sui computer condivisi conviene togliere la spunta.

## Come funziona

| File | A cosa serve |
|---|---|
| `docs/index.html` | Il sito (accesso, calendario, pagina del giorno) |
| `docs/data/atti.enc.json` | Gli atti letti dall'albo, cifrati. Si aggiorna da solo; i vecchi atti restano in archivio |
| `docs/data/accesso.json` | Gli utenti abilitati (contiene solo dati cifrati, nessuna password) |
| `scripts/aggiorna_albo.py` | Legge l'albo e rigenera i dati cifrati |
| `scripts/cifratura.py` | Cifratura e gestione degli utenti |
| `.github/workflows/aggiorna-albo.yml` | Aggiornamento automatico verso le 7, le 13 e le 19 |

La chiave di cifratura è salvata nel segreto del repository **ALBO_CHIAVE** (*Settings → Secrets and variables → Actions*). Non va mai scritta nei file del repository. Se si perde, si genera una chiave nuova e si ricreano gli utenti.

## Gestione utenti

Serve Python 3 con il pacchetto `cryptography` e la chiave ALBO_CHIAVE.

- Aggiungere un utente o cambiare la password:
  `ALBO_CHIAVE=... python3 scripts/cifratura.py nomeutente "password"`
- Togliere un utente:
  `python3 scripts/cifratura.py --rimuovi nomeutente`

Poi caricare su GitHub il file `docs/data/accesso.json` aggiornato.

## Se qualcosa non va

- **Croce rossa nella scheda Actions**: aprire l'esecuzione e leggere l'ultima riga. Se il sito del Comune era irraggiungibile, il turno successivo di solito va a buon fine; i dati già salvati non vengono cancellati. "Manca il segreto ALBO_CHIAVE" significa che il segreto non è impostato.
- **GitHub sospende gli aggiornamenti** dei repository senza attività per 60 giorni: nella scheda *Actions* compare il pulsante per riattivarli.
- **Aggiornamento manuale**: scheda *Actions* → *Aggiorna albo pretorio* → *Run workflow*.
