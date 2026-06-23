"""Centrální konfigurace. Precedence: env proměnná > conf/app.conf > default."""

import configparser
import os


PROJECT_HOME = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

CONF_PATH = os.environ.get(
    "APP_CONF", os.path.join(PROJECT_HOME, "conf", "app.conf")
)

_parser = configparser.ConfigParser()
_parser.read(CONF_PATH)


def _get(section, key, env, default, cast=str):
    if env in os.environ:
        return cast(os.environ[env])
    if _parser.has_option(section, key):
        return cast(_parser.get(section, key))
    return cast(default)


def _resolve(path):
    """Relativní cestu z konfigurace bere od kořene projektu."""
    return path if os.path.isabs(path) else os.path.join(PROJECT_HOME, path)


# server
HOST = _get("server", "host", "HOST", "127.0.0.1")
PORT = _get("server", "port", "PORT", 8000, int)

# downloader
INTERVAL = _get("downloader", "interval", "INTERVAL", 300, int)
HOURS_BACK = _get("downloader", "hours_back", "HOURS_BACK", 3, int)

# zdrojová URL
RADAR_URL = _get(
    "sources", "radar_url", "RADAR_URL",
    "https://opendata.chmi.cz/meteorology/weather/radar/composite/maxz/png/",
)
FORECAST_URL = _get(
    "sources", "forecast_url", "FORECAST_URL",
    "https://opendata.chmi.cz/meteorology/weather/radar/composite/fct_maxz/png/",
)

# adresáře dat
OUT_RADAR_DATA = _resolve(_get("paths", "radar_dir", "RADAR_DIR", "radar"))
OUT_FORECAST = _resolve(_get("paths", "forecast_dir", "FORECAST_DIR", "forecast"))
