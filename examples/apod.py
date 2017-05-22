#!/usr/bin/env python3
# See the result of this script in the channel: https://telegram.me/astropod
import argparse
import json
import os
from subprocess import call

import requests

from secret import key


def main():
    parser = argparse.ArgumentParser(description="Send the daily Astronomy Picture of the Day.")
    parser.add_argument("--config", help="configuration file for telegram-send", type=str)
    args = parser.parse_args()
    conf_command = ["--config", args.config] if args.config else []

    api = "https://api.nasa.gov/planetary/apod"
    payload = {"api_key": key}  # date: YYYY-MM-DD
    r = requests.get(api, params=payload)

    data = json.loads(r.text)
    url = data["url"]
    explanation = data["explanation"]
    title = data["title"]

    year, month, day = data["date"].split('-')
    link = "http://apod.nasa.gov/apod/ap" + year[2:] + month + day + ".html"

    if data["media_type"] == "image":
        if "hdurl" in data:
            hdurl = data["hdurl"]
            hd_headers = requests.head(hdurl).headers
            if int(hd_headers["Content-Length"]) < 2E6:  # only download HD images under 2 MB
                url = hdurl
        image = requests.get(url).content

        filename = "astro"
        with open(filename, "wb") as f:
            f.write(image)
        call(["telegram-send", "--image", filename, "--caption", title + " - " + link] + conf_command)
        os.remove(filename)
    elif data["media_type"] == "video":
        message = url
        call(["telegram-send", message] + conf_command)


if __name__ == "__main__":
    main()
