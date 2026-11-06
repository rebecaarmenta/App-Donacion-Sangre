"""Identificadores aleatorios cortos basados en UUID4."""
from __future__ import annotations

import uuid

from ..ports.ids import IdGenerator


class UuidIdGenerator(IdGenerator):
    def __init__(self, length: int = 8) -> None:
        self._length = length

    def new_id(self) -> str:
        return uuid.uuid4().hex[: self._length]
