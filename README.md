# CHMI_MapOnly

![Náhled aplikace](docs/screenshot.png)

Webový prohlížeč radarových dat ČHMÚ pro Českou republiku – animace posledních
hodin pozorování plus krátkodobá radarová předpověď, vykreslené přes mapu
OpenStreetMap. Volitelně lze do mapy zapnout i pozemní pozorování ze stanic
ČHMÚ (teplota, vítr, vlhkost, tlak) jako popisky synchronizované s animací.

## Co projekt dělá

Aplikace má dvě části:

- **Downloader** (`chmi_radar.main`) – běží ve smyčce a v pravidelném intervalu
  stahuje z [ČHMÚ open data](https://opendata.chmi.cz/):
  - radarové snímky `maxz` (kompozit max. odrazivosti) za posledních `hours_back`
    hodin, po 5 minutách,
  - nejnovější radarovou předpověď (`fct_maxz`, .tar archiv, který se rozbalí),
  - pozemní pozorování ze stanic ČHMÚ (`climate/now`, 10minutová data českých
    stanic) a z nich poskládá agregát `stations/stations.json` s časovými
    řadami teploty (`T`), vlhkosti (`H`), tlaku (`P`) a větru (`F`, `D`) za
    posledních `hours_back` hodin.

  Zároveň uklízí data starší než `hours_back` a ponechává jen nejnovější běh
  předpovědi.

- **Viewer** (`chmi_radar.serve`) – jednoduchý HTTP server (stdlib `http.server`),
  který:
  - servíruje `web/viewer.html` a statické soubory Leaflet,
  - na endpointu `/frames` vrací JSON se seznamem snímků (radar + navazující
    předpověď),
  - na endpointu `/stations.json` vrací agregát pozorování ze stanic (tentýž
    soubor slouží i jako odkaz „⬇ data stanic" ke stažení),
  - servíruje samotné PNG z adresářů `radar/` a `forecast/`.

  Frontend (Leaflet) snímky animuje jako overlay nad mapou OSM – tlačítko
  přehrávání, posuvník (modrá = pozorování, oranžová = předpověď), volba
  rozsahu zobrazeného pozorování, rychlosti a průhlednosti. Checkboxy „stanice"
  (teplota / vítr / vlhkost / tlak) zapínají popisky stanic, jejichž hodnoty se
  mění podle času zobrazeného snímku (u snímků předpovědi drží poslední
  pozorování). Teplota je barevně odlišená, vítr má šipku ve směru proudění. Volby rozsahu se
  generují podle `hours_back` (celé hodiny od maxima dolů ke 2 h, pak 1,5 / 1 /
  0,5 h); výchozí jsou 3 h, a je-li `hours_back` menší než 3, největší dostupná
  hodnota. Rozsah filtruje jen z dat, která downloader drží, takže okno lze
  zúžit, ne rozšířit nad `hours_back`.

## Schéma

```
                        ČHMÚ open data
        opendata.chmi.cz/.../maxz/png/      (radarové PNG)
        opendata.chmi.cz/.../fct_maxz/png/  (předpověď .tar)
        opendata.chmi.cz/.../climate/now/   (pozorování stanic, JSON)
                              │
                              │  HTTP GET (requests)
                              ▼
   ┌─────────────────────────────────────────────┐
   │  downloader  (chmi_radar.main → update_once)  │
   │   • get_radar_history()  stáhne radar         │
   │   • get_forecast()       stáhne + rozbalí tar │
   │   • update_stations()    stáhne pozorování    │
   │   • cleanup()            smaže stará data     │
   │   smyčka každých INTERVAL s                   │
   └───────────────┬───────────────────────────────┘
                   │ zapisuje PNG + stations.json
                   ▼
       radar/   forecast/<běh>/   stations/   ◄── sdílené adresáře / volumes
                   │
                   │ čte PNG + JSON
                   ▼
   ┌─────────────────────────────────────────────┐
   │  viewer  (chmi_radar.serve, http.server)      │
   │   GET /              → web/viewer.html        │
   │   GET /frames        → JSON seznam snímků     │
   │   GET /stations.json → pozorování stanic      │
   │   GET /radar/*       → radarové PNG           │
   │   GET /forecast/*    → PNG předpovědi          │
   │   GET /static/*      → Leaflet                │
   └───────────────┬───────────────────────────────┘
                   │ HTTP
                   ▼
              prohlížeč  (Leaflet animace nad OSM)
```

Konfigurace je centrální v `chmi_radar.config` s precedencí:
**proměnná prostředí > `conf/app.conf` > výchozí hodnota v kódu**.

## Spuštění lokálně

Vyžaduje Python 3.13+ (jediná závislost je `requests`).

```bash
# 1) virtuální prostředí a závislosti
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2) aby byl balíček chmi_radar na cestě
export PYTHONPATH=src

# 3) v jednom terminálu downloader (stahuje data ve smyčce)
python -m chmi_radar.main

# 4) ve druhém terminálu viewer (HTTP server)
python -m chmi_radar.serve
```

Viewer poté běží na adrese a portu z `conf/app.conf`
(výchozí `http://127.0.0.1:8987/`).

Nastavení lze měnit v `conf/app.conf` (interval, počet hodin zpět, zdrojové URL,
host/port, cílové adresáře) nebo přepsat proměnnou prostředí, např.:

```bash
PORT=9000 HOURS_BACK=2 python -m chmi_radar.serve
```

## Spuštění přes Podman / Docker Compose

Funguje s `docker compose` i `podman-compose`. Compose spouští dvě služby –
`downloader` a `viewer` – které sdílejí data přes pojmenované volumes
(`radar`, `forecast`, `stations`).

```bash
podman-compose up --build
# nebo
docker compose up --build
```

Viewer poté běží na adrese a portu z `conf/app.conf`
(výchozí `http://127.0.0.1:8987/`).

- **Port (i host) se nastavuje jen v `conf/app.conf`.** Služba `viewer` používá
  host networking (`network_mode: host`), takže kontejner naslouchá přímo na
  hostiteli na portu z konfigurace. Změníš-li port v `conf/app.conf` a službu
  restartuješ, je viewer hned dostupný na tom portu – žádná další úprava není
  potřeba.
- Chceš-li viewer zpřístupnit i z jiných počítačů, nastav v `conf/app.conf`
  `host = 0.0.0.0`.
- `conf/app.conf` je připojen jako volume – stačí ho upravit a služby
  restartovat, není potřeba rebuild.
- **SELinux (Fedora apod.):** adresář `conf/` je do kontejneru připojen s
  labelem `:z` (`./conf:/app/conf:ro,z`), jinak by SELinux čtení konfigurace
  zablokoval a aplikace by spadla na výchozí hodnoty.

### Health check

Obě služby mají v compose definovaný `healthcheck` (plní roli liveness i
readiness – Compose má jen tento jeden mechanismus):

- **viewer** – je `healthy`, když HTTP server odpovídá na portu z `conf/app.conf`.
- **downloader** – je `healthy`, když je v `radar/` čerstvý snímek (mladší než
  2× `interval`), tedy stahovací smyčka skutečně běží. Po startu má 120 s
  odklad (`start_period`), než dorazí první data – do té doby je ve stavu
  `starting`.

Stav zjistíš přes:

```bash
podman ps                  # sloupec STATUS ukáže "(healthy)"
# nebo konkrétní služba:
podman inspect chmi_maponly_viewer_1 --format '{{.State.Health.Status}}'
```

---

Projekt byl vytvořen s využitím [Claude Code](https://claude.com/claude-code).
