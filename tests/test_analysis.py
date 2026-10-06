"""
Unit-тесты для cafe_analysis.py (версия 2.0).

Проверяют:
  - структуру summaries (по товарам);
  - суммарные метрики (прибыль, денежный поток, стоимость остатков);
  - поток гостей и разложение по факторам;
  - сезонность (коэффициенты, прогноз);
  - будни/выходные;
  - вердикт (score и текст);
  - предупреждения о данных.
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from cafe_analysis import Analysis
from cafe_model import (
    DailyData,
    DailyRow,
    Period,
    Product,
    SeasonRecord,
)


# ============================================================
#  ФИКСТУРЫ
# ============================================================
@pytest.fixture
def products():
    """Два товара: чипсы (растёт) и кофе (растёт)."""
    return [
        Product(
            name="Чипсы", category="готовый",
            purchase_price_1=45, purchase_price_2=55,
            sale_price_1=90, sale_price_2=110,
            qty_1=120, qty_2=100,
            purchase_qty_1=200, purchase_qty_2=150,
            stock_start_1=30, stock_start_2=110,
        ),
        Product(
            name="Кофе", category="напиток",
            purchase_price_1=25, purchase_price_2=32,
            sale_price_1=100, sale_price_2=130,
            qty_1=200, qty_2=180,
            purchase_qty_1=220, purchase_qty_2=200,
            stock_start_1=50, stock_start_2=70,
        ),
    ]


@pytest.fixture
def periods():
    p1 = Period("Январь", date(2026, 1, 1), date(2026, 1, 31),
                "зима", 30000, guests=500)
    p2 = Period("Февраль", date(2026, 2, 1), date(2026, 2, 28),
                "зима", 32000, guests=450)
    return [p1, p2]


@pytest.fixture
def daily():
    """6 дней в январе: будни и выходные, поток и продажи."""
    rows = [
        DailyRow(date(2026, 1, 1), 100, {"Чипсы": 30, "Кофе": 40}),   # чт
        DailyRow(date(2026, 1, 2), 110, {"Чипсы": 35, "Кофе": 50}),   # пт
        DailyRow(date(2026, 1, 3), 340, {"Чипсы": 110, "Кофе": 180}), # сб
        DailyRow(date(2026, 1, 4), 320, {"Чипсы": 100, "Кофе": 170}), # вс
        DailyRow(date(2026, 1, 5), 100, {"Чипсы": 30, "Кофе": 40}),   # пн
        DailyRow(date(2026, 1, 6), 120, {"Чипсы": 40, "Кофе": 50}),   # вт
    ]
    return DailyData(rows)


@pytest.fixture
def season_records():
    """История по 2 сезонам для чипсов и кофе."""
    return [
        SeasonRecord("зима", "Чипсы", 95, 420),
        SeasonRecord("лето", "Чипсы", 60, 310),
        SeasonRecord("зима", "Кофе", 140, 420),
        SeasonRecord("лето", "Кофе", 70, 310),
    ]


@pytest.fixture
def analysis(products, periods, daily, season_records):
    return Analysis(products, periods, daily, season_records)


# ============================================================
#  СВОДКА И СУММЫ
# ============================================================
def test_summaries_count(analysis):
    assert len(analysis.summaries) == 2


def test_summaries_first_chip(analysis):
    s = analysis.summaries[0]
    assert s.name == "Чипсы"
    # прибыль 1: (90−45)*120 = 5400
    assert s.profit_1 == 5400
    # прибыль 2: (110−55)*100 = 5500
    assert s.profit_2 == 5500


def test_total_profit(analysis):
    # чипсы: 5400, кофе: (100−25)*200 = 15000 → 20400
    assert analysis.total_profit(1) == 5400 + 15000
    # чипсы: 5500, кофе: (130−32)*180 = 17640 → 23140
    assert analysis.total_profit(2) == 5500 + 17640


def test_total_profit_delta(analysis):
    # 23140 − 20400 = 2740
    assert analysis.total_profit_delta() == 2740


def test_total_profit_delta_pct(analysis):
    # 2740 / 20400 * 100 ≈ 13.43%
    assert analysis.total_profit_delta_pct() == pytest.approx(13.43, rel=0.01)


def test_total_revenue(analysis):
    # чипсы 10800, кофе 20000 → 30800
    assert analysis.total_revenue(1) == 10800 + 20000


def test_total_cash_flow(analysis):
    # чипсы: 10800 − 45*200 = 1800
    # кофе:  20000 − 25*220 = 14500
    # итого 16300
    assert analysis.total_cash_flow(1) == 1800 + 14500


def test_total_stock_value(analysis):
    # чипсы: 45 * (30+200−120) = 45*110 = 4950
    # кофе:  25 * (50+220−200) = 25*70  = 1750
    assert analysis.total_stock_value(1) == 4950 + 1750


# ============================================================
#  ПОТОК ГОСТЕЙ
# ============================================================
def test_flow_summary_count(analysis):
    fs = analysis.flow_summary()
    assert len(fs) == 2


def test_flow_conversion_chip(analysis):
    fs = analysis.flow_summary()
    chip = next(r for r in fs if r["Товар"] == "Чипсы")
    # конв 1: 120/500 = 0.24
    assert chip["Конв_1"] == pytest.approx(0.24, rel=1e-6)
    # конв 2: 100/450 ≈ 0.2222
    assert chip["Конв_2"] == pytest.approx(100 / 450, rel=1e-6)


def test_flow_decomposition_sum(analysis):
    """Эффект потока + эффект конверсии = ΔПродано."""
    for r in analysis.flow_summary():
        total = r["Эффект_потока"] + r["Эффект_конверсии"]
        assert total == pytest.approx(r["ΔПродано"], abs=1e-6)


def test_guests_change_pct(analysis):
    # (450 − 500) / 500 * 100 = −10%
    assert analysis.guests_change_pct() == pytest.approx(-10.0)


# ============================================================
#  СЕЗОННОСТЬ
# ============================================================
def test_has_season_history(analysis):
    assert analysis.has_season_history() is True


def test_season_coefficients_for_chip(analysis):
    coef = analysis.season_coefficients()
    # чипсы: среднее (95+60)/2 = 77.5
    # зима: 95 / 77.5 ≈ 1.2258
    assert coef["Чипсы"]["зима"] == pytest.approx(95 / 77.5, rel=1e-3)
    assert coef["Чипсы"]["лето"] == pytest.approx(60 / 77.5, rel=1e-3)


def test_season_forecast(analysis):
    forecasts = analysis.season_forecast_per_product()
    assert len(forecasts) == 2
    # у всех есть ключи
    for f in forecasts:
        assert "Товар" in f
        assert "Прогноз_в_день" in f
        assert "Прогноз_за_период" in f


# ============================================================
#  БУДНИ / ВЫХОДНЫЕ
# ============================================================
def test_has_daily_data(analysis):
    assert analysis.has_daily_data() is True


def test_weekday_weekend_guests(analysis):
    s = analysis.weekday_weekend_for_period(1)
    # гости будни: (100+110+100+120)/4 = 107.5
    assert s["guests"]["будни"] == pytest.approx(107.5, rel=1e-3)
    # гости выходные: (340+320)/2 = 330
    assert s["guests"]["выходные"] == pytest.approx(330, rel=1e-3)


def test_weekday_weekend_product(analysis):
    s = analysis.weekday_weekend_for_period(1)
    chip = s["products"]["Чипсы"]
    # будни: (30+35+30+40)/4 = 33.75
    assert chip["будни"] == pytest.approx(33.75, rel=1e-3)
    # выходные: (110+100)/2 = 105
    assert chip["выходные"] == pytest.approx(105.0, rel=1e-3)


def test_weekday_by_day_of_week(analysis):
    d = analysis.weekday_by_day_of_week(1)
    # гости по дням: чт=100, пт=110, сб=340, вс=320, пн=100, вт=120
    assert d["сб"] == 340
    assert d["вс"] == 320
    assert d["чт"] == 100


# ============================================================
#  ВЕРДИКТ
# ============================================================
def test_verdict_present(analysis):
    assert analysis.verdict is not None
    assert 0 <= analysis.verdict.score <= 5
    assert analysis.verdict.total == 5


def test_verdict_checks_keys(analysis):
    """Проверяем, что в вердикте есть все 5 критериев."""
    keys = analysis.verdict.checks.keys()
    assert "Сохранение наценки" in keys
    assert "Прибыль с единицы" in keys
    assert "Общая прибыль" in keys
    assert "Рост цены vs закупка" in keys
    assert "Падение спроса" in keys


def test_verdict_all_ok(analysis):
    """На наших данных все 5 критериев должны пройти."""
    assert analysis.verdict.score == 5
    assert analysis.verdict.text == "ПОВЫШЕНИЕ ОБОСНОВАНО"


# ============================================================
#  ПРЕДУПРЕЖДЕНИЯ
# ============================================================
def test_no_warnings(analysis):
    """На согласованных данных предупреждений быть не должно."""
    assert analysis.data_warnings() == []


def test_warning_negative_stock(periods, daily, season_records):
    """Если продали больше, чем было — предупреждение."""
    bad = Product(
        name="Плохой", category="готовый",
        purchase_price_1=10, purchase_price_2=12,
        sale_price_1=30, sale_price_2=35,
        qty_1=100, qty_2=100,
        purchase_qty_1=10, purchase_qty_2=10,
        stock_start_1=0, stock_start_2=0,
    )
    a = Analysis([bad], periods, daily, season_records)
    warnings = a.data_warnings()
    assert any("отрицательный остаток" in w for w in warnings)


def test_warning_stock_mismatch(periods, daily, season_records):
    """Остаток конца 1 ≠ начало 2 → предупреждение."""
    bad = Product(
        name="Разрыв", category="готовый",
        purchase_price_1=10, purchase_price_2=12,
        sale_price_1=30, sale_price_2=35,
        qty_1=50, qty_2=50,
        purchase_qty_1=100, purchase_qty_2=100,
        stock_start_1=0, stock_start_2=999,
    )
    a = Analysis([bad], periods, daily, season_records)
    warnings = a.data_warnings()
    assert any("≠" in w for w in warnings)

# ============================================================
#  ТОЧКА БЕЗУБЫТОЧНОСТИ
# ============================================================
def test_breakeven_simple_count(analysis):
    """Возвращает по одной строке на каждый товар."""
    be = analysis.breakeven_simple(2)
    assert len(be) == len(analysis.products)


def test_breakeven_simple_formula(analysis):
    """ТБ = Пост.издержки / Прибыль с единицы."""
    be = analysis.breakeven_simple(2)
    chip = next(r for r in be if r["Товар"] == "Чипсы")
    # Пост.издержки 2 периода = 32000; Прибыль/шт = 110 − 55 = 55
    assert chip["Прибыль_шт"] == 55
    assert chip["ТБ_шт"] == pytest.approx(32000 / 55, rel=1e-3)


def test_breakeven_simple_stock(analysis):
    """Запас = Продано − ТБ."""
    be = analysis.breakeven_simple(2)
    chip = next(r for r in be if r["Товар"] == "Чипсы")
    expected_stock = 100 - 32000 / 55
    assert chip["Запас_шт"] == pytest.approx(expected_stock, rel=1e-3)


def test_breakeven_simple_period_1(analysis):
    """Для 1 периода использует издержки 1 периода (30000)."""
    be = analysis.breakeven_simple(1)
    chip = next(r for r in be if r["Товар"] == "Чипсы")
    # Прибыль/шт = 90 − 45 = 45; ТБ = 30000 / 45 ≈ 666.7
    assert chip["ТБ_шт"] == pytest.approx(30000 / 45, rel=1e-3)


def test_breakeven_simple_zero_margin(analysis):
    """Если прибыль с единицы ≤ 0 — ТБ недостижимо."""
    from cafe_model import DailyData, Product
    bad = Product("Убыточный", "готовый", 100, 120, 90, 110, 50, 50,
                  50, 50, 0, 0)
    a = Analysis([bad], analysis.periods, DailyData([]), [])
    be = a.breakeven_simple(2)
    assert be[0]["ТБ_шт"] == "недостижимо"


def test_breakeven_cafe_total_fields(analysis):
    """Общая сводка содержит нужные поля."""
    total = analysis.breakeven_cafe_total(2)
    assert "Постоянные_издержки" in total
    assert "Прибыль" in total
    assert "Покрытие_%" in total
    assert total["Постоянные_издержки"] == 32000


def test_breakeven_cafe_total_not_covered(analysis):
    """На тестовых данных прибыль НЕ покрывает издержки (мало товаров)."""
    total = analysis.breakeven_cafe_total(2)
    # Постоянные издержки 32000, прибыль 23140 → покрытие ~72%
    assert total["Покрывает"] == "нет"
    assert 60 < total["Покрытие_%"] < 90


def test_breakeven_cafe_total_coverage_math(analysis):
    """Покрытие = Прибыль / Издержки × 100."""
    total = analysis.breakeven_cafe_total(2)
    expected = 23140 / 32000 * 100
    assert total["Покрытие_%"] == pytest.approx(expected, rel=1e-3)
