import logging
import sys

from PIL import Image, ImageDraw, ImageFont

LOGGER = logging.getLogger(__name__)


def draw_char(font: ImageFont.ImageFont, char: str) -> Image.Image:
    bbox = font.getbbox(char)
    _, _, width, height = bbox
    img = Image.new(
        "1",
        (width, height),
    )
    draw = ImageDraw.Draw(img)
    draw.text((0, 0), char, fill=1, font=font)
    return img


def to_gfx_bytes(img: Image.Image) -> bytes:
    width, height = img.size

    bit_counter = 0
    font_bytes = bytearray()
    byte = 0

    for y in range(0, height):  # from top to bottom
        debug_line = ""
        for x in range(0, width):  # from left to right
            pixel = bool(img.getpixel((x, y)))
            byte |= pixel << bit_counter
            bit_counter += 1
            if bit_counter == 8:
                font_bytes.append(byte)
                bit_counter = byte = 0
            if LOGGER.level == logging.DEBUG:
                debug_line += "⬛️" if pixel else "⬜️"
        LOGGER.debug(debug_line)
    if bit_counter > 0:
        font_bytes.append(byte)
    return bytes(font_bytes)


def convert_font(
    font, alphabet: list[str | tuple[str, str]]
) -> dict[str, tuple[int, int, bytes]]:
    font_dict = {}
    for character in alphabet:
        LOGGER.debug("Converting '%s'", character)
        if isinstance(character, str):
            char_name, img = character, draw_char(font, character)
        elif isinstance(character, tuple):
            char_name, text_to_draw = character
            img = draw_char(font, text_to_draw)
        else:
            raise TypeError(
                f"invalid type for alphabet element: {type(character).__name__}"
            )
        width, height = img.size
        bs = to_gfx_bytes(img)
        font_dict[char_name] = width, height, bs
    return font_dict


def dump_font_module(font_dict: dict[str, tuple[int, int, bytes]]) -> str:
    return f"font_dict={repr(font_dict)}"


def parse_args():
    import argparse
    import string

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug", action="store_true", help="enable debug logging (print glyphs)"
    )
    parser.add_argument("--font", help="font name", required=True)
    parser.add_argument("--style", help="style name", required=False, default=None)
    parser.add_argument("--size", help="font size in pixels", type=int, required=True)
    parser.add_argument(
        "--alphabet", help="characters to include", default=string.printable
    )
    parser.add_argument(
        "--extra-chars",
        help="special characters list, format is 'SUN:☀️;CLOUD:☁️;...'",
        default="",
    )
    parser.add_argument(
        "--filename", help="Python file name to save", default=None, required=False
    )
    return parser.parse_args()


def parse_extra_chars(extra_chars_arg: str) -> list[tuple[str, str]]:
    if not extra_chars_arg:
        return []
    parts = [tuple(part.strip().split(":")) for part in extra_chars_arg.split(";")]
    extra_chars_pairs = []

    for part in parts:
        match part:
            case () | "":
                pass
            case [name, char]:
                extra_chars_pairs.append((name, char))
            case not_a_pair:
                raise ValueError(f"invalid extra char input: '{':'.join(not_a_pair)}'")
    return extra_chars_pairs


def create_font(name, style_name, size):
    face_index = 0
    font = ImageFont.truetype(name, size=size, encoding="unic", index=face_index)
    if not style_name:
        return font

    try:
        font.set_variation_by_name(style_name)
        return font
    except OSError:
        pass

    try:
        while font.getname()[1] != style_name:
            face_index += 1
            font = ImageFont.truetype(
                name, size=size, encoding="unic", index=face_index
            )
            LOGGER.debug("trying index %s: %s", face_index, font.getname())
        return font
    except OSError:
        raise KeyError(f"Could not open a font for {name, style_name}")


def main():
    from pathlib import Path

    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s :: %(levelname)-8s :: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    args = parse_args()
    LOGGER.setLevel(logging.DEBUG if args.debug else logging.INFO)
    size = int(args.size)
    font = create_font(args.font, args.style, args.size)

    alphabet = list(args.alphabet)
    alphabet.extend(parse_extra_chars(args.extra_chars))
    alphabet.append(("UNKNOWN", "\N{REPLACEMENT CHARACTER}"))
    font_dict = convert_font(font, alphabet)

    fontname, style = font.getname()
    if args.filename is not None:
        filename = args.filename
    else:
        filename = (
            f"{fontname.replace(' ', '_')}{style.replace(' ', '_')}{font.size}.py"
        )

    bytes_written = Path(filename).write_text(dump_font_module(font_dict))
    LOGGER.info(
        "Created %d dict entries for %s %s %d and wrote %d bytes to %s.",
        len(font_dict),
        fontname,
        style,
        size,
        bytes_written,
        filename,
    )


if __name__ == "__main__":
    main()
