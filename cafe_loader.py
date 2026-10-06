"""
Загрузка данных из cafe_data.xlsx (версия 2.0).

Читает 4 листа:
  1. Товары
  2. Периоды
  3. Ежедневные данные
  4. Сезонная история

Возвращает объекты модели: Product, Period, DailyRow, SeasonRecord.

Все ошибки — с номером строки и понятным текстом.
"""

import os
import sys
from datetime import date, datetime
from typing import List, Tuple, Optional

import pandas as pd

from cafe_model import (
    Product, Period, DailyRow, DailyData,
    SeasonRecord, SEASONS,
)
def _detect_warning_row(xlsx_path: str, sheet_name: str) -> int:
    """
    Проверяет, начинается ли лист со строки-предупреждения.
    Если да — возвращает 1 (пропустить первую строку),
    если нет — 0.
    """
    try:
        head = pd.read_excel(xlsx_path, sheet_name=sheet_name,
                             nrows=2, header=None)
    except Exception:
        return 0

    first_cell = str(head.iloc[0, 0]) if len(head) > 0 else ""
    if "⚠" in first_cell or "пример" in first_cell.lower() \
            or "прим" in first_cell.lower():
        return 1
    return 0


# ============================================================
#  ВСПОМОГАТЕЛЬНЫЕ
# ============================================================
def _is_blank(value) -> bool:
    if value is None:
        return True
    try:
        if value != value:    # NaN
            return True
    except Exception:
        pass
    s = str(value).strip()
    return s == "" or s.lower() in ("nan", "none")


def _to_float(value, row_num: int, field: str) -> float:
    if _is_blank(value):
        raise ValueError(
            f"Лист, строка {row_num}, поле «{field}»: пусто. "
            f"Впишите число."
        )
    try:
        return float(str(value).replace(",", ".").replace(" ", ""))
    except Exception:
        raise ValueError(
            f"Лист, строка {row_num}, поле «{field}» = '{value}' "
            f"не является числом."
        )


def _to_int(value, row_num: int, field: str) -> int:
    if _is_blank(value):
        raise ValueError(
            f"Лист, строка {row_num}, поле «{field}»: пусто. "
            f"Впишите целое число."
        )
    try:
        return int(float(str(value).replace(",", ".").replace(" ", "")))
    except Exception:
        raise ValueError(
            f"Лист, строка {row_num}, поле «{field}» = '{value}' "
            f"не является числом."
        )


def _to_date(value, row_num: int, field: str) -> date:
    if _is_blank(value):
        raise ValueError(
            f"Лист, строка {row_num}, поле «{field}»: пусто. "
            f"Впишите дату в формате 2026-01-15."
        )
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(
        f"Лист, строка {row_num}, поле «{field}» = '{value}': "
        f"не распознана дата. Используйте формат 2026-01-15."
    )


def _check_columns(df: pd.DataFrame, required: set, sheet_name: str):
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Лист «{sheet_name}»: не хватает столбцов {sorted(missing)}. "
            f"Нужны: {sorted(required)}."
        )


# ============================================================
#  ЛИСТ "Товары"
# ============================================================
def load_products(xlsx_path: str) -> List[Product]:
    df = pd.read_excel(xlsx_path, sheet_name="Товары",
        skiprows=_detect_warning_row(xlsx_path, "Товары"))

    required = {"Товар", "Категория", "Закуп_1", "Закуп_2",
                "Цена_1", "Цена_2", "Кол_1", "Кол_2",
                "Закуп_кол_1", "Закуп_кол_2",
                "Остаток_нач_1", "Остаток_нач_2"}
    _check_columns(df, required, "Товары")

    products = []
    for idx, row in df.iterrows():
        # idx — это индекс DataFrame; +1 заголовок, +1 потому что Excel с 1
        row_num = idx + 2

        name = row.get("Товар", "")
        # Пропускаем полностью пустые строки
        if _is_blank(name):
            continue

        name = str(name).strip()
        # Пропускаем, если в строке вообще нет цифр — это шаблонная строка
        numeric_fields = ["Закуп_1", "Закуп_2", "Цена_1", "Цена_2",
                          "Кол_1", "Кол_2"]
        empty_numeric = [f for f in numeric_fields if _is_blank(row.get(f))]
        if len(empty_numeric) == len(numeric_fields):
            continue

        try:
            products.append(Product(
                name=name,
                category=str(row["Категория"]).strip(),
                purchase_price_1=_to_float(row["Закуп_1"], row_num, "Закуп_1"),
                purchase_price_2=_to_float(row["Закуп_2"], row_num, "Закуп_2"),
                sale_price_1=_to_float(row["Цена_1"], row_num, "Цена_1"),
                sale_price_2=_to_float(row["Цена_2"], row_num, "Цена_2"),
                qty_1=_to_int(row["Кол_1"], row_num, "Кол_1"),
                qty_2=_to_int(row["Кол_2"], row_num, "Кол_2"),
                purchase_qty_1=_to_int(row["Закуп_кол_1"], row_num, "Закуп_кол_1"),
                purchase_qty_2=_to_int(row["Закуп_кол_2"], row_num, "Закуп_кол_2"),
                stock_start_1=_to_int(row["Остаток_нач_1"], row_num, "Остаток_нач_1"),
                stock_start_2=_to_int(row["Остаток_нач_2"], row_num, "Остаток_нач_2"),
            ))
        except ValueError as e:
            raise ValueError(f"Товар «{name}»: {e}")

    if not products:
        raise ValueError(
            "Лист «Товары»: нет ни одной заполненной строки с товаром."
        )
    return products


# ============================================================
#  ЛИСТ "Периоды"
# ============================================================
def load_periods(xlsx_path: str) -> Tuple[Period, Period]:
    df = pd.read_excel(xlsx_path, sheet_name="Периоды",
        skiprows=_detect_warning_row(xlsx_path, "Периоды"))

    _check_columns(df, {"Поле", "Период 1", "Период 2"}, "Периоды")

    # Превращаем в словарь {имя_поля: (значение1, значение2)}
    data = {}
    for idx, row in df.iterrows():
        field = str(row["Поле"]).strip()
        if _is_blank(field):
            continue
        data[field] = (row["Период 1"], row["Период 2"])

    def get(field_partial: str, col: int):
        """Ищет поле, содержащее подстроку. col: 0 для 1, 1 для 2."""
        for key, vals in data.items():
            if field_partial.lower() in key.lower():
                return vals[col]
        raise ValueError(
            f"Лист «Периоды»: не найдено поле, содержащее «{field_partial}»."
        )

    periods = []
    for col, period_num in [(0, 1), (1, 2)]:
        name = str(get("Название", col)).strip()
        ds = _to_date(get("Дата начала", col), period_num, "Дата начала")
        de = _to_date(get("Дата конца", col), period_num, "Дата конца")
        season = str(get("Сезон", col)).strip().lower()
        fixed = _to_float(get("Постоянные издержки", col),
                          period_num, "Постоянные издержки")
        guests = _to_int(get("Гостей", col), period_num, "Гостей")

        p = Period(name=name, date_start=ds, date_end=de,
                   season=season, fixed_costs=fixed, guests=guests)
        err = p.validate()
        if err:
            raise ValueError(f"Лист «Периоды»: {err}")
        periods.append(p)

    return periods[0], periods[1]


# ============================================================
#  ЛИСТ "Ежедневные данные"
# ============================================================
def load_daily(xlsx_path: str,
               product_names: List[str]) -> DailyData:
    """
    Читает лист "Ежедневные данные".
    product_names — список имён товаров из листа "Товары".
    Возвращает DailyData (может быть пустой, если лист пуст).
    """
    try:
        df = pd.read_excel(xlsx_path, sheet_name="Ежедневные данные",
            skiprows=_detect_warning_row(xlsx_path, "Ежедневные данные"))
    except Exception:
        return DailyData([])

    if "Дата" not in df.columns or "Гостей" not in df.columns:
        # лист есть, но структура неправильная — считаем, что данных нет
        return DailyData([])

    rows = []
    for idx, row in df.iterrows():
        row_num = idx + 2

        d = row.get("Дата", "")
        if _is_blank(d):
            continue

        try:
            d_parsed = _to_date(d, row_num, "Дата")
            guests = _to_int(row["Гостей"], row_num, "Гостей")
        except ValueError as e:
            raise ValueError(str(e))

        sales = {}
        for pname in product_names:
            if pname in df.columns:
                v = row.get(pname, 0)
                if _is_blank(v):
                    sales[pname] = 0
                else:
                    try:
                        sales[pname] = int(float(v))
                    except Exception:
                        raise ValueError(
                            f"Лист «Ежедневные данные», строка {row_num}, "
                            f"столбец «{pname}»: '{v}' не число."
                        )

        rows.append(DailyRow(date=d_parsed, guests=guests, sales=sales))

    return DailyData(rows)


# ============================================================
#  ЛИСТ "Сезонная история"
# ============================================================
def load_season_history(xlsx_path: str) -> List[SeasonRecord]:
    try:
        df = pd.read_excel(xlsx_path, sheet_name="Сезонная история",
            skiprows=_detect_warning_row(xlsx_path, "Сезонная история"))
    except Exception:
        return []

    required = {"Сезон", "Товар", "Среднее_продаж_в_день",
                "Средний_поток_в_день"}
    if not required.issubset(df.columns):
        return []

    records = []
    for idx, row in df.iterrows():
        row_num = idx + 2
        season = row.get("Сезон", "")
        product = row.get("Товар", "")
        if _is_blank(season) or _is_blank(product):
            continue

        season = str(season).strip().lower()
        if season not in SEASONS:
            raise ValueError(
                f"Лист «Сезонная история», строка {row_num}: "
                f"сезон «{season}» не из {SEASONS}."
            )

        try:
            records.append(SeasonRecord(
                season=season,
                product=str(product).strip(),
                avg_sales_per_day=_to_float(
                    row["Среднее_продаж_в_день"], row_num,
                    "Среднее_продаж_в_день"),
                avg_flow_per_day=_to_float(
                    row["Средний_поток_в_день"], row_num,
                    "Средний_поток_в_день"),
            ))
        except ValueError as e:
            raise ValueError(str(e))

    return records


# ============================================================
#  ОБЩАЯ ЗАГРУЗКА
# ============================================================
class LoadedData:
    def __init__(self, products: List[Product],
                 periods: List[Period],
                 daily: DailyData,
                 season_records: List[SeasonRecord]):
        self.products = products
        self.periods = periods
        self.daily = daily
        self.season_records = season_records


def load_all(xlsx_path: str) -> LoadedData:
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(f"Файл '{xlsx_path}' не найден.")

    products = load_products(xlsx_path)
    p1, p2 = load_periods(xlsx_path)
    product_names = [p.name for p in products]
    daily = load_daily(xlsx_path, product_names)
    season_records = load_season_history(xlsx_path)

    return LoadedData(products, [p1, p2], daily, season_records)