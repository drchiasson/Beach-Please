import re
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import requests

BASE_URL = "https://cdn.star.nesdis.noaa.gov/GOES18/ABI/SECTOR/psw/GEOCOLOR/"
FILENAME_PATTERN = re.compile(r"(\d{11})_GOES18-ABI-psw-GEOCOLOR-2400x2400\.jpg")

HOURS_BACK = 2
INTERVAL_MINUTES = 10
MATCH_TOLERANCE_MINUTES = 4

IMAGE_DIR = Path(__file__).resolve().parent.parent / "satellite_image_bin"
CROP = (slice(1120, 1225), slice(575, 680))


def parse_timestamp(ts):
    year = int(ts[0:4])
    day_of_year = int(ts[4:7])
    hour = int(ts[7:9])
    minute = int(ts[9:11])
    return datetime(year, 1, 1) + timedelta(days=day_of_year - 1, hours=hour, minutes=minute)


def get_available_images():
    resp = requests.get(BASE_URL)
    resp.raise_for_status()

    images = {}
    for ts in FILENAME_PATTERN.findall(resp.text):
        images[parse_timestamp(ts)] = f"{ts}_GOES18-ABI-psw-GEOCOLOR-2400x2400.jpg"
    return images


def select_image_urls(images):
    latest = max(images)
    urls = []
    for minutes_back in range(0, HOURS_BACK * 60 + 1, INTERVAL_MINUTES):
        target = latest - timedelta(minutes=minutes_back)
        closest = min(images, key=lambda t: abs((t - target).total_seconds()))
        if abs((closest - target).total_seconds()) <= MATCH_TOLERANCE_MINUTES * 60:
            urls.append(BASE_URL + images[closest])

    return sorted(set(urls))


def download_and_crop_images(urls):
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    for url in urls:
        image_path = IMAGE_DIR / url.rsplit("/", 1)[-1]

        resp = requests.get(url)
        resp.raise_for_status()
        image_path.write_bytes(resp.content)

        image = cv2.imread(str(image_path))
        cropped = image[CROP]
        cv2.imwrite(str(image_path), cropped)


if __name__ == "__main__":
    images = get_available_images()
    urls = select_image_urls(images)
    print(urls)
    download_and_crop_images(urls)
