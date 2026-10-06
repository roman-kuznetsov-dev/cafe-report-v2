"""
Unit-тесты для cafe_exporter.py (версия 2.0).

Проверяют:
  - создание Excel-файла;
  - наличие всех 8 листов;
  - базовую структуру (заголовки, количество строк).
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import pytest

from cafe_model import (
    Product, Period, DailyRow, DailyData, SeasonRecord,
)
from cafe_analysis import Analysis
from cafe_exporter import export_to_excel


# ============================================================
#  ФИКСТУРЫ
# ============================================================
@pytest.fixture
def analysis():
    products = [
        Product("Чипсы", "готовый", 45, 55, 90, 110, 120, 100,
                200, 150, 30, 110),
        Product("Кофе", "напиток", 25, 32, 100, 130, 200, 180,
                220, 200, 50, 70),
    ]
    p1 = Period("Январь", date(2026, 1, 1), date(2026, 1, 31),
                "зима", 30000, guests=500)
    p2 = Period("Февраль", date(2026, 2, 1), date(2026, 2, 28),
                "зима", 32000, guests=450)
    rows = [
        DailyRow(date(2026, 1, 1), 100, {"Чипсы": 30, "Кофе": 40}),
        DailyRow(date(2026, 1, 3), 340, {"Чипсы": 110, "Кофе": 180}),
        DailyRow(date(2026, 1, 4), 320, {"Чипсы": 100, "Кофе": 170}),
    ]
    daily = DailyData(rows)
    season = [
        SeasonRecord("зима", "Чипсы", 95, 420),
        SeasonRecord("лето", "Чипсы", 60, 310),
    ]
    return Analysis(products, [p1, p2], daily, season)


# ============================================================
#  ТЕСТЫ
# ============================================================
def test_export_creates_file(analysis, tmp_path):
    out = str(tmp_path / "report.xlsx")
    export_to_excel(analysis, out)
    assert os.path.exists(out)


def test_export_has_all_sheets(analysis, tmp_path):
    out = str(tmp_path / "report.xlsx")
    export_to_excel(analysis, out)
    xl = pd.ExcelFile(out)
    expected = {
        "Сводка", "Обоснованность", "Закупки и остатки",
        "Денежный поток", "Поток гостей", "Сезонность",
        "Будни и выходные", "Категории",
    }
    assert expected.issubset(set(xl.sheet_names))


def test_summary_sheet_columns(analysis, tmp_path):
    out = str(tmp_path / "report.xlsx")
    export_to_excel(analysis, out)
    df = pd.read_excel(out, sheet_name="Сводка")
    assert "Товар" in df.columns
    assert "Прибыль_1" in df.columns
    assert "Прибыль_2" in df.columns
    assert len(df) == 2


def test_justification_sheet(analysis, tmp_path):
    out = str(tmp_path / "report.xlsx")
    export_to_excel(analysis, out)
    df = pd.read_excel(out, sheet_name="Обоснованность")
    assert "Критерий" in df.columns
    assert "Результат" in df.columns
    # 4 критерия × 2 товара = 8 + итог общей прибыли + пропуск + вердикт
    assert len(df) >= 8


def test_stock_sheet(analysis, tmp_path):
    out = str(tmp_path / "report.xlsx")
    export_to_excel(analysis, out)
    df = pd.read_excel(out, sheet_name="Закупки и остатки")
    assert "Остаток_нач_1" in df.columns
    assert "Остаток_кон_2" in df.columns
    # 2 товара + 1 строка ИТОГО = 3
    assert len(df) == 3


def test_cashflow_sheet(analysis, tmp_path):
    out = str(tmp_path / "report.xlsx")
    export_to_excel(analysis, out)
    df = pd.read_excel(out, sheet_name="Денежный поток")
    assert "Управленческая_прибыль_1" in df.columns
    assert "Денежный_поток_1" in df.columns


def test_flow_sheet(analysis, tmp_path):
    out = str(tmp_path / "report.xlsx")
    export_to_excel(analysis, out)
    df = pd.read_excel(out, sheet_name="Поток гостей")
    assert "Конверсия_1" in df.columns
    assert "Влияние_потока" in df.columns
    assert len(df) == 2


def test_seasonality_sheet(analysis, tmp_path):
    out = str(tmp_path / "report.xlsx")
    export_to_excel(analysis, out)
    df = pd.read_excel(out, sheet_name="Сезонность")
    # в шапке будут столбцы зима/весна/лето/осень
    assert any(s in df.columns for s in ["зима", "весна", "лето", "осень"])


def test_weekday_sheet(analysis, tmp_path):
    out = str(tmp_path / "report.xlsx")
    export_to_excel(analysis, out)
    df = pd.read_excel(out, sheet_name="Будни и выходные")
    assert "Будни" in df.columns
    assert "Выходные" in df.columns


def test_categories_sheet(analysis, tmp_path):
    out = str(tmp_path / "report.xlsx")
    export_to_excel(analysis, out)
    df = pd.read_excel(out, sheet_name="Категории")
    assert "Категория" in df.columns
    # 2 категории: готовый и напиток
    assert len(df) == 2