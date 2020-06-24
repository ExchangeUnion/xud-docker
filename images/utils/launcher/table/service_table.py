from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from .base import Table, Column, TableStyle, ColumnStyle
from .color import Color

if TYPE_CHECKING:
    pass


class ServiceTable(Table):
    def __init__(self, services: Dict[str, str]):
        super().__init__(
            columns=[
                Column(
                    key="service",
                    title="SERVICE",
                    style=ColumnStyle(color=Color.blue()),
                ),
                Column(
                    key="status",
                    title="STATUS",
                    style=ColumnStyle(width=-1),
                ),
            ],
            rows=[{
                "service": key,
                "status": value,
            } for key, value in services.items()],
            style=TableStyle(width=62))
        self.services = services

    def update_service_status(self, service: str, status: str):
        index = list(self.services.keys()).index(service)
        self.update_row(index, {
            "service": service,
            "status": status
        })
