from chmi_radar.get_images import (
    cleanup,
    get_forecast,
    get_radar_history,
    mkdir,
)
from chmi_radar.stations import update_stations


def update_once():
    """Jeden cyklus: stáhne nejnovější radar i forecast a uklidí stará data."""

    mkdir()

    print("=== ČHMÚ radar poslední 3 hodiny ===")

    history, last_time = get_radar_history()

    print()
    print("Staženo:")
    for f in history:
        print(" ", f)

    print()
    print("=== ČHMÚ radarová předpověď ===")

    forecast = get_forecast(last_time)

    print()
    print("Forecast soubory:")
    for f in forecast:
        print(" ", f)

    print()
    print("=== ČHMÚ pozemní stanice (teplota, vítr, vlhkost, tlak) ===")
    count = update_stations()
    print(f"Stanic s daty: {count}")

    print()
    print("=== úklid starých dat ===")
    cleanup()

    print()
    print("Hotovo.")


if __name__ == "__main__":
    update_once()
