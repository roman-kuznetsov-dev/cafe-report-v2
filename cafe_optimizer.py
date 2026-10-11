"""
Оптимизатор цены для товаров кафе.

Задача: для каждого товара найти цену продажи, при которой
суммарная прибыль максимальна — с учётом эластичности спроса.

Эластичность E: на сколько % изменится спрос при изменении цены на 1%.
    E = 0.8   → цена +10% → спрос −8%
    E = 1.0   → цена +10% → спрос −10%
    E = 1.5   → цена +10% → спрос −15%

Формулы:
    Новая цена        = Текущая × (1 + Δ% / 100)
    Новый спрос       = Текущий × (1 − E × Δ% / 100)
    Новая прибыль     = (Новая цена − Закупка) × Новый спрос
"""

from dataclasses import dataclass

from cafe_model import ELASTICITY, Product


# ============================================================
#  РЕЗУЛЬТАТ ОПТИМИЗАЦИИ ПО ОДНОМУ ТОВАРУ
# ============================================================
@dataclass
class OptimalPrice:
    """Результат оптимизации цены для одного товара."""
    product: str
    base_price: float          # текущая цена
    base_qty: int              # текущий спрос
    base_profit: float         # текущая прибыль
    purchase_price: float      # закупка (не меняется)
    optimal_price: float       # оптимальная цена
    optimal_delta_pct: float   # изменение цены в %
    optimal_qty: int           # прогноз спроса при оптимальной цене
    optimal_profit: float      # прибыль при оптимальной цене

    def profit_delta(self) -> float:
        """Рост прибыли в рублях."""
        return self.optimal_profit - self.base_profit

    def profit_delta_pct(self) -> float:
        """Рост прибыли в %."""
        if self.base_profit == 0:
            return 0
        return self.profit_delta() / self.base_profit * 100


# ============================================================
#  ОПТИМИЗАЦИЯ ОДНОГО ТОВАРА
# ============================================================
def optimize_product(product: Product,
                     period: int = 2,
                     delta_min: float = -20,
                     delta_max: float = 40,
                     step: float = 1.0,
                     elasticity: float | None = None) -> OptimalPrice:
    """
    Перебирает изменения цены для одного товара,
    возвращает оптимальную точку.

    product    — товар.
    period     — 1 или 2 (берём базовую цену и спрос за этот период).
    delta_min  — минимальное изменение цены, % (например, −20).
    delta_max  — максимальное изменение, % (например, +40).
    step       — шаг перебора, % (например, 1).
    elasticity — эластичность; если None — берётся ELASTICITY из cafe_model.
    """
    if elasticity is None:
        elasticity = ELASTICITY

    base_price = product.sale_price_1 if period == 1 else product.sale_price_2
    base_qty = product.qty_1 if period == 1 else product.qty_2
    purchase = (product.purchase_price_1 if period == 1
                else product.purchase_price_2)
    base_profit = (base_price - purchase) * base_qty

    best_profit = base_profit
    best_price = base_price
    best_qty = base_qty
    best_delta = 0.0

    # Перебор с шагом step
    current_delta = delta_min
    while current_delta <= delta_max + 1e-9:
        new_price = base_price * (1 + current_delta / 100)
        new_qty = base_qty * (1 - elasticity * current_delta / 100)
        new_qty = max(0, new_qty)

        new_profit = (new_price - purchase) * new_qty

        if new_profit > best_profit:
            best_profit = new_profit
            best_price = new_price
            best_qty = int(round(new_qty))
            best_delta = current_delta

        current_delta += step

    return OptimalPrice(
        product=product.name,
        base_price=round(base_price, 2),
        base_qty=base_qty,
        base_profit=round(base_profit, 2),
        purchase_price=round(purchase, 2),
        optimal_price=round(best_price, 2),
        optimal_delta_pct=round(best_delta, 1),
        optimal_qty=best_qty,
        optimal_profit=round(best_profit, 2),
    )


# ============================================================
#  ОПТИМИЗАЦИЯ ПО ВСЕМ ТОВАРАМ
# ============================================================
def optimize_all(products: list[Product],
                 period: int = 2,
                 delta_min: float = -20,
                 delta_max: float = 40,
                 step: float = 1.0,
                 elasticity: float | None = None) -> list[OptimalPrice]:
    """Оптимизирует цены для всех товаров."""
    return [
        optimize_product(p, period, delta_min, delta_max, step, elasticity)
        for p in products
    ]


def total_optimal(products: list[Product],
                  period: int = 2,
                  **kwargs) -> dict:
    """
    Суммарная оптимизация: сколько прибыли кафе может получить,
    если оптимизировать все товары.
    """
    results = optimize_all(products, period, **kwargs)

    base_total = sum(r.base_profit for r in results)
    optimal_total = sum(r.optimal_profit for r in results)
    delta = optimal_total - base_total
    delta_pct = (delta / base_total * 100) if base_total else 0

    return {
        "результаты": results,
        "базовая_прибыль": round(base_total, 2),
        "оптимальная_прибыль": round(optimal_total, 2),
        "Δ_прибыль": round(delta, 2),
        "Δ_прибыль_%": round(delta_pct, 1),
    }


# ============================================================
#  ПРОГНОЗ ПРИ КОНКРЕТНОЙ ЦЕНЕ (для вкладки «Что-если»)
# ============================================================
def forecast_at_price(product: Product,
                      new_price: float,
                      period: int = 2,
                      elasticity: float | None = None) -> dict:
    """
    Прогноз для конкретной новой цены товара.

    Возвращает: новый спрос, новая прибыль, изменение.
    """
    if elasticity is None:
        elasticity = ELASTICITY

    base_price = product.sale_price_1 if period == 1 else product.sale_price_2
    base_qty = product.qty_1 if period == 1 else product.qty_2
    purchase = (product.purchase_price_1 if period == 1
                else product.purchase_price_2)

    delta_pct = ((new_price - base_price) / base_price * 100
                 if base_price else 0)

    new_qty = base_qty * (1 - elasticity * delta_pct / 100)
    new_qty = max(0, new_qty)

    base_profit = (base_price - purchase) * base_qty
    new_profit = (new_price - purchase) * new_qty

    return {
        "Товар": product.name,
        "Базовая_цена": round(base_price, 2),
        "Новая_цена": round(new_price, 2),
        "Δ_цены_%": round(delta_pct, 1),
        "Базовая_продажа": base_qty,
        "Новая_продажа": int(round(new_qty)),
        "Базовая_прибыль": round(base_profit, 2),
        "Новая_прибыль": round(new_profit, 2),
        "Δ_прибыль": round(new_profit - base_profit, 2),
        "Δ_прибыль_%": round((new_profit - base_profit) / base_profit * 100, 1)
                       if base_profit else 0,
    }


def forecast_all_at_prices(products: list[Product],
                           new_prices: dict[str, float],
                           period: int = 2,
                           elasticity: float | None = None) -> dict:
    """
    Прогноз для всех товаров при заданных новых ценах.

    new_prices: {имя_товара: новая_цена}
    Если для товара цены нет — берётся текущая.
    """
    rows = []
    for p in products:
        base_price = (p.sale_price_1 if period == 1 else p.sale_price_2)
        price = new_prices.get(p.name, base_price)
        rows.append(forecast_at_price(p, price, period, elasticity))

    base_total = sum(r["Базовая_прибыль"] for r in rows)
    new_total = sum(r["Новая_прибыль"] for r in rows)

    return {
        "результаты": rows,
        "базовая_прибыль": round(base_total, 2),
        "новая_прибыль": round(new_total, 2),
        "Δ_прибыль": round(new_total - base_total, 2),
        "Δ_прибыль_%": round((new_total - base_total) / base_total * 100, 1)
                       if base_total else 0,
    }
