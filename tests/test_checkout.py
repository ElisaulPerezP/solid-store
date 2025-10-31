# tests/test_checkout.py
from decimal import Decimal
import pytest

from src.checkout_dirty import checkout

def base_inventory():
    # Prices/weights as Decimals for precision
    return {
        "BK1": {"name": "Clean Code", "category": "BOOK", "price": Decimal("30.00"), "weight": Decimal("0.5"), "stock": 10},
        "ST1": {"name": "Notebook A5", "category": "STATIONERY", "price": Decimal("5.00"), "weight": Decimal("0.2"), "stock": 100},
        "ST2": {"name": "Pen Blue", "category": "STATIONERY", "price": Decimal("2.00"), "weight": Decimal("0.05"), "stock": 50},
        "DG1": {"name": "Ebook SOLID", "category": "DIGITAL", "price": Decimal("15.00"), "weight": Decimal("0.0"), "stock": 999999999},
    }

def test_simple_order_card_standard():
    inv = base_inventory()
    order = {
        "lines": [{"sku":"BK1","qty":1}, {"sku":"ST1","qty":2}],
        "shipping": {"method": "standard"},
        "coupons": [],
        "payment": {"method": "card"}
    }
    res = checkout(order, inv, customer={"store_credit": Decimal("0.00")})

    # Subtotal: 30 + 2*5 = 40
    assert res["subtotal_after_discounts"] == Decimal("40.00")
    # Taxes: BOOK 4% of 30 = 1.20; STATIONERY 19% of 10 = 1.90; total 3.10
    assert res["tax_total"] == Decimal("3.10")
    # Shipping standard <=2kg => 5.00
    assert res["shipping_cost"] == Decimal("5.00")
    # Card fee 2% of (40+3.10+5) = 0.96
    assert res["payment_fee"] == Decimal("0.96")
    # Final total = 49.06
    assert res["total"] == Decimal("49.06")

    # Inventory should decrease (not for digital)
    assert inv["BK1"]["stock"] == 9
    assert inv["ST1"]["stock"] == 98

def test_free_shipping_with_save10_bank_transfer():
    inv = base_inventory()
    order = {
        "lines": [{"sku":"BK1","qty":4}],  # 4 * 30 = 120
        "shipping": {"method": "standard"},
        "coupons": ["SAVE10"],
        "payment": {"method": "bank_transfer"}
    }
    res = checkout(order, inv, customer={})

    # After SAVE10 on non-digital: 120 * 0.90 = 108.00
    assert res["subtotal_after_discounts"] == Decimal("108.00")
    # Free standard shipping
    assert res["free_shipping"] is True
    assert res["shipping_cost"] == Decimal("0.00")
    # Tax: BOOK 4% on 108 = 4.32
    assert res["tax_total"] == Decimal("4.32")
    # Final without fees = 112.32
    assert res["total"] == Decimal("112.32")
    assert res["hold_days"] == 2

def test_express_shipping_overweight_bulk5_store_credit():
    inv = base_inventory()
    order = {
        "lines": [
            {"sku":"ST1","qty":12},  # 12*5=60, 12*0.2kg=2.4kg
            {"sku":"ST2","qty":4},   # 4*2=8,  4*0.05kg=0.2kg
            {"sku":"DG1","qty":1},   # 15,     0kg
        ],
        "shipping": {"method": "express"},
        "coupons": ["BULK5"],  # qty total = 17 => bulk applies
        "payment": {"method": "store_credit"}
    }
    customer = {"store_credit": Decimal("200.00")}
    res = checkout(order, inv, customer=customer)

    # Expected total: 106.12 (checked in spec)
    assert res["total"] == Decimal("106.12")
    # Credit deducted
    assert customer["store_credit"] == Decimal("93.88")
    # Express over 2.0 kg => base 10 + one started kg * 5 = 15
    assert res["shipping_cost"] == Decimal("15.00")

def test_insufficient_stock_raises():
    inv = base_inventory()
    order = {
        "lines": [{"sku":"ST2","qty":9999}],
        "shipping": {"method": "standard"},
        "coupons": [],
        "payment": {"method": "card"}
    }
    with pytest.raises(ValueError):
        checkout(order, inv, customer={})

def test_booklover_and_save10_compose():
    inv = base_inventory()
    order = {
        "lines": [{"sku":"BK1","qty":1}, {"sku":"ST2","qty":1}, {"sku":"DG1","qty":1}],
        "shipping": {"method": "standard"},
        "coupons": ["BOOKLOVER", "SAVE10"],
        "payment": {"method": "card"}
    }
    res = checkout(order, inv, customer={})
    # Expected final total from spec: 46.93
    assert res["total"] == Decimal("46.93")

def test_store_credit_insufficient_raises():
    inv = base_inventory()
    order = {
        "lines": [{"sku":"BK1","qty":1}],
        "shipping": {"method": "standard"},
        "coupons": [],
        "payment": {"method": "store_credit"}
    }
    with pytest.raises(ValueError):
        checkout(order, inv, customer={"store_credit": Decimal("10.00")})
