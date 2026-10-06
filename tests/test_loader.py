"""
Unit-тесты для cafe_loader.py (версия 2.0).

Проверяют загрузку данных из cafe_data.xlsx:
  - чтение листа «Товары»;
  - чтение листа «Периоды»;
  - чтение ежедневных данных;
  - чтение сезонной истории;
  - корректные ошибки при отсутствии файла.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import pytest

from cafe_loader import (
    load_all, load_products, load_periods,
    load_daily, load_season_history,
)


# ============================================================
#  ФИКСТУРА: минимальный валидный cafe_data.xlsx
# ============================================================
@pytest.fixture
def sample_xlsx(tmp_path):
    """Создаёт временный Excel с 4 листами для тестов."""
    path = str(tmp_path / "cafe_data.xlsx")

    df_products = pd.DataFrame([
        {"Товар": "Чипсы", "Категория": "готовый",
         "Закуп_1": 45, "Закуп_2": 55, "Цена_1": 90, "Цена_2": 110,
         "Кол_1": 120, "Кол_2": 100,
         "Закуп_кол_1": 200, "Закуп_кол_2": 150,
         "Остаток_нач_1": 30, "Остаток_нач_2": 110},
        {"Товар": "Кофе", "Категория": "напиток",
         "Закуп_1": 25, "Закуп_2": 32, "Цена_1": 100, "Цена_2": 130,
         "Кол_1": 200, "Кол_2": 180,
         "Закуп_кол_1": 220, "Закуп_кол_2": 200,
         "Остаток_нач_1": 50, "Остаток_нач_2": 70},
    ])

    df_periods = pd.DataFrame([
        {"Поле": "Название", "Период 1": "Январь", "Период 2": "Февраль"},
        {"Поле": "Дата начала", "Период 1": "2026-01-01",
         "Период 2": "2026-02-01"},
        {"Поле": "Дата конца", "Период 1": "2026-01-31",
         "Период 2": "2026-02-28"},
        {"Поле": "Сезон", "Период 1": "зима", "Период 2": "зима"},
        {"Поле": "Гостей", "Период 1": 500, "Период 2": 450},
        {"Поле": "Постоянные издержки, ₽",
         "Период 1": 30000, "Период 2": 32000},
    ])

    df_daily = pd.DataFrame([
        {"Дата": "2026-01-01", "Гостей": 100, "Чипсы": 30, "Кофе": 40},
        {"Дата": "2026-01-02", "Гостей": 120, "Чипсы": 35, "Кофе": 50},
        {"Дата": "2026-01-03", "Гостей": 340, "Чипсы": 110, "Кофе": 180},
    ])

    df_season = pd.DataFrame([
        {"Сезон": "зима", "Товар": "Чипсы",
         "Среднее_продаж_в_день": 95, "Средний_поток_в_день": 420},
        {"Сезон": "лето", "Товар": "Чипсы",
         "Среднее_продаж_в_день": 60, "Средний_поток_в_день": 310},
    ])

    with pd.ExcelWriter(path, engine="xlsxwriter") as w:
        df_products.to_excel(w, sheet_name="Товары", index=False)
        df_periods.to_excel(w, sheet_name="Периоды", index=False)
        df_daily.to_excel(w, sheet_name="Ежедневные данные", index=False)
        df_season.to_excel(w, sheet_name="Сезонная история", index=False)

    return path


# ============================================================
#  ТЕСТЫ
# ============================================================
def test_load_products(sample_xlsx):
    products = load_products(sample_xlsx)
    assert len(products) == 2
    chip = products[0]
    assert chip.name == "Чипсы"
    assert chip.purchase_qty_1 == 200
    assert chip.stock_start_1 == 30


def test_load_products_returns_second(sample_xlsx):
    products = load_products(sample_xlsx)
    coffee = products[1]
    assert coffee.name == "Кофе"
    assert coffee.purchase_price_2 == 32


def test_load_periods(sample_xlsx):
    p1, p2 = load_periods(sample_xlsx)
    assert p1.name == "Январь"
    assert p1.season == "зима"
    assert p1.guests == 500
    assert p2.guests == 450
    assert p1.fixed_costs == 30000


def test_load_daily(sample_xlsx):
    daily = load_daily(sample_xlsx, ["Чипсы", "Кофе"])
    assert len(daily) == 3
    assert daily.guests_total() == 560
    assert daily.sales_total("Чипсы") == 30 + 35 + 110
    assert daily.sales_total("Кофе") == 40 + 50 + 180


def test_load_season(sample_xlsx):
    recs = load_season_history(sample_xlsx)
    assert len(recs) == 2
    assert recs[0].season == "зима"
    assert recs[0].product == "Чипсы"


def test_load_all(sample_xlsx):
    data = load_all(sample_xlsx)
    assert len(data.products) == 2
    assert len(data.periods) == 2
    assert len(data.daily) == 3
    assert len(data.season_records) == 2


def test_load_missing_file():
    with pytest.raises(FileNotFoundError):
        load_all("несуществующий_файл.xlsx")