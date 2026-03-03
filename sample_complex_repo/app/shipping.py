STANDARD_SHIPPING = 7.5
FREE_SHIPPING_THRESHOLD = 100.0


def shipping_cost(discounted_subtotal: float) -> float:
    # Bug: threshold should include 100.0 exactly.
    if discounted_subtotal > FREE_SHIPPING_THRESHOLD:
        return 0.0
    return STANDARD_SHIPPING
