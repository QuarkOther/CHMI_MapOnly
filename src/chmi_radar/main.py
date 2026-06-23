import time

from chmi_radar.config import INTERVAL
from chmi_radar.update import update_once


def main():
    while True:
        update_once()
        print(f"\nDalší aktualizace za {INTERVAL} s ...\n")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
