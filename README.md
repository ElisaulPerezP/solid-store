# SOLID Store — Ejercicio de práctica

Este ejercicio simula el **checkout** de una tienda en línea con reglas de negocio realistas. El objetivo es:
1) Entender y modelar correctamente las reglas de negocio.
2) Usar tests para validar la solución y permitir refactors seguros.
3) Partir de una **solución sucia** (que pasa tests) y refactorizar hacia una solución SOLID.

## Reglas del negocio (resumen operativo)

**Catálogos y categorías**
- `BOOK` (libros): impuesto 4%.
- `STATIONERY` (papelería): impuesto 19%.
- `DIGITAL` (digital): impuesto 0% y stock ilimitado.

**Productos de ejemplo**
- BK1 (BOOK): $30.00, 0.5 kg, stock 10
- ST1 (STATIONERY - Notebook A5): $5.00, 0.2 kg, stock 100
- ST2 (STATIONERY - Pen Blue): $2.00, 0.05 kg, stock 50
- DG1 (DIGITAL - Ebook): $15.00, 0 kg, stock ilimitado

**Cupones**
- `SAVE10`: 10% sobre **no digitales** (libros + papelería).
- `BULK5`: 5% si la **cantidad total** de ítems (sumada) ≥ 10. Aplica a todo el carro (incluye digitales).
- `BOOKLOVER`: 15% **solo** a libros.
- Los cupones **se aplican en este orden**: (1) cupones por categoría, (2) `SAVE10`, (3) `BULK5`. Los descuentos son **secuenciales** (compuestos), por línea.

**Envíos**
- `standard`: $5.00 hasta 2.0 kg; +$2.00 por cada **kg iniciado** por encima.
- `express`:  $10.00 hasta 2.0 kg; +$5.00 por cada **kg iniciado** por encima.
- **Envío estándar gratis** si el subtotal **post-descuentos** (antes de impuestos) ≥ $100.00.

**Pagos**
- `card`: recargo 2% sobre **(subtotal con descuentos + impuestos + envío)**.
- `bank_transfer`: sin recargo, pero el pedido queda en **hold 2 días hábiles**.
- `store_credit`: sin recargo; requiere crédito suficiente o **falla**.

**Inventario**
- Se descuenta stock de todo excepto `DIGITAL`.
- Si falta stock, el checkout **falla**.

**Redondeos**
- Impuestos calculados por línea después de descuentos, redondeo **half-up a 2 decimales**.
- Totales a 2 decimales.

## Estructuras esperadas en la llamada

- `order`:
```python
{
  "lines": [{"sku": "BK1", "qty": 1}, ...],
  "shipping": {"method": "standard" | "express"},
  "coupons": ["SAVE10", "BOOKLOVER", "BULK5"],
  "payment": {"method": "card" | "bank_transfer" | "store_credit"}
}
