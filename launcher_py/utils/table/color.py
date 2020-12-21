from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass


class Color:
    def __init__(self, type: str, **kwargs):
        self.type = type
        self.value = kwargs

    @classmethod
    def rgb(cls, red: int, green: int, blue: int) -> Color:
        return Color(type="24-bit", red=red, green=green, blue=blue)

    @classmethod
    def black(cls) -> Color:
        return Color(type="4-bit", code=0)

    @classmethod
    def red(cls) -> Color:
        return Color(type="4-bit", code=1)

    @classmethod
    def green(cls) -> Color:
        return Color(type="4-bit", code=2)

    @classmethod
    def yellow(cls) -> Color:
        return Color(type="4-bit", code=3)

    @classmethod
    def blue(cls) -> Color:
        return Color(type="4-bit", code=4)

    @classmethod
    def magenta(cls) -> Color:
        return Color(type="4-bit", code=5)

    @classmethod
    def cyan(cls) -> Color:
        return Color(type="4-bit", code=6)

    @classmethod
    def white(cls) -> Color:
        return Color(type="4-bit", code=7)

    @classmethod
    def light_black(cls) -> Color:
        return Color(type="4-bit", code=8)

    @classmethod
    def light_red(cls) -> Color:
        return Color(type="4-bit", code=9)

    @classmethod
    def light_green(cls) -> Color:
        return Color(type="4-bit", code=10)

    @classmethod
    def light_yellow(cls) -> Color:
        return Color(type="4-bit", code=11)

    @classmethod
    def light_blue(cls) -> Color:
        return Color(type="4-bit", code=12)

    @classmethod
    def light_magenta(cls) -> Color:
        return Color(type="4-bit", code=13)

    @classmethod
    def light_cyan(cls) -> Color:
        return Color(type="4-bit", code=14)

    @classmethod
    def light_white(cls) -> Color:
        return Color(type="4-bit", code=15)

    @classmethod
    def color256(cls, code) -> Color:
        return Color(type="8-bit", code=code)

