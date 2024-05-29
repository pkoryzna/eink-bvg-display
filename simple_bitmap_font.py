from framebuf import FrameBuffer, MONO_HMSB


class MonoFont:
    OFFSCREEN = 9001

    LEFT = 0
    RIGHT = 1
    CENTER = 2

    def __init__(
        self,
        font_dict: dict[str, tuple[int, int, bytes]],
        preload_chars: bool | list[str] = False,
        foreground_color: int = 1,
        background_color: int = 0,
        y_offset: int = 0,
    ) -> None:
        self._char_fb_cache = dict()
        self._font_dict = font_dict
        self._unknown_char = self._font_dict["UNKNOWN"]
        self._foreground_color = foreground_color
        self._background_color = background_color
        self._line_height = max(h for _, h, _ in font_dict.values())
        print(f"detected line height: {self._line_height}")
        if preload_chars:
            temp_fb = FrameBuffer(bytearray(1), 1, 1, MONO_HMSB)

            if isinstance(preload_chars, list):
                self.draw_text(
                    temp_fb, preload_chars, MonoFont.OFFSCREEN, MonoFont.OFFSCREEN
                )
            else:
                self.draw_text(
                    temp_fb,
                    list(self._font_dict.keys()),
                    MonoFont.OFFSCREEN,
                    MonoFont.OFFSCREEN,
                )
                self._font_dict = dict()
            print("font cache preheated")

    @micropython.native
    @classmethod
    def _draw_char_fb(cls, char_data: bytes, width: int, height: int, fg: int, bg: int):
        fb_buf = bytearray(width * height)
        fb = FrameBuffer(fb_buf, width, height, MONO_HMSB)
        char_x = char_y = 0
        for byte in char_data:
            bit = 0
            while bit < 8:
                pixel = byte & (1 << bit)
                fb.pixel(char_x, char_y, fg if pixel else bg)

                char_x += 1
                bit += 1
                if char_x == width:
                    char_x = 0
                    char_y += 1
                if char_y == height:
                    break
        return fb

    @micropython.native
    def _draw_char(
        self,
        display: FrameBuffer | None,
        char: str,
        x: int,
        y: int,
        transparent: bool = False,
    ):
        cached = self._char_fb_cache.get(char)
        if cached:
            width, height, char_fb = cached
        else:
            chr_tuple = self._font_dict.get(char)
            if chr_tuple:
                width, height, char_data = chr_tuple
            else:
                width, height, char_data = self._unknown_char
            char_fb = self._draw_char_fb(
                char_data, width, height, self._foreground_color, self._background_color
            )
            self._char_fb_cache[char] = width, height, char_fb
        if display:
            display.blit(char_fb, x, y, self._background_color if transparent else -1)
        return width, height

    def draw_text(
        self,
        display: FrameBuffer,
        text: str | list[str],
        x: int,
        y: int,
        transparent: bool = False,
        align: int = LEFT,
    ):
        if align == MonoFont.RIGHT:
            width, _ = self.get_text_size(text)
            x -= width
        elif align == MonoFont.CENTER:
            width, _ = self.get_text_size(text)
            x -= width // 2

        return self._draw_text(display, text, x, y, transparent)

    def get_text_size(self, text: str | list[str]) -> tuple[int, int]:
        _, _, width, height = self._draw_text(
            None,
            text,
            0,
            0,
        )
        return width, height

    @micropython.native
    def _draw_text(
        self,
        display: FrameBuffer | None,
        text: str | list[str],
        x: int,
        y: int,
        transparent: bool = False,
    ):
        bracket_counter = 0
        special_char = ""

        display_x = x

        for ch in text:
            w = 0

            if ch == "{":
                if bracket_counter < 2:
                    bracket_counter += 1
                else:
                    # this is a 3rd '{' so let's print it
                    bracket_counter = 0
                    w, _ = self._draw_char(display, "{", display_x, y)
            elif ch == "}":
                if bracket_counter > 0:
                    bracket_counter -= 1
                if bracket_counter == 0 and special_char:
                    # this was the second '}', draw special now
                    w, _ = self._draw_char(display, special_char, display_x, y)
                    special_char = ""

            elif bracket_counter == 2:
                special_char += ch
            else:
                # reset bracket counter if there's only 1 and it wasn't followed up
                bracket_counter = 0
                if special_char:
                    raise ValueError(f"unclosed parenthesis: {special_char}}}")
                w, _ = self._draw_char(display, ch, display_x, y)

            if w:
                display_x += w
        return (x, y, display_x, y + self._line_height)
