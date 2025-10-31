# src/checkout_dirty.py
# WARNING: This is intentionally "dirty" code:
# - God function doing too many things.
# - Hard-coded strings and magic numbers.
# - Mixed calculations, rounding, inventory mutation, and payment processing.
# - No abstractions / interfaces / dependency inversion.
# Goal: It passes the tests but violates SOLID principles.

from decimal import Decimal, ROUND_HALF_UP, getcontext
getcontext().rounding = ROUND_HALF_UP

def _q2(x):
    # Quantize to 2 decimal places with HALF_UP
    if not isinstance(x, Decimal):
        x = Decimal(str(x))
    return x.quantize(Decimal("0.01"))

def checkout(order, inventory, customer=None):
    if customer is None:
        customer = {}

    # Constants (magic numbers inlined: still "dirty")
    TAX_RATES = {
        "BOOK": Decimal("0.04"),
        "STATIONERY": Decimal("0.19"),
        "DIGITAL": Decimal("0.00"),
    }
    SHIPPING_BASE = {
        "standard": (Decimal("5.00"), Decimal("2.00")),   # base, per-started-kg over 2.0
        "express":  (Decimal("10.00"), Decimal("5.00")),
    }
    FREE_SHIP_THRESHOLD = Decimal("100.00")
    CARD_FEE = Decimal("0.02")

    # Gather inputs
    lines = order.get("lines") or []
    shipping_method = (order.get("shipping") or {}).get("method", "standard")
    coupons = order.get("coupons") or []
    payment_method = (order.get("payment") or {}).get("method", "card")

    # Validate shipping method
    if shipping_method not in SHIPPING_BASE:
        raise ValueError("Unsupported shipping method")

    # Clone inventory-like view (still mutating later – dirty)
    # For DIGITAL we ignore stock
    # Accumulators
    line_results = []
    total_weight = Decimal("0")
    subtotal_before_discounts = Decimal("0")
    qty_total = 0

    # Pre-scan for inventory and basic sums
    for item in lines:
        sku = item["sku"]
        qty = Decimal(str(item["qty"]))
        if sku not in inventory:
            raise ValueError(f"Unknown SKU: {sku}")
        rec = inventory[sku]
        category = rec["category"]
        price = Decimal(str(rec["price"]))
        weight = Decimal(str(rec["weight"]))
        stock = rec.get("stock", None)

        if category != "DIGITAL":
            if stock is None:
                raise ValueError(f"Missing stock for {sku}")
            if qty > Decimal(str(stock)):
                raise ValueError(f"Insufficient stock for {sku}")

        qty_total += int(qty)
        subtotal_before_discounts += price * qty
        total_weight += weight * qty

    # Apply coupons in order:
    #   1) category coupons -> apply per line where category matches
    #   2) SAVE10 -> 10% to non-digital
    #   3) BULK5 -> 5% if qty_total >= 10, applied to all
    # We'll do this in a very coupled way per line (dirty), duplicating logic.
    # Build line contexts
    for item in lines:
        sku = item["sku"]
        qty = Decimal(str(item["qty"]))
        rec = inventory[sku]
        category = rec["category"]
        base_price = Decimal(str(rec["price"]))

        # price after sequential coupons
        price_after = base_price

        # 1) Category coupon(s)
        # (Currently only BOOKLOVER)
        if "BOOKLOVER" in coupons and category == "BOOK":
            price_after = _q2(price_after * Decimal("0.85"))

        # 2) SAVE10 on non-digital
        if "SAVE10" in coupons and category in ("BOOK", "STATIONERY"):
            price_after = _q2(price_after * Decimal("0.90"))

        # 3) BULK5 if qty_total >= 10 (applies to everything)
        if "BULK5" in coupons and qty_total >= 10:
            price_after = _q2(price_after * Decimal("0.95"))

        # store line
        line_total = _q2(price_after * qty)
        line_results.append({
            "sku": sku,
            "category": category,
            "qty": int(qty),
            "unit_price_final": price_after,
            "line_subtotal": line_total
        })

    # Subtotal post-discounts
    subtotal_after_discounts = sum((l["line_subtotal"] for l in line_results), Decimal("0.00"))

    # Shipping
    base_fee, per_kg = SHIPPING_BASE[shipping_method]
    # Free standard shipping rule (based on post-discount subtotal)
    free_shipping = shipping_method == "standard" and (subtotal_after_discounts >= FREE_SHIP_THRESHOLD)
    if free_shipping:
        shipping_cost = Decimal("0.00")
    else:
        if total_weight <= Decimal("2.00"):
            shipping_cost = base_fee
        else:
            # per started kg beyond 2.0 kg
            over = total_weight - Decimal("2.00")
            # "ceil" for Decimals
            over_kg_started = (int(over) if over == int(over) else int(over) + 1)
            shipping_cost = base_fee + per_kg * Decimal(str(over_kg_started))
        shipping_cost = _q2(shipping_cost)

    # Taxes (per line, after discounts)
    tax_total = Decimal("0.00")
    for l in line_results:
        rate = TAX_RATES[l["category"]]
        # tax per line with rounding half-up
        tax_line = _q2(l["line_subtotal"] * rate)
        l["tax_line"] = tax_line
        tax_total += tax_line
    tax_total = _q2(tax_total)

    # Base total before payment fee
    base_total = _q2(subtotal_after_discounts + tax_total + shipping_cost)

    # Payment handling
    hold_days = 0
    payment_fee = Decimal("0.00")
    if payment_method == "card":
        payment_fee = _q2(base_total * CARD_FEE)
    elif payment_method == "bank_transfer":
        hold_days = 2
    elif payment_method == "store_credit":
        # Check credit
        credit = _q2(customer.get("store_credit", Decimal("0.00")))
        final_candidate = _q2(base_total + payment_fee)
        if credit < final_candidate:
            raise ValueError("Insufficient store credit")
        # Deduct credit (mutating external state – dirty)
        customer["store_credit"] = _q2(credit - final_candidate)
    else:
        raise ValueError("Unsupported payment method")

    final_total = _q2(base_total + payment_fee)

    # Now mutate inventory stocks (mixing concerns – dirty)
    for l in line_results:
        sku = l["sku"]
        rec = inventory[sku]
        if rec["category"] != "DIGITAL":
            rec["stock"] = int(Decimal(str(rec["stock"])) - Decimal(str(l["qty"])))

    # Return a very concrete dict (no abstraction)
    return {
        "lines": line_results,
        "subtotal_before_discounts": _q2(subtotal_before_discounts),
        "subtotal_after_discounts": _q2(subtotal_after_discounts),
        "shipping_cost": shipping_cost,
        "tax_total": tax_total,
        "payment_fee": payment_fee,
        "total": final_total,
        "hold_days": hold_days,
        "free_shipping": free_shipping,
        "weight": _q2(total_weight),
        "payment_method": payment_method,
        "shipping_method": shipping_method
    }
