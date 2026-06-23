import glob
import json
import os
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler

from chmi_radar import config


PROJECT_HOME = config.PROJECT_HOME

OUT_RADAR_DATA = config.OUT_RADAR_DATA
OUT_FORECAST = config.OUT_FORECAST

WEB_DIR = os.path.join(PROJECT_HOME, "web")
VIEWER = os.path.join(WEB_DIR, "viewer.html")
STATIC_DIR = os.path.join(WEB_DIR, "static")

HOST = config.HOST
PORT = config.PORT


def time_key(name):
    """Vrátí YYYYMMDDHHMM z názvu souboru pro řazení."""
    parts = os.path.basename(name).split(".")
    return parts[2] + parts[3]


def label(name):
    parts = os.path.basename(name).split(".")
    date, hhmm = parts[2], parts[3]
    return f"{date[6:8]}.{date[4:6]}. {hhmm[:2]}:{hhmm[2:]}"


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
            body = json.dumps(collect_frames()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        return super().do_GET()

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
