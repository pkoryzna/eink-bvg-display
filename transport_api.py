import requests

URL_TEMPLATE = "https://v6.vbb.transport.rest/stops/{}/departures/"

UNRESERVED_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"


def _log(*args, **kwargs):
    print(*args, end="")
    if kwargs:
        print(kwargs)
    print()


def _percent_hex(bs):
    return "".join("%" + hex(b).lstrip("0x").ljust(2, "0") for b in bs)


def _percent_encode_query(value: str) -> str:
    encoded = ""

    for ch in value:
        if ch in UNRESERVED_CHARS:
            encoded += ch
        else:
            bytez = ch.encode("utf-8")
            encoded += _percent_hex(bytez)

    return encoded


def _run_request(url: str, method: str, timeout: int=5):
    response = requests.request(
        method=method,
        url=url,
        timeout=timeout
    )
    if response.status_code < 200 or response.status_code > 299:
        raise ValueError("response was not successful!", response)

    return response


def departures_url(stop_id: str, params: dict[str, str]) -> str:
    templated = URL_TEMPLATE.format(stop_id)
    if params:
        templated += "?"
        templated += "&".join(
            _percent_encode_query(name) + "=" + _percent_encode_query(value)
            for name, value in params.items()
        )

    return templated


def get_departures(stop_id: str, duration: int = 50, cache: dict[str, dict] = dict(), now_epoch: int = 0) -> any:
    params = {
        "duration": str(duration),
    }
    url = departures_url(stop_id, params)
    result_json = _run_request(
        method="GET",
        url=url,
    ).json()
    departures = result_json.get("departures")
    if departures is not None:
        return departures
    raise KeyError(f"missing departures in response: {result_json}")
