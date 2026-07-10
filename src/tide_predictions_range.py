import argparse

import requests

STATION = "9414290"
TIDES_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"


def get_tide_predictions(start_date, end_date):
    params = {
        "begin_date": start_date,
        "end_date": end_date,
        "station": STATION,
        "product": "predictions",
        "datum": "STND",
        "time_zone": "lst",
        "units": "english",
        "format": "json",
    }
    resp = requests.get(TIDES_URL, params=params)
    resp.raise_for_status()
    return resp.json()["predictions"]


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch NOAA tide predictions for a date range.")
    parser.add_argument("startdate", help="Start date in YYYYMMDD format")
    parser.add_argument("enddate", help="End date in YYYYMMDD format")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    predictions = get_tide_predictions(args.startdate, args.enddate)
    print(predictions)
