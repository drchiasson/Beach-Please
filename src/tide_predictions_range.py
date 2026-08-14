import argparse
import logging

import requests

from constants import REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

STATION = "9414290"
TIDES_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"


def get_tide_predictions(start_date, end_date):
    params = {
        "begin_date": start_date,
        "end_date": end_date,
        "station": STATION,
        "product": "predictions",
        "datum": "MLLW",
        "time_zone": "lst_ldt",
        "units": "english",
        "format": "json",
    }
    resp = requests.get(TIDES_URL, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return get_high_low_tides(resp.json()["predictions"])


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch NOAA tide predictions for a date range.")
    parser.add_argument("startdate", help="Start date in YYYYMMDD format")
    parser.add_argument("enddate", help="End date in YYYYMMDD format")
    return parser.parse_args()

def get_high_low_tides(predictions):
    """Find local high/low points in a tide prediction series.

    predictions: list of {"t": "<datetime>", "v": "<height>"} dicts,
    as returned by get_tide_predictions.
    """

    logger.debug("Tidal formatted data")

    points = [(p["t"], float(p["v"])) for p in predictions]

    highs = []
    lows = []
    for i in range(1, len(points) - 1):
        t, v = points[i]
        _, v_prev = points[i - 1]
        _, v_next = points[i + 1]

        if v > v_prev and v > v_next:
            highs.append({"time": t, "height": v})
        elif v < v_prev and v < v_next:
            lows.append({"time": t, "height": v})

    tides = {"high_tides": highs, "low_tides": lows}
    logger.debug(tides)
    return tides


if __name__ == "__main__":
    args = parse_args()
    predictions = get_tide_predictions(args.startdate, args.enddate)
    lowHighTides = get_high_low_tides(predictions)
    print(lowHighTides)
