from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, List, Dict, Union
from .color import Color

if TYPE_CHECKING:
    pass

__all__ = ["Table", "TableStyle", "Column", "ColumnStyle", "Alignment", "Color16", "RGBColor"]


class Alignment(Enum):
    LEADING = 0
    CENTER = 1
    TRAILING = 2


Row = Dict[str, str]


@dataclass
class ColumnStyle:
    color: Color = None
    bold: bool = False
    width: int = 0
    alignment: Alignment = Alignment.LEADING
    padding: int = 1


@dataclass
class Column:
    key: str
    title: str
    style: ColumnStyle


class LayoutedColumn(Column):
    calculated_width: int = None

    def __init__(self, column: Column):
        super().__init__(key=column.key, title=column.title, style=column.style)

    def cell_text(self, text: str):
        padding = ' ' * self.style.padding
        w = self.calculated_width - self.style.padding * 2
        fmt = "%s%%-%ds%s" % (padding, w, padding)
        if len(text) > w:
            text = text[0:w - 3] + "..."
        return fmt % text


@dataclass
class TitleStyle:
    color: Color = None
    bold: bool = True
    alignment: Alignment = Alignment.LEADING


@dataclass
class TableStyle:
    border_color: Color = None
    title_style: TitleStyle = TitleStyle()
    width: int = 0


class Table:
    def __init__(self, columns: List[Column], rows: List[Row], style: TableStyle):
        self.columns = columns
        self.rows = rows
        self.style = style

    def update_row(self, index: int, row: Row):
        self.rows[index] = row

    def _layout(self) -> List[LayoutedColumn]:
        result = []
        s = 0
        for c in self.columns:
            lc = LayoutedColumn(c)
            result.append(lc)
            if c.style.width == 0:
                lc.calculated_width = max(len(c.title), max([len(row[c.key]) for row in self.rows])) + c.style.padding * 2
                s += lc.calculated_width
            if c.style.width > 0:
                lc.calculated_width = c.style.width
        if s < self.style.width:
            unmeasured_cols = [c for c in result if not c.calculated_width]
            n = len(unmeasured_cols)
            r = self.style.width - s
            w = int(r / n)
            for c in unmeasured_cols:
                if r > w:
                    c.calculated_width = w
                else:
                    c.calculated_width = r
                r -= w
        else:
            raise RuntimeError("Failed layout table")
        return result

    @property
    def border_style(self) -> str:
        return "\033[90m"

    @property
    def title_style(self) -> str:
        return "\033[0;1m"

    def _get_header_cell(self, column: LayoutedColumn) -> str:
        return column.cell_text(column.title)

    def _get_body_cell(self, row: Row, column: LayoutedColumn) -> str:
        return column.cell_text(row[column.key])

    def __str__(self):
        columns = self._layout()
        lines = []
        reset = "\033[0m"
        separators = ['─' * c.calculated_width for c in columns]
        headers = [self._get_header_cell(c) for c in columns]
        fmt1 = f"\033[K{self.border_style}┌%s┐{reset}"
        fmt2 = f"\033[K{self.border_style}│{reset}%s{self.border_style}│{reset}"
        fmt3 = f"\033[K{self.border_style}├%s┤{reset}"
        fmt4 = f"\033[K{self.border_style}└%s┘{reset}"
        lines.append(fmt1 % '┬'.join(separators))
        lines.append(fmt2 % f'{self.border_style}│{reset}'.join(headers))
        for row in self.rows:
            lines.append(fmt3 % '┼'.join(separators))
            lines.append(fmt2 % f'{self.border_style}│{reset}'.join([self._get_body_cell(row, c) for c in columns]))
        lines.append(fmt4 % '┴'.join(separators))
        return '\n'.join(lines)
