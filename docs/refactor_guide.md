# Guía de refactorización SOLID (paso a paso)

Objetivo: transformar `checkout_dirty.py` en un diseño limpio, extensible y testeable **sin romper los tests**.

> Sugerencia: crea una carpeta `src/checkout/` y migra allí el código limpio por etapas; deja `checkout_dirty.py` intacto mientras mueves dependencias y cambias el import en tests al final.

---

## 1) S — Single Responsibility Principle

**Problema actual**: `checkout()` hace TODO (validación, descuentos, impuestos, envío, pago, inventario, redondeo).

**Acción**:
- Extrae servicios con responsabilidades únicas:
  - `PricingService` (aplica cupones, calcula subtotales).
  - `TaxService` (impuestos por línea).
  - `ShippingService` (costos por método/peso + free shipping).
  - `PaymentService` (fees, holds, cobros, store credit).
  - `InventoryService` (validación y decremento de stock).
  - `RoundingPolicy` (reglas de redondeo centralizadas).
- Crea un DTO/Value Object `CheckoutResult` (solo datos, sin lógica) para el output.
- Mantén un `CheckoutOrchestrator` delgado que coordine.

**Checklist**:
- [ ] No hay mutaciones de inventario dentro de pricing/tax/ship.
- [ ] Cada clase tiene 1 razón de cambio clara.

---

## 2) O — Open/Closed Principle

**Problema actual**: para agregar un cupón nuevo o un método de envío, hay que tocar `checkout()`.

**Acción**:
- Modela **estrategias de descuento**: interfaz `DiscountStrategy` con `apply(line_items, context)`; registra `BookLover`, `Save10`, `Bulk5`.
- Modela **estrategias de envío**: interfaz `ShippingStrategy` (`standard`, `express`) seleccionada por factoría.
- Modela **métodos de pago**: interfaz `PaymentMethod` (`Card`, `BankTransfer`, `StoreCredit`).

**Checklist**:
- [ ] Agregar un cupón/método no modifica código existente; solo se registra una nueva clase.

---

## 3) L — Liskov Substitution Principle

**Problema actual**: métodos con condicionales por tipo (`if method == "card": ...`).

**Acción**:
- Asegura que `PaymentMethod` cumpla mismo contrato: `compute_fee(total)`, `apply_post_payment(customer, amount)`, etc.
- `StoreCredit.apply_post_payment` no debe generar efectos colaterales extraños que rompan expectativas (p.ej., lanzar error solo si falta crédito, pero el resto se comporta como los demás).

**Checklist**:
- [ ] Cualquier `PaymentMethod` puede reemplazar a otro sin romper el flujo.

---

## 4) I — Interface Segregation Principle

**Problema actual**: se mezclaría una interfaz gigante si no se cuida (pago, impuestos, shipping…).

**Acción**:
- Interfaces pequeñas y específicas: `DiscountStrategy`, `ShippingStrategy`, `PaymentMethod`, `TaxRule`, `RoundingPolicy`.
- Evita “interfaces gordas”; no obligues a implementar métodos que no apliquen.

**Checklist**:
- [ ] Ninguna clase implementa métodos que no usa.

---

## 5) D — Dependency Inversion Principle

**Problema actual**: uso directo de diccionarios globales y literales mágicos.

**Acción**:
- Inyecta dependencias por constructor:
  - `PricingService(discount_strategies, rounding_policy)`
  - `TaxService(tax_table, rounding_policy)`
  - `ShippingService(strategy_factory, free_ship_threshold, rounding_policy)`
  - `PaymentService(payment_method_factory, rounding_policy)`
  - `InventoryService(stock_repository)`
- Define **abstracciones** (protocolos o ABC) para repositorios: `StockRepository`, `CustomerAccountRepository`.
- Orquesta todo en `CheckoutOrchestrator` recibiendo **interfaces**, no implementaciones concretas.

**Checklist**:
- [ ] Los servicios no conocen estructuras concretas; dependen de abstracciones inyectadas.
- [ ] Puedes “mockear” repos fácilmente en tests adicionales.

---

## Plan sugerido en iteraciones (manteniendo tests verdes)

1. **Mover redondeo** a `RoundingPolicy` y reemplazar llamadas directas.
2. **Extraer ShippingService** con dos estrategias (standard/express).
3. **Extraer TaxService** (tabla de tasas + cálculo por línea).
4. **Extraer DiscountStrategies** (BookLover, Save10, Bulk5) dentro de `PricingService`.
5. **Extraer PaymentService** con `PaymentMethod` (Card/Bank/StoreCredit).
6. **Extraer InventoryService** y aislar mutaciones.
7. **Crear CheckoutOrchestrator** y reubicar `checkout()` allí.
8. Cambia import en tests de `from src.checkout_dirty import checkout` a
   `from src.checkout.clean import checkout` (o similar), sin tocar los tests.

> Mantén el contrato de entrada/salida; si necesitas cambiar algo, añade adaptadores.

---

## Sugerencias de diseño (esqueleto)

```python
# src/checkout/domain.py
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Protocol

@dataclass
class LineItem:
    sku: str
    category: str
    qty: int
    unit_price: Decimal

@dataclass
class PricedLine:
    sku: str
    category: str
    qty: int
    unit_price_final: Decimal
    line_subtotal: Decimal
    tax_line: Decimal

@dataclass
class CheckoutResult:
    lines: List[PricedLine]
    subtotal_after_discounts: Decimal
    shipping_cost: Decimal
    tax_total: Decimal
    payment_fee: Decimal
    total: Decimal
    hold_days: int
    free_shipping: bool
