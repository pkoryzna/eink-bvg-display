import requests
from cache import StateCache
import dateutil

TIME_API_IP_URL = "http://worldtimeapi.org/api/ip"

def _log(*args, **kwargs):
    print(*args, end=" ")
    if kwargs:
        print(kwargs)
    else:
        print()

def _run_request(url: str, method: str):
    # _log("http request", method=method, url=url)
    return requests.request(
        method=method,
        url=url,
    ).json()


def get_tz_info_for_my_ip(cache: StateCache, config):
    if check_needed(cache, config):
        _log("fetching TZ info from current IP")
        cache.last_tz_response = _run_request(TIME_API_IP_URL, "GET")
    return cache.last_tz_response

def check_needed(cache: StateCache, config: dict) -> bool:
    if cache.last_connected_wifi_ssid != config["wifi"]["ssid"]:
        return True

    last_tz_resp = cache.last_tz_response
    if not last_tz_resp:
        return True
    
    last_check_iso = last_tz_resp["datetime"]
    last_check_epoch = dateutil.parse_iso(last_check_iso)
    now_epoch = dateutil.now_epoch()
    if now_epoch - last_check_epoch > 12*60*60:
        return True
    
    is_dst = last_tz_resp["dst"]

    if is_dst:
        until_str = last_tz_resp["dst_until"]
        if until_str is not None and now_epoch > dateutil.parse_iso(until_str):
            return True
    else:
        from_str = last_tz_resp["dst_from"]
        if from_str is not None and now_epoch > dateutil.parse_iso(from_str):
            return True
        
    return False