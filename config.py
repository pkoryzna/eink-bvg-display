import json
import re


def _check_config(config: any) -> dict[str, list[str | dict[str, str]]]:
    has_keys = isinstance(config, dict) and all(
        key in config
        for key in (
            "stops",
            "remove_phrases",
            # "my_zone",
            "lines_directions",
            "wifi",
        )
    )

    lines_directions_valid = all(
        "line_name" in item and "direction_regex" in item
        for item in config["lines_directions"]
    )

    wifi_valid = "ssid" in config["wifi"] and "key" in config["wifi"]

    config_valid = has_keys and lines_directions_valid and wifi_valid
    if not config_valid:
        raise ValueError(f"config: {config} was invalid")
    config["lines_directions"] = _compile(config["lines_directions"])
    return config


def load_config():
    with open("config.json") as config_file:
        config = json.load(config_file)
    return _check_config(config)


def _compile(
    lines_directions: list[dict[str, str]]
) -> list[tuple[str, re.Pattern, re.Pattern | None]]:
    compiled = []
    for item in lines_directions:
        line_name = item["line_name"]
        direction_regex = re.compile(item["direction_regex"])

        except_regex = None
        if "except_regex" in item:
            except_regex = re.compile(item["except_regex"])

        compiled.append(
            {
                "line_name": line_name,
                "direction_regex": direction_regex,
                "except_regex": except_regex,
            }
        )

    return compiled
