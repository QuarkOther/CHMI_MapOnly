"""Stažení pozemních pozorování ČHMÚ (climate/now) a sestavení stations.json.

Na rozdíl od radaru nejde o georeferencovaný obrázek, ale o bodová data po
stanicích. Downloader z nich poskládá jeden agregát `stations/stations.json`,
který viewer vykreslí jako značky s hodnotami synchronizované s animací.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

import requests

from chmi_radar.config import HOURS_BACK, OUT_STATIONS, STATIONS_URL

# Veličiny, které zobrazujeme: teplota, vlhkost, tlak, rychlost a směr větru.
ELEMENTS = ["T", "H", "P", "F", "D"]

# Sloupce v datovém souboru: STATION,ELEMENT,DT,VAL,FLAG,QUALITY
_EL, _DT, _VAL = 1, 2, 3
# Sloupce v meta1: WSI,GH_ID,FULL_NAME,GEOGR1(lon),GEOGR2(lat),ELEVATION,BEGIN_DATE
_WSI, _NAME, _LON, _LAT = 0, 2, 3, 4


def _get_json(url):
    """Stáhne a naparsuje JSON; vrátí dict nebo None (404, timeout, chyba)."""
    try:
        r = requests.get(url, timeout=15)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except ValueError:
        return None


def _values(doc):
    """Vytáhne pole řádků z dvojitě zanořené struktury ČHMÚ (data.data.values)."""
    try:
        return doc["data"]["data"]["values"]
    except (KeyError, TypeError):
        return []


def _date_strs():
    """UTC data, která pokrývají okno HOURS_BACK – dnešek a případně i včerejšek."""
    now = datetime.now(timezone.utc)
    days = {now, now - timedelta(hours=HOURS_BACK)}
    return sorted({d.strftime("%Y%m%d") for d in days})


def _parse_ts(dt_str):
    """'2026-06-23T12:50:00Z' -> unix sekundy (UTC), jinak None."""
    try:
        return int(
            datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
            .replace(tzinfo=timezone.utc)
            .timestamp()
        )
    except (ValueError, TypeError):
        return None


def fetch_meta():
    """Stanice bloku 11 (ČR) -> {wsi: {name, lat, lon}}. Zkusí dnešek i včerejšek."""
    for date in reversed(_date_strs()):
        doc = _get_json(f"{STATIONS_URL}metadata/meta1-{date}.json")
        rows = _values(doc)
        if not rows:
            continue
        meta = {}
        for row in rows:
            wsi = row[_WSI]
            if not isinstance(wsi, str) or not wsi.split("-")[-1].startswith("11"):
                continue  # jen české stanice (WMO blok 11)
            meta[wsi] = {
                "name": row[_NAME],
                "lat": row[_LAT],
                "lon": row[_LON],
            }
        if meta:
            return meta
    return {}


def fetch_series(wsi, cutoff_ts):
    """Časové řady veličin jedné stanice za okno: {element: [[ts, val], ...]}."""
    series = {el: [] for el in ELEMENTS}
    for date in _date_strs():
        doc = _get_json(f"{STATIONS_URL}data/10m-{wsi}-{date}.json")
        for row in _values(doc):
            el = row[_EL]
            if el not in series:
                continue
            ts = _parse_ts(row[_DT])
            val = row[_VAL]
            if ts is None or ts < cutoff_ts or not isinstance(val, (int, float)):
                continue
            series[el].append([ts, val])
    for el in series:
        series[el].sort(key=lambda p: p[0])
    return {el: pts for el, pts in series.items() if pts}


def build_payload():
    """Sestaví agregát: metadata stanic + jejich časové řady za HOURS_BACK."""
    cutoff_ts = int(
        (datetime.now(timezone.utc) - timedelta(hours=HOURS_BACK)).timestamp()
    )
    meta = fetch_meta()

    stations = []
    for wsi, info in meta.items():
        series = fetch_series(wsi, cutoff_ts)
        if not series:
            continue  # stanice bez 10min dat (jen klimatologická) – přeskoč
        stations.append({
            "id": wsi.split("-")[-1],
            "name": info["name"],
            "lat": info["lat"],
            "lon": info["lon"],
            "series": series,
        })

    return {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "elements": ELEMENTS,
        "stations": stations,
    }


def update_stations():
    """Stáhne pozorování a atomicky přepíše stations/stations.json."""
    os.makedirs(OUT_STATIONS, exist_ok=True)
    payload = build_payload()

    fd, tmp = tempfile.mkstemp(dir=OUT_STATIONS, suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    os.chmod(tmp, 0o644)  # mkstemp dělá 600; viewer musí umět číst i přes volume
    os.replace(tmp, os.path.join(OUT_STATIONS, "stations.json"))

    return len(payload["stations"])
