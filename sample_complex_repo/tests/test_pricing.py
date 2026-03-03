from app.models import LineItem
from app.pricing import discounted_subtotal, parse_coupon_rate


def test_parse_coupon_rate_percentage_to_decimal() -> None:
    assert parse_coupon_rate("save10") == 0.10


def test_discounted_subtotal_coupon_and_loyalty() -> None:
    items = [LineItem("A", 40.0, 3)]  # 120.00 subtotal
    assert discounted_subtotal(items, coupon_code="SAVE10", loyalty_points=10) == 98.0
