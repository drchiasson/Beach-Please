import re
from dataclasses import dataclass

import requests

POINTS_URL = "https://api.weather.gov/points/37.8017,-122.48"
HEADERS = {"User-Agent": "BeachPlease-WeatherScript (shlukiman@gmail.com)"}


@dataclass
class Forecast:
    temperature: float
    windSpeed: float
    windDirection: str
    probabilityOfPrecipitation: int


def parse_wind_speed(wind_speed_str):
    speeds = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", wind_speed_str)]
    return sum(speeds) / len(speeds)


def get_forecasts(points_url):
    points_resp = requests.get(points_url, headers=HEADERS)
    points_resp.raise_for_status()
    forecast_url = points_resp.json()["properties"]["forecast"]

    forecast_resp = requests.get(forecast_url, headers=HEADERS)
    forecast_resp.raise_for_status()
    periods = forecast_resp.json()["properties"]["periods"]

    return [
        Forecast(
            temperature=float(period["temperature"]),
            windSpeed=parse_wind_speed(period["windSpeed"]),
            windDirection=period["windDirection"],
            probabilityOfPrecipitation=period["probabilityOfPrecipitation"]["value"],
        )
        for period in periods
    ]


if __name__ == "__main__":
    forecasts = get_forecasts(POINTS_URL)
    print(forecasts)
