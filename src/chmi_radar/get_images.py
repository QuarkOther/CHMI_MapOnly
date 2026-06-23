import glob
import os
import shutil
import requests
import tarfile
from datetime import datetime, timedelta, timezone

from chmi_radar.config import (
    FORECAST_URL,
    HOURS_BACK,
    OUT_FORECAST,
    OUT_RADAR_DATA,
    RADAR_URL,
)


def mkdir():
    os.makedirs(OUT_RADAR_DATA, exist_ok=True)
    os.makedirs(OUT_FORECAST, exist_ok=True)


def round_to_5min(dt):
    """Zaokrouhlení dolů na poslední radarový termín."""
    minute = (dt.minute // 5) * 5
    return dt.replace(
        minute=minute,
        second=0,
        microsecond=0
    )


def download(url, filename):
    path = os.path.join(OUT_RADAR_DATA, filename)

    if os.path.exists(path):
        return path

    print("stahuji:", filename)

    r = requests.get(url, timeout=30)

    if r.status_code != 200:
        print("nenalezeno:", url)
        return None

    with open(path, "wb") as f:
        f.write(r.content)

    return path


def get_radar_history(hours=HOURS_BACK):

    now = datetime.now(timezone.utc)
    end = round_to_5min(now)

    files = []

    t = end - timedelta(hours=hours)

    while t <= end:

        name = (
            f"pacz2gmaps3.z_max3d."
            f"{t:%Y%m%d.%H%M}.0.png"
        )

        url = RADAR_URL + name

        result = download(url, name)

        if result:
            files.append(result)

        t += timedelta(minutes=5)

    return files, end


def get_forecast(base_time):

    name = (
        f"pacz2gmaps3.fct_z_max."
        f"{base_time:%Y%m%d.%H%M}.ft60s10.tar"
    )

    url = FORECAST_URL + name

    tarfile_path = download(url, name)

    if not tarfile_path:
        return []

    print("rozbaluji forecast")

    with tarfile.open(tarfile_path) as tar:
        tar.extractall(OUT_FORECAST)
        return tar.getnames()


def _parse_dt(date, hhmm):
    """'20260622','1315' -> UTC datetime, jinak None."""
    try:
        return datetime.strptime(
            date + hhmm, "%Y%m%d%H%M"
        ).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def cleanup(hours=HOURS_BACK):
    """Smaže radarové snímky, forecast tary a běhy starší než `hours`."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # radarové PNG i stažené forecast .tar (oboje v OUT_RADAR_DATA);
    # název: pacz2gmaps3.<typ>.YYYYMMDD.HHMM.* -> parts[2], parts[3]
    for path in glob.glob(os.path.join(OUT_RADAR_DATA, "*")):
        parts = os.path.basename(path).split(".")
        if len(parts) < 4:
            continue
        t = _parse_dt(parts[2], parts[3])
        if t and t < cutoff:
            os.remove(path)
            print("smazáno:", os.path.basename(path))

    # forecast: ponecháme jen nejnovější běh – na ten navazuje radar ve vieweru
    runs = sorted(
        d for d in glob.glob(os.path.join(OUT_FORECAST, "*"))
        if os.path.isdir(d)
    )
    for d in runs[:-1]:
        shutil.rmtree(d)
        print("smazán forecast běh:", os.path.basename(d))

