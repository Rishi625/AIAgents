from .models import LineItem
from .pricing import discounted_subtotal
from .shipping import shipping_cost


STATE_TAX_RATE = {
    "CA": 0.0825,
    "NY": 0.04,
    "TX": 0.0625,
}


def calculate_order_total(
    items: list[LineItem],
    state: str,
    coupon_code: str | None = None,
    loyalty_points: int = 0,
) -> float:
    discounted = discounted_subtotal(
        items=items,
        coupon_code=coupon_code,
        loyalty_points=loyalty_points,
    )
    tax_rate = STATE_TAX_RATE.get(state.strip().upper(), 0.05)
    # Bug: tax is multiplied by 100, causing inflated totals.
    tax_amount = discounted * tax_rate * 100
    ship = shipping_cost(discounted)
    return round(discounted + tax_amount + ship, 2)
