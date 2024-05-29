import requests
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


def get_tz_info_for_my_ip(cache, config):
    if check_needed(cache, config):
        _log("fetching TZ info from current IP")
        cache["last_tz_response"] = _run_request(TIME_API_IP_URL, "GET")
    return cache["last_tz_response"]

def check_needed(cache: dict, config: dict) -> bool:
    if cache.get("last_connected_wifi", "") != config["wifi"]["ssid"]:
        return True

    last_tz_resp = cache.get("last_tz_response")
    if not last_tz_resp:
        return True
    
    last_check_iso = last_tz_resp["datetime"]
    last_check_epoch = dateutil.parse_iso(last_check_iso)
    now_epoch = dateutil.now_epoch()
    if now_epoch - last_check_epoch > 12*60*60:
        return True
    if last_tz_resp["dst"]:
        if now_epoch > dateutil.parse_iso(last_tz_resp["dst_until"]):
            return True
    else:
        if now_epoch > dateutil.parse_iso(last_tz_resp["dst_from"]):
            return True
        
    return False