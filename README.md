# Calendario Albo Pretorio – Comune di Palestrina

Consultazione a calendario degli atti dell'Albo Pretorio del Comune di Palestrina (ordinanze, delibere, determine, convocazioni, autorizzazioni, avvisi, pubblicazioni di matrimonio), ognuno con il suo colore. Selezionando un giorno si apre la pagina con tutti i dettagli degli atti e il link all'atto originale con gli allegati.

Si aggiorna da solo tre volte al giorno, gratis, usando GitHub.

## Cosa c'è dentro

| File | A cosa serve |
|---|---|
| `docs/index.html` | Il sito (calendario + pagina del giorno) |
| `docs/data/atti.json` | Gli atti letti dall'albo (si riempie ogni giorno, i vecchi atti restano in archivio) |
| `docs/calendario.ics` | Tutti gli atti in formato calendario, per Google Calendar |
| `docs/calendario-ordinanze.ics` | Solo le ordinanze |
| `scripts/aggiorna_albo.py` | Lo script che legge l'albo e aggiorna i file qui sopra |
| `.github/workflows/aggiorna-albo.yml` | L'orario dell'aggiornamento automatico |

## Messa online, passo passo (circa 10 minuti)

1. **Crea un account** su [github.com](https://github.com) (gratis), se non lo hai già.
2. **Crea un repository**: in alto a destra `+` → *New repository*. Nome: `albo-palestrina`. Scegli **Public** (le Pagine gratuite funzionano solo con i repository pubblici). Clicca *Create repository*.
3. **Carica i file**: nella pagina del repository clicca *uploading an existing file*, poi trascina nella finestra **il contenuto** della cartella estratta dallo zip (le cartelle `docs`, `scripts`, `.github` e il file `README.md`). Clicca *Commit changes*.
   - La cartella `.github` su Mac e Windows può essere nascosta. Se dopo il caricamento non la vedi nel repository: *Add file* → *Create new file*, come nome scrivi `.github/workflows/aggiorna-albo.yml`, incolla il contenuto del file con lo stesso nome che trovi nello zip e salva.
4. **Dai il permesso di aggiornare i file**: *Settings* → *Actions* → *General* → in fondo, *Workflow permissions* → seleziona **Read and write permissions** → *Save*.
5. **Accendi il sito**: *Settings* → *Pages* → *Source: Deploy from a branch* → Branch **main**, cartella **/docs** → *Save*.
6. **Primo aggiornamento a mano**: scheda *Actions* → *Aggiorna albo pretorio* → *Run workflow*. Dopo un minuto deve comparire la spunta verde.
7. **Apri il sito** (dopo 1-2 minuti): `https://TUO-NOME-UTENTE.github.io/albo-palestrina/`
   Salvalo nei preferiti o sulla schermata Home del telefono (Safari: *Condividi → Aggiungi alla schermata Home*; Chrome: *⋮ → Aggiungi a schermata Home*).

Da qui in poi non serve fare più nulla: alle 7, alle 13 e alle 19 (circa) GitHub legge l'albo e aggiorna il sito.

## Vederlo dentro Google Calendar (facoltativo)

In fondo al sito c'è il link **Aggiungi tutto a Google Calendar**. In alternativa, da computer: Google Calendar → *Altri calendari* `+` → *Da URL* → incolla
`https://TUO-NOME-UTENTE.github.io/albo-palestrina/calendario.ics`

Google ricarica i calendari esterni ogni qualche ora, quindi le novità possono comparire con un po' di ritardo rispetto al sito. Per le sole ordinanze usa `calendario-ordinanze.ics`.

## Come si legge il calendario

- **Casella piena colorata**: atto pubblicato all'albo quel giorno.
- **Casella con il solo bordo**: evento *in programma* quel giorno, ricavato dalla data scritta nell'atto (es. un'ordinanza di chiusura strada per il 4 novembre compare anche il 4 novembre).
- I bottoni colorati in alto sono anche filtri: toccali per nascondere o mostrare un tipo di atto. La casella *Cerca* trova vie, uffici o parole.
- Sul telefono il mese diventa una griglia a pallini colorati con sotto l'elenco dei giorni.

L'albo online mostra solo gli atti in pubblicazione (di solito 15 giorni). Il calendario invece li conserva: più giorni passano, più lo storico si riempie.

## Se qualcosa non va

- **Croce rossa nella scheda Actions**: apri l'esecuzione e leggi l'ultima riga. Se il sito del Comune era irraggiungibile, il turno successivo di solito va a buon fine; i dati già salvati non vengono mai cancellati.
- **GitHub sospende gli aggiornamenti** di un repository pubblico rimasto senza attività per 60 giorni. Se succede, nella scheda *Actions* compare un avviso con il pulsante per riattivarlo.
- **Aggiornare a mano dal computer** (serve Python 3): `python3 scripts/aggiorna_albo.py`. Oppure, se hai già scaricato l'export CSV dal sito dell'albo (pulsante *Esporta*): `python3 scripts/aggiorna_albo.py --da-file export.csv`.

Fonte dei dati: [Albo Pretorio del Comune di Palestrina](https://palestrina.trasparenza-valutazione-merito.it/web/trasparenza/dettaglio-albo-pretorio). Il calendario è una consultazione di comodo: per gli effetti legali fa fede l'atto pubblicato sul sito del Comune.
