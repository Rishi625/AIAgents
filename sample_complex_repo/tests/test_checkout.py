from app.checkout import calculate_order_total
from app.models import LineItem
from app.shipping import shipping_cost


def test_shipping_is_free_at_threshold() -> None:
    assert shipping_cost(100.0) == 0.0


def test_calculate_order_total_with_coupon() -> None:
    items = [LineItem("A", 40.0, 3)]  # 120 subtotal
    # Expected:
    # discounted = 120 - 12 - 10 = 98
    # tax (NY 4%) = 3.92
    # shipping (below threshold) = 7.5
    # total = 109.42
    assert calculate_order_total(items, state="NY", coupon_code="SAVE10", loyalty_points=10) == 109.42
