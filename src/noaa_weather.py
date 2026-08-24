import logging
import re
from dataclasses import dataclass

from constants import REQUEST_TIMEOUT, session

logger = logging.getLogger(__name__)

POINTS_URL = "https://api.weather.gov/points/37.8017,-122.48"
HEADERS = {"User-Agent": "BeachPlease-Weather"}

def parse_wind_speed(wind_speed_str):
    speeds = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", wind_speed_str)]
    if not speeds:
        return 0.0
    return sum(speeds) / len(speeds)


def get_forecasts(points_url=POINTS_URL) -> dict:
    points_resp = session.get(points_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    points_resp.raise_for_status()
    forecast_url = points_resp.json()["properties"]["forecast"]

    forecast_resp = session.get(forecast_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    forecast_resp.raise_for_status()
    periods = forecast_resp.json()["properties"]["periods"]

    forecast =  {"Forcast":[
        {
            "startTime": str(period["startTime"]),
            "endTime": str(period["endTime"]),
            "temperature": str(float(period["temperature"])),
            "windSpeed": str(parse_wind_speed(period["windSpeed"])),
            "windDirection": str(period["windDirection"]),
            "probabilityOfPrecipitation": str(period["probabilityOfPrecipitation"]["value"]),
        }
        for period in periods
    ]}

    logger.info(forecast)
    return forecast


if __name__ == "__main__":
    forecasts = get_forecasts(POINTS_URL)
    print(forecasts)
