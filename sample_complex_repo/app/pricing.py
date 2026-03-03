from .models import LineItem, order_subtotal


COUPON_PERCENT_BY_CODE = {
    "SAVE10": 10,
    "SAVE20": 20,
}


def parse_coupon_rate(coupon_code: str | None) -> float:
    if not coupon_code:
        return 0.0
    normalized = coupon_code.strip().upper()
    # Bug: this returns whole percentage (10) instead of decimal rate (0.10).
    return float(COUPON_PERCENT_BY_CODE.get(normalized, 0))


def apply_discounts(subtotal: float, coupon_rate: float, loyalty_points: int) -> float:
    coupon_discount = subtotal * coupon_rate
    after_coupon = subtotal - coupon_discount
    after_loyalty = after_coupon - max(0, loyalty_points)
    return round(after_loyalty, 2)


def discounted_subtotal(
    items: list[LineItem],
    coupon_code: str | None = None,
    loyalty_points: int = 0,
) -> float:
    subtotal = order_subtotal(items)
    coupon_rate = parse_coupon_rate(coupon_code)
    return apply_discounts(subtotal, coupon_rate, loyalty_points)
