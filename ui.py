import collections
import sys
import json
import time
import machine

from soldered_inkplate6 import Inkplate

import transport_api
import timezone_api
import dateutil

start_time_ticks = time.ticks_ms()

import netutil
from config import load_config
from dateutil import timedelta_pformat
from stringutil import clean_string

from simple_bitmap_font import MonoFont
from fonts.condensed import font_dict as condensed_font
from fonts.regular import font_dict as regular_font

Any = object

CONDENSED = MonoFont(font_dict=condensed_font, preload_chars=False)
REGULAR = MonoFont(font_dict=regular_font, preload_chars=False)

UIState = collections.namedtuple("UIState", ("departures", "created_at"))
Message = collections.namedtuple("Message", ("text", "created_at"))
UIDeparture = collections.namedtuple(
    "UIDeparture", ("line_name", "direction", "time_left", "stop")
)
XY = collections.namedtuple("XY", ("x", "y"))

display = Inkplate(Inkplate.INKPLATE_1BIT)


APPROX_REFRESH_DURATION_AFTER_DEEPSLEEP_RESET = 16
APPROX_COLD_BOOT_REFRESH_DURATION = 22


def _log(*args, **kwargs):
    print(*args, end=" ")
    if kwargs:
        print(kwargs)
    else:
        print()


def _when(departure) -> int:
    # bobby you got to learn a lot about python my boy
    hwen = departure["when"]
    if hwen is None:
        return -1

    try:
        return dateutil.parse_iso(hwen)
    except TypeError as e:
        raise TypeError(f"failed to parse 'when': {type(e)}: {e}")


def is_relevant(
    departure: dict[str, Any], lines_directions: list[dict], now: int
) -> bool:
    api_when = _when(departure)
    if not api_when:
        # probably canceled
        return False
    time_left = api_when - now

    if time_left < 0:
        return False

    for match_config in lines_directions:
        match_line, dir_regex, except_regex = (
            match_config["line_name"],
            match_config["direction_regex"],
            match_config.get("except_regex"),
        )

        departure_line = departure["line"]["name"]
        if departure_line != match_line:
            continue

        direction_departure = departure["direction"]
        dir_match = dir_regex.match(direction_departure)
        if dir_match is None:
            continue

        if except_regex and except_regex.match(direction_departure):
            continue

        return True

    return False


def get_configured_departures(
    stops: list[str], lines_directions: list, remove_phrases: list[str]
) -> dict[str, list[UIDeparture]]:
    departures = []
    now = dateutil.now_epoch()

    for stop_id in stops:
        _log("getting departures from api for", stop_id)
        all_departures_from_stop = transport_api.get_departures(stop_id)
        _log("got", len(all_departures_from_stop), "departures from", stop_id)
        departures_list = [
            d for d in all_departures_from_stop if is_relevant(d, lines_directions, now)
        ]
        for api_departure in departures_list:
            display_direction = clean_string(api_departure["direction"], remove_phrases)

            departures.append(
                UIDeparture(
                    api_departure["line"]["name"],
                    display_direction,
                    _when(api_departure) - now,
                    clean_string(api_departure["stop"]["name"], remove_phrases),
                )
            )
    filtered = dict()
    for d in departures:
        stop_departures = filtered.get(d.stop, list())
        stop_departures.append(d)
        filtered[d.stop] = stop_departures

    return filtered


MARGIN = 5
DESTINATION_X = 130 + MARGIN
TIME_LEFT_X = 0 + MARGIN

CONDENSED_Y_OFFSET = -5


def display_departures(departure_data: dict[str, list[UIDeparture]]):
    y = MARGIN
    deps_per_stop = 6 // len(departure_data)
    for stop, departures in departure_data.items():
        # _log(stop)
        CONDENSED.draw_text(display.ipm, stop, 0, y, align=MonoFont.LEFT)
        y += CONDENSED._line_height

        departures = departures[:deps_per_stop]

        for line, dir, time_left, _ in departures:
            # _log(line, dir, time_left)
            _, _, line_end_x, _ = REGULAR.draw_text(display.ipm, line, x=0, y=y)

            CONDENSED.draw_text(
                display.ipm, dir, x=DESTINATION_X, y=y + CONDENSED_Y_OFFSET
            )
            when_pretty = timedelta_pformat(time_left)
            when_w, when_h = REGULAR.get_text_size(when_pretty)
            display.ipm.fill_rect(800 - when_w, y, when_w, when_h, 0)
            REGULAR.draw_text(
                display.ipm, when_pretty, x=800, y=y, align=MonoFont.RIGHT
            )
            y += 100

        y += 12
        display.drawRect(y=y, x=0, w=800, h=2, c=1)
        y += 12


CLOCK_TEXT_SIZE = 4


def show_status_message(text: str):
    print(text)


def display_clock(utc_offset_seconds: int):
    (_, _, _, hour, minute, _, _, _) = time.gmtime(
        dateutil.now_epoch() + utc_offset_seconds
    )

    CONDENSED.draw_text(
        display.ipm,
        f"{hour:02d}:{minute:02d}",
        x=800 - 3,
        y=10,
        transparent=False,
        align=MonoFont.RIGHT,
    )


def should_set_time(cache: dict) -> bool:
    seconds_since_update = abs(
        dateutil.now_epoch() - cache.get("last_rtc_ntp_update", 0)
    )
    return seconds_since_update > 1 * 60 * 60


def loop(config, cache):
    global start_time_ticks
    if not netutil.wlan.isconnected():
        connect_wifi(config, cache)

    if should_set_time(cache):
        show_status_message("Setting time from NTP...")
        netutil.setup_time()
        cache["last_rtc_ntp_update"] = dateutil.now_epoch()

    departures = get_configured_departures(
        config["stops"],
        config["lines_directions"],
        config["remove_phrases"],
    )
    tz_info = timezone_api.get_tz_info_for_my_ip(config=config, cache=cache)

    seconds_until_next_min = dateutil.next_full_minute() - dateutil.now_epoch()
    if seconds_until_next_min < 10:
        _log("light sleep for", seconds_until_next_min, "seconds")
        machine.lightsleep(seconds_until_next_min * 1000)

    display.begin()

    display_departures(departure_data=departures)
    _log("detected timezone:", tz_info["timezone"])
    utc_offset_seconds = get_utc_offset(tz_info)
    display_clock(utc_offset_seconds)
    display.display()

    save_cache(cache)
    _log(
        "loop() done in",
        time.ticks_diff(time.ticks_ms(), start_time_ticks),
        "ms ticks",
    )
    if not go_to_sleep():
        start_time_ticks = time.ticks_ms()


def get_utc_offset(tz_info):
    return tz_info["raw_offset"] + (tz_info["dst_offset"] if tz_info["dst"] else 0)


def go_to_sleep():
    display.einkOff()

    reset_refresh_sec = (
        APPROX_REFRESH_DURATION_AFTER_DEEPSLEEP_RESET
        if machine.reset_cause() == machine.DEEPSLEEP_RESET
        else APPROX_COLD_BOOT_REFRESH_DURATION
    )
    hot_refresh_seconds = 8

    sleep_time_seconds = (
        dateutil.next_full_minute() - dateutil.now_epoch() - reset_refresh_sec
    )
    # sleep only if it makes sense
    if sleep_time_seconds > hot_refresh_seconds:
        _log("going into deep sleep for", sleep_time_seconds, "seconds")
        machine.deepsleep(sleep_time_seconds * 1000)
    else:
        return False


def connect_wifi(config, cache):
    wifi_conf = config["wifi"]
    ssid = wifi_conf["ssid"]
    show_status_message(f"Connecting to WiFi '{ssid}'")
    ip, _, _, _ = netutil.do_connect(ssid, wifi_conf.get("key", None))
    show_status_message(f"Connected to {ssid} ({ip})")
    cache["last_connected_wifi"] = config["wifi"]["ssid"]


def load_cache():
    try:
        with open("/cache.json", encoding="utf-8") as cache_file:
            cache_dict = json.load(cache_file)
        if not isinstance(cache_dict, dict):
            raise TypeError(
                f"loaded cache was not a dict, it was a '{type(cache_dict).__name__}'"
            )
        return cache_dict

    except (OSError, TypeError) as e:
        _log("failed to load cache :( ", type(e).__name__, str(e))
        return dict()


def save_cache(cache):
    with open("/cache.json", "wt", encoding="utf-8") as json_file:
        json.dump(cache, json_file)


def main():
    try:
        while True:
            config = load_config()
            cache = load_cache()
            loop(config, cache)

    except KeyboardInterrupt:
        raise
    except Exception as e:
        default_exc_handler(e)


def default_exc_handler(e):
    sys.print_exception(e)
    with open("/error.log", mode="wt", encoding="utf-8") as error_log_file:
        error_log_file.write(f"\n{dateutil.now_epoch()}\n")
        sys.print_exception(e, error_log_file)

    machine.reset()
