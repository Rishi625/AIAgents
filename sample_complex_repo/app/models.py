from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class LineItem:
    sku: str
    unit_price: float
    quantity: int

    @property
    def total(self) -> float:
        return round(self.unit_price * self.quantity, 2)


def order_subtotal(items: Iterable[LineItem]) -> float:
    return round(sum(item.total for item in items), 2)
