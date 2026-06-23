import glob
import json
import os
from datetime import datetime, timezone
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from zoneinfo import ZoneInfo

from chmi_radar import config


PRAGUE_TZ = ZoneInfo("Europe/Prague")


PROJECT_HOME = config.PROJECT_HOME

OUT_RADAR_DATA = config.OUT_RADAR_DATA
OUT_FORECAST = config.OUT_FORECAST
OUT_STATIONS = config.OUT_STATIONS

WEB_DIR = os.path.join(PROJECT_HOME, "web")
VIEWER = os.path.join(WEB_DIR, "viewer.html")
STATIC_DIR = os.path.join(WEB_DIR, "static")

HOST = config.HOST
PORT = config.PORT
HOURS_BACK = config.HOURS_BACK


def time_key(name):
    """Vrátí YYYYMMDDHHMM z názvu souboru pro řazení."""
    parts = os.path.basename(name).split(".")
    return parts[2] + parts[3]


def frame_utc(name):
    """Vrátí UTC datetime snímku z názvu souboru."""
    parts = os.path.basename(name).split(".")
    return datetime.strptime(parts[2] + parts[3], "%Y%m%d%H%M").replace(
        tzinfo=timezone.utc
    )


def label(name):
    # názvy souborů ČHMÚ jsou v UTC; pro zobrazení převedeme na pražský čas
    local = frame_utc(name).astimezone(PRAGUE_TZ)
    return f"{local:%d.%m. %H:%M}"


def collect_frames():
    """Radar následovaný nejnovější předpovědí; forecast navazuje za posledním radarem."""
    frames = []

    radar = sorted(
        glob.glob(os.path.join(OUT_RADAR_DATA, "*.png")),
        key=time_key,
    )
    for path in radar:
        frames.append({
            "url": "/radar/" + os.path.basename(path),
            "label": label(path),
            "ts": int(frame_utc(path).timestamp()),
            "forecast": False,
        })

    # čas posledního radaru (YYYYMMDDHHMM); forecast bereme jen za ním
    last_radar = time_key(radar[-1]) if radar else ""

    runs = sorted(
        d for d in glob.glob(os.path.join(OUT_FORECAST, "*"))
        if os.path.isdir(d)
    )
    if runs:
        latest = runs[-1]
        run_name = os.path.basename(latest)
        forecast = sorted(
            glob.glob(os.path.join(latest, "*.png")),
            key=time_key,
        )
        for path in forecast:
            if time_key(path) <= last_radar:
                continue  # přeskoč překryv – forecast má navazovat až za radarem
            frames.append({
                "url": f"/forecast/{run_name}/" + os.path.basename(path),
                "label": label(path),
                "ts": int(frame_utc(path).timestamp()),
                "forecast": True,
            })

    return frames


class Handler(SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            return self.send_file(VIEWER, "text/html")

        if self.path.startswith("/static/"):
            rel = self.path[len("/static/"):].split("?", 1)[0]
            path = os.path.normpath(os.path.join(STATIC_DIR, rel))
            if not path.startswith(STATIC_DIR) or not os.path.isfile(path):
                self.send_error(404)
                return
            ctype = self.guess_type(path)
            return self.send_file(path, ctype)

        if self.path == "/frames":
            return self.send_json(collect_frames())

        if self.path == "/stations.json":
            path = os.path.join(OUT_STATIONS, "stations.json")
            if not os.path.isfile(path):
                return self.send_json({"elements": [], "stations": []})
            return self.send_file(path, "application/json")

        if self.path == "/config":
            return self.send_json({"hours_back": HOURS_BACK})

        return super().do_GET()

    def send_json(self, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, content_type):
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    handler = partial(Handler, directory=PROJECT_HOME)
    server = HTTPServer((HOST, PORT), handler)
    print(f"Otevři http://{HOST}:{PORT}/  (Ctrl+C ukončí)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKonec.")


if __name__ == "__main__":
    main()
