"""Functions and types to deal with caching the state between reboots"""

import collections

import json

UIDeparture = collections.namedtuple(
    "UIDeparture", ("line_name", "direction", "time_left", "stop")
)


def _ui_departure_to_json_dict(departure: UIDeparture) -> dict:
    return {
        "line_name": departure.line_name,
        "direction": departure.direction,
        "time_left": departure.time_left,
        "stop": departure.stop,
    }


def _ui_departure_from_json_dict(json_dict: dict) -> UIDeparture:
    return UIDeparture(
        json_dict["line_name"],
        json_dict["direction"],
        json_dict["time_left"],
        json_dict["stop"],
    )


class StateCache:
    def __init__(
        self,
        last_rtc_ntp_update: int = 0,
        departures: list[UIDeparture] = [],
        last_departure_update: int = 0,
        last_tz_response: dict = dict(),
        last_connected_wifi_ssid: str = "",
    ) -> None:
        self.last_rtc_ntp_update = last_rtc_ntp_update
        self.departures = departures
        self.last_departure_update = last_departure_update
        self.last_tz_response = last_tz_response
        self.last_connected_wifi_ssid = last_connected_wifi_ssid

    def to_json_dict(self):
        return {
            "last_rtc_ntp_update": self.last_rtc_ntp_update,
            "last_departure_update": self.last_departure_update,
            "last_tz_response": self.last_tz_response,
            "last_connected_wifi_ssid": self.last_connected_wifi_ssid,
            "departures": [_ui_departure_to_json_dict(d) for d in self.departures],
        }

    @classmethod
    def load_cache(cls, path="/cache.json") -> "StateCache":
        try:
            with open(path, encoding="utf-8") as cache_file:
                cache_dict = json.load(cache_file)

            if not isinstance(cache_dict, dict):
                raise TypeError(
                    f"loaded cache was not a dict, it was a '{type(cache_dict).__name__}'"
                )
            cache_dict["departures"] = [_ui_departure_from_json_dict(dd) for dd in cache_dict["departures"]]
            return StateCache(**cache_dict)

        except (OSError, TypeError, ValueError) as e:
            _log("failed to load cache :( ", type(e).__name__, str(e))
            return StateCache()


    def perist(self, path="/cache.json"):
        with open(path, "wt", encoding="utf-8") as json_file:
            json.dump(self.to_json_dict(), json_file)
            _log("saved cache to", path)

    def __enter__(self):
        return self

    def __exit__(self):
        return self.perist()


def _log(*args, **kwargs):
    print(*args, end=" ")
    if kwargs:
        print(kwargs)
    else:
        print()
