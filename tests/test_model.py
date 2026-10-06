"""
Unit-тесты для cafe_model.py (версия 2.0).

Запуск:  pytest
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from cafe_model import (
    DailyData,
    DailyRow,
    Flow,
    Period,
    Product,
    Seasonality,
    SeasonRecord,
    WeekdayWeekend,
)


# ============================================================
#  ФИКСТУРЫ
# ============================================================
@pytest.fixture
def chip():
    """Чипсы: закупка 45→55, цена 90→110, продано 120→100,
    закуплено 200→150, остаток нач 30→110."""
    return Product(
        name="Чипсы", category="готовый",
        purchase_price_1=45, purchase_price_2=55,
        sale_price_1=90, sale_price_2=110,
        qty_1=120, qty_2=100,
        purchase_qty_1=200, purchase_qty_2=150,
        stock_start_1=30, stock_start_2=110,
    )


@pytest.fixture
def periods():
    p1 = Period("Январь", date(2026, 1, 1), date(2026, 1, 31),
                "зима", 30000, guests=500)
    p2 = Period("Февраль", date(2026, 2, 1), date(2026, 2, 28),
                "зима", 32000, guests=450)
    return [p1, p2]


@pytest.fixture
def daily():
    rows = [
        DailyRow(date(2026, 1, 1), 100, {"Чипсы": 30}),  # чт (будний)
        DailyRow(date(2026, 1, 2), 110, {"Чипсы": 35}),  # пт
        DailyRow(date(2026, 1, 3), 340, {"Чипсы": 110}), # сб
        DailyRow(date(2026, 1, 4), 320, {"Чипсы": 100}), # вс
        DailyRow(date(2026, 1, 5), 100, {"Чипсы": 30}),  # пн
        DailyRow(date(2026, 1, 6), 120, {"Чипсы": 40}),  # вт
    ]
    return DailyData(rows)


# ============================================================
#  ПРОСТЫЕ ПРОВЕРКИ Product
# ============================================================
def test_revenue(chip):
    assert chip.revenue(1) == 90 * 120
    assert chip.revenue(2) == 110 * 100


def test_cost_of_goods_sold(chip):
    assert chip.cost_of_goods_sold(1) == 45 * 120
    assert chip.cost_of_goods_sold(2) == 55 * 100


def test_purchase_expense(chip):
    assert chip.purchase_expense(1) == 45 * 200
    assert chip.purchase_expense(2) == 55 * 150


def test_profit(chip):
    assert chip.profit(1) == 10800 - 5400
    assert chip.profit(2) == 11000 - 5500


def test_cash_flow(chip):
    assert chip.cash_flow(1) == 10800 - 9000    # 1800
    assert chip.cash_flow(2) == 11000 - 8250    # 2750


def test_stock_end(chip):
    assert chip.stock_end(1) == 30 + 200 - 120   # 110
    assert chip.stock_end(2) == 110 + 150 - 100  # 160


def test_stock_value(chip):
    assert chip.stock_value(1) == 45 * 110       # 4950
    assert chip.stock_value(2) == 55 * 160       # 8800


def test_stock_balance_no_errors(chip):
    assert chip.stock_error(1) is None
    assert chip.stock_error(2) is None
    assert chip.stock_mismatch() is None


def test_stock_error_negative():
    p = Product("Тест", "готовый", 10, 12, 30, 35, 100, 100, 50, 50, 10, 10)
    # 10 + 50 − 100 = −40 — отрицательный остаток
    err = p.stock_error(1)
    assert err is not None
    assert "отрицательный остаток" in err


def test_stock_mismatch():
    p = Product("Тест", "готовый", 10, 12, 30, 35, 50, 50, 100, 100, 0, 999)
    # конец 1 = 0 + 100 − 50 = 50; начало 2 = 999 → несовпадение
    err = p.stock_mismatch()
    assert err is not None
    assert "≠" in err


# ============================================================
#  ПРОВЕРКИ Period
# ============================================================
def test_period_days_count(periods):
    assert periods[0].days_count() == 31
    assert periods[1].days_count() == 28


def test_period_validate_ok(periods):
    for p in periods:
        assert p.validate() is None


def test_period_validate_bad_season():
    p = Period("X", date(2026, 1, 1), date(2026, 1, 31),
               "несуществующий", 1000, guests=0)
    assert p.validate() is not None


# ============================================================
#  ПРОВЕРКИ DailyData
# ============================================================
def test_daily_len(daily):
    assert len(daily) == 6


def test_daily_guests_total(daily):
    assert daily.guests_total() == 100 + 110 + 340 + 320 + 100 + 120


def test_daily_sales_total(daily):
    assert daily.sales_total("Чипсы") == 30 + 35 + 110 + 100 + 30 + 40


def test_daily_weekday_type(daily):
    parts = daily.by_weekday_type()
    assert len(parts["будни"]) == 4       # чт, пт, пн, вт
    assert len(parts["выходные"]) == 2    # сб, вс


def test_daily_by_day_of_week(daily):
    parts = daily.by_day_of_week()
    assert len(parts["сб"]) == 1
    assert len(parts["вс"]) == 1
    assert len(parts["чт"]) == 1


def test_daily_filter_period(daily, periods):
    # все 6 дней внутри января
    filtered = daily.filter_period(periods[0])
    assert len(filtered) == 6
    # февраль — пусто
    filtered2 = daily.filter_period(periods[1])
    assert len(filtered2) == 0


# ============================================================
#  ПРОВЕРКИ Flow
# ============================================================
def test_conversion(chip, periods):
    f = Flow([chip], periods)
    assert f.conversion(chip, 1) == pytest.approx(0.24, rel=1e-3)
    assert f.conversion(chip, 2) == pytest.approx(100 / 450, rel=1e-3)


def test_flow_decompose(chip, periods):
    f = Flow([chip], periods)
    d = f.decompose(chip)
    # эффект потока: (450 − 500) × 0.24 = −12
    assert d["эффект_потока"] == pytest.approx(-12, abs=1e-6)
    # эффект конверсии: 450 × (100/450 − 0.24) = 100 − 108 = −8
    assert d["эффект_конверсии"] == pytest.approx(-8, abs=1e-6)
    # сумма должна дать Δпродаж
    assert d["проверка"] == pytest.approx(-20, abs=1e-6)


# ============================================================
#  ПРОВЕРКИ Seasonality
# ============================================================
def test_seasonality_no_history():
    s = Seasonality([])
    assert s.has_history() is False
    assert s.coefficient("Кофе", "зима") == 0


def test_seasonality_coefficient():
    recs = [
        SeasonRecord("зима", "Кофе", 240, 550),
        SeasonRecord("весна", "Кофе", 200, 470),
        SeasonRecord("лето", "Кофе", 130, 400),
        SeasonRecord("осень", "Кофе", 210, 500),
    ]
    s = Seasonality(recs)
    assert s.has_history() is True
    # среднее (240+200+130+210)/4 = 195
    assert s.average_sales_all_seasons("Кофе") == pytest.approx(195, abs=0.01)
    # зима: 240 / 195 ≈ 1.2308
    assert s.coefficient("Кофе", "зима") == pytest.approx(240 / 195, rel=1e-3)
    # лето: 130 / 195 ≈ 0.6667
    assert s.coefficient("Кофе", "лето") == pytest.approx(130 / 195, rel=1e-3)


def test_seasonality_forecast():
    recs = [SeasonRecord("зима", "Кофе", 240, 550)]
    s = Seasonality(recs)
    # поток 550, конверсия 0.5, коэф = 240/240 = 1 → 550 * 0.5 * 1 = 275
    forecast = s.forecast_sales("Кофе", "зима", conversion=0.5)
    assert forecast == pytest.approx(275, rel=1e-3)


# ============================================================
#  ПРОВЕРКИ WeekdayWeekend
# ============================================================
def test_weekday_weekend_guests(daily):
    w = WeekdayWeekend(daily)
    s = w.summary_guests()
    # будни: (100+110+100+120)/4 = 107.5
    assert s["будни"] == pytest.approx(107.5, rel=1e-3)
    # выходные: (340+320)/2 = 330
    assert s["выходные"] == pytest.approx(330, rel=1e-3)
    # индекс: 330 / 107.5 ≈ 3.07
    assert s["индекс_вых"] == pytest.approx(330 / 107.5, rel=1e-3)


def test_weekday_weekend_product(daily):
    w = WeekdayWeekend(daily)
    s = w.summary_for_product("Чипсы")
    # будни: (30+35+30+40)/4 = 33.75
    assert s["будни"] == pytest.approx(33.75, rel=1e-3)
    # выходные: (110+100)/2 = 105
    assert s["выходные"] == pytest.approx(105, rel=1e-3)


def test_weekday_weekend_by_day(daily):
    w = WeekdayWeekend(daily)
    d = w.by_day_of_week("Чипсы")
    assert d["сб"] == 110
    assert d["вс"] == 100
    assert d["чт"] == 30
