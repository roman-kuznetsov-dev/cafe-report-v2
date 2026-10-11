"""
Unit-тесты для cafe_optimizer.py.

Проверяют:
  - оптимизацию одного товара;
  - поведение при разных эластичностях;
  - суммарную оптимизацию по всем товарам;
  - прогноз для конкретной новой цены;
  - граничные случаи (нулевые продажи, отрицательная прибыль).
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

import cafe_optimizer as opt
from cafe_model import Product


# ============================================================
#  ФИКСТУРЫ
# ============================================================
@pytest.fixture
def simple_product():
    """Обычный товар: закупка 45→55, цена 90→110, продано 120→100."""
    return Product(
        name="Чипсы", category="готовый",
        purchase_price_1=45, purchase_price_2=55,
        sale_price_1=90, sale_price_2=110,
        qty_1=120, qty_2=100,
        purchase_qty_1=200, purchase_qty_2=150,
        stock_start_1=30, stock_start_2=110,
    )


@pytest.fixture
def cheap_product():
    """Товар с большой наценкой: закупка 10, цена 100."""
    return Product(
        name="Кофе", category="напиток",
        purchase_price_1=10, purchase_price_2=10,
        sale_price_1=100, sale_price_2=100,
        qty_1=50, qty_2=50,
        purchase_qty_1=60, purchase_qty_2=60,
        stock_start_1=0, stock_start_2=10,
    )


@pytest.fixture
def products_list(simple_product, cheap_product):
    return [simple_product, cheap_product]


# ============================================================
#  ОПТИМИЗАЦИЯ ОДНОГО ТОВАРА
# ============================================================
def test_optimize_product_returns_object(simple_product):
    """Функция возвращает объект OptimalPrice."""
    r = opt.optimize_product(simple_product)
    assert r.product == "Чипсы"
    assert r.base_price == 110
    assert r.purchase_price == 55


def test_optimize_product_optimal_profit_ge_base(simple_product):
    """Оптимальная прибыль не меньше базовой (по построению)."""
    r = opt.optimize_product(simple_product)
    assert r.optimal_profit >= r.base_profit


def test_optimize_product_elasticity_zero(cheap_product):
    """
    При эластичности 0 спрос не меняется.
    Значит, оптимум — максимальная возможная цена (delta_max).
    """
    r = opt.optimize_product(cheap_product, elasticity=0,
                             delta_min=-20, delta_max=40, step=1)
    assert r.optimal_delta_pct == 40


def test_optimize_product_high_elasticity(cheap_product):
    """
    При высокой эластичности поднимать цену невыгодно.
    Оптимум — отрицательный или нулевой.
    """
    r = opt.optimize_product(cheap_product, elasticity=2.0)
    # При E=2 и цене 100 (закупка 10) — оптимум близок к 0 или отрицательный
    assert r.optimal_delta_pct <= 5


def test_optimize_product_period_1(simple_product):
    """Использование 1 периода: цена 90, продано 120."""
    r = opt.optimize_product(simple_product, period=1)
    assert r.base_price == 90
    assert r.base_qty == 120
    assert r.purchase_price == 45


def test_optimize_product_step_5(simple_product):
    """С шагом 5% оптимум должен быть кратным 5."""
    r = opt.optimize_product(simple_product, step=5)
    assert r.optimal_delta_pct % 5 == 0


def test_optimize_product_profit_delta(simple_product):
    """profit_delta() = optimal_profit − base_profit."""
    r = opt.optimize_product(simple_product)
    assert r.profit_delta() == pytest.approx(
        r.optimal_profit - r.base_profit)


def test_optimize_product_profit_delta_pct(simple_product):
    """profit_delta_pct() — процент роста прибыли."""
    r = opt.optimize_product(simple_product)
    expected = r.profit_delta() / r.base_profit * 100
    assert r.profit_delta_pct() == pytest.approx(expected)


# ============================================================
#  ОПТИМИЗАЦИЯ ПО ВСЕМ ТОВАРАМ
# ============================================================
def test_optimize_all_count(products_list):
    """Возвращает список, длина = количество товаров."""
    results = opt.optimize_all(products_list)
    assert len(results) == 2


def test_total_optimal_keys(products_list):
    """total_optimal возвращает нужные ключи."""
    t = opt.total_optimal(products_list)
    assert "результаты" in t
    assert "базовая_прибыль" in t
    assert "оптимальная_прибыль" in t
    assert "Δ_прибыль" in t
    assert "Δ_прибыль_%" in t


def test_total_optimal_improves(products_list):
    """Оптимальная прибыль >= базовой."""
    t = opt.total_optimal(products_list)
    assert t["оптимальная_прибыль"] >= t["базовая_прибыль"]
    assert t["Δ_прибыль"] >= 0


def test_total_optimal_math(products_list):
    """Δ прибыли = оптимальная − базовая."""
    t = opt.total_optimal(products_list)
    assert t["Δ_прибыль"] == pytest.approx(
        t["оптимальная_прибыль"] - t["базовая_прибыль"])


# ============================================================
#  ПРОГНОЗ ДЛЯ КОНКРЕТНОЙ ЦЕНЫ
# ============================================================
def test_forecast_at_price_same(cheap_product):
    """Прогноз при текущей цене = базовые показатели."""
    r = opt.forecast_at_price(cheap_product, new_price=100)
    assert r["Δ_цены_%"] == 0
    assert r["Δ_прибыль"] == pytest.approx(0)


def test_forecast_at_price_higher(cheap_product):
    """Прогноз при цене выше текущей — цена растёт, спрос падает."""
    r = opt.forecast_at_price(cheap_product, new_price=120)
    assert r["Δ_цены_%"] == pytest.approx(20)
    assert r["Новая_продажа"] < r["Базовая_продажа"]


def test_forecast_at_price_lower(cheap_product):
    """Прогноз при цене ниже текущей — цена падает, спрос растёт."""
    r = opt.forecast_at_price(cheap_product, new_price=80)
    assert r["Δ_цены_%"] == pytest.approx(-20)
    assert r["Новая_продажа"] > r["Базовая_продажа"]


def test_forecast_all_at_prices(products_list):
    """Прогноз для всех товаров возвращает нужные поля."""
    prices = {"Чипсы": 130, "Кофе": 110}
    r = opt.forecast_all_at_prices(products_list, prices)
    assert "результаты" in r
    assert len(r["результаты"]) == 2
    assert "Δ_прибыль" in r


def test_forecast_all_uses_current_when_missing(products_list):
    """Если цена не задана — берётся текущая."""
    prices = {"Чипсы": 130}  # Кофе не указан
    r = opt.forecast_all_at_prices(products_list, prices)
    coffee = next(x for x in r["результаты"] if x["Товар"] == "Кофе")
    assert coffee["Δ_цены_%"] == 0


# ============================================================
#  ГРАНИЧНЫЕ СЛУЧАИ
# ============================================================
def test_optimize_with_zero_quantity():
    """Если продано 0 — оптимизация не падает."""
    p = Product("Пустой", "готовый", 10, 12, 30, 35, 0, 0, 0, 0, 0, 0)
    r = opt.optimize_product(p)
    assert r.base_qty == 0
    assert r.optimal_profit >= 0


def test_optimize_with_zero_purchase():
    """Если закупка 0 — оптимизация не падает."""
    p = Product("Подарок", "готовый", 0, 0, 100, 100, 50, 50,
                50, 50, 0, 0)
    r = opt.optimize_product(p)
    assert r.purchase_price == 0
    assert r.optimal_profit >= 0


def test_forecast_at_price_extreme_low(cheap_product):
    """При очень низкой цене продажи не отрицательные."""
    r = opt.forecast_at_price(cheap_product, new_price=1)
    assert r["Новая_продажа"] >= 0
