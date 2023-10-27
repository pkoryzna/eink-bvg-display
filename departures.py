import datetime
import functools
import itertools
import json
import logging
import pprint
import re
import zoneinfo

import requests

logging.basicConfig()
logging.root.setLevel(logging.ERROR)

URL_TEMPLATE = "https://v6.bvg.transport.rest/stops/{}/departures/"


def _check_config(config: any) -> dict[str, list[str | dict[str, str]]]:
    has_keys = isinstance(config, dict) and all(
        key in config
        for key in (
            "stops",
            "remove_phrases",
            "my_zone",
            "lines_directions",
        )
    )

    lines_directions_valid = all(
        "line_name" in item and "direction_regex" in item
        for item in config["lines_directions"]
    )

    config_valid = has_keys and lines_directions_valid
    if not config_valid:
        raise ValueError(f"config: {config} was invalid")
    config["lines_directions"] = _compile(config["lines_directions"])
    return config


def _load_config():
    with open("config.json") as config_file:
        config = json.load(config_file)
    return _check_config(config)


def _compile(lines_directions: list[dict[str, str]]) -> list[tuple[str, re.Pattern]]:
    compiled = [
        (item["line_name"], re.compile(item["direction_regex"]))
        for item in lines_directions
    ]
    return compiled


_LOGGER = logging.getLogger(__name__)

session = requests.Session()


@functools.wraps(requests.request)
def _run_request(*args, **kwargs):
    response = session.request(*args, timeout=5, **kwargs)
    response.raise_for_status()
    logging.debug(pprint.pformat(response.headers, compact=True))
    logging.debug
    return response.json()


def departures_url(stop_id: str) -> str:
    return URL_TEMPLATE.format(stop_id)


def get_departures(stop_id: str) -> any:
    url = departures_url(stop_id)
    result_json = _run_request(
        method="GET",
        url=url,
        params={
            "duration": 50,
        },
    )
    departures = result_json.get("departures")
    if departures is not None:
        return departures
    raise KeyError(f"missing departures in response: {result_json}")


def now(my_zone: zoneinfo.ZoneInfo):
    return datetime.datetime.now(tz=my_zone)


def timedelta_pformat(td: datetime.timedelta) -> str:
    seconds = int(td.total_seconds())
    minutes = seconds // 60
    hours = minutes // 60
    if seconds > 0:
        formatted = "in "

    if hours:
        formatted += f"{hours}h"
    if minutes:
        formatted += f"{minutes}m"

    if not hours and not minutes and not seconds:
        formatted = "now"

    if seconds < 0:
        formatted += f"{seconds} sec ago"

    return formatted


def zip_max(*lists):
    """
    Return a list of maxiumum elements of lists compared index-wise

    zipped = [0, 9, 0] zip [1, 2, 3] -> [(0,1), (9,2), (0,3)]
    for each in zipped: max(each) = [ 1, 9, 3 ]
    """
    if len({len(input_list) for input_list in lists}) > 1:
        raise ValueError("input lists must have equal sizes")
    return [max(zipped_tuple) for zipped_tuple in zip(*lists)]


def clean_string(input: str, remove_phrases: list[str]) -> str:
    def remove_phrase(input: str, phrase: str):
        return input.replace(phrase, "")

    return functools.reduce(remove_phrase, remove_phrases, input)


def clean_row(row: tuple[str, ...], remove_phrases: list[str]):
    return tuple(clean_string(s, remove_phrases) for s in row)


def _when(departure):
    when = departure["when"]
    # print(when)
    try:
        return datetime.datetime.fromisoformat(when)
    except TypeError as e:
        raise TypeError(f"unexpected type of 'when': {type(when)}") from e


def should_display(
    departure: dict[str, any], lines_directions: list[dict[str, str]]
) -> bool:
    for line, dir_regex in lines_directions:
        line_name = departure["line"]["name"]
        match = dir_regex.match(departure["direction"])
        _LOGGER.debug(
            "line_name=%s, line=%s, dir_regex=%s, match=%s",
            line_name,
            line,
            dir_regex.pattern,
            match,
        )
        if line_name == line and match is not None:
            return True
    return False


def main():
    departures = []
    config = _load_config()
    zone = zoneinfo.ZoneInfo(config["my_zone"])
    for stop_id in config["stops"]:
        departures += get_departures(stop_id)
    filtered = [d for d in departures if should_display(d, config["lines_directions"])]

    for key, departures in itertools.groupby(
        filtered, key=lambda d: (d["stop"]["name"], d["line"]["name"], d["direction"])
    ):
        stop, name, dir = key
        print(f"{stop} -> {name} -> {dir}")
        for departure in departures:
            when = _when(departure)
            now_rounded = now(zone).replace(second=0, microsecond=0)
            time_left = when - now_rounded
            nice_time = timedelta_pformat(time_left)
            print(nice_time, end=" ")
        print("\n")


if __name__ == "__main__":
    main()
