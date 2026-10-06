"""
Генератор больших тестовых данных cafe_data.xlsx.

Создаёт файл с:
  - большим количеством товаров (по умолчанию 40);
  - полными периодами (январь и февраль 2026);
  - ежедневными данными за оба периода;
  - сезонной историей по 4 сезонам.

Используется для:
  - проверки производительности;
  - демонстрации программы на объёме;
  - нагрузочного тестирования.

Запуск:  python tools/generate_test_data.py
"""

import argparse
import os
import random
from datetime import date, timedelta

import pandas as pd

# Наборы названий товаров — выбираются случайно
READY_NAMES = [
    "Чипсы Lays", "Чипсы Pringles", "Печенье Oreo", "Печенье Юбилейное",
    "Шоколад Milka", "Шоколад Alpen Gold", "Батончик Snickers",
    "Батончик Twix", "Сухарики Кириешки", "Крекеры TUC",
    "Жвачка Orbit", "Жвачка Dirol", "Конфеты Skittles", "M&M's",
    "Попкорн", "Начос", "Кукурузные палочки", "Вафли",
]
DRINK_NAMES = [
    "Кофе американо", "Кофе капучино", "Кофе латте", "Кофе эспрессо",
    "Чай чёрный", "Чай зелёный", "Чай фруктовый",
    "Кола", "Спрайт", "Фанта", "Вода без газа", "Вода с газом",
    "Сок апельсиновый", "Сок яблочный", "Смузи", "Какао",
]


def _random_product(name, category, seed_offset):
    """Случайные данные для одного товара."""
    random.seed(hash(name) + seed_offset)

    # закупка
    base_buy = random.uniform(15, 90)
    buy_1 = round(base_buy, 2)
    # рост закупки от 5% до 30%
    buy_2 = round(buy_1 * random.uniform(1.05, 1.30), 2)

    # продажа: наценка 80–200% от закупки
    sale_1 = round(buy_1 * random.uniform(1.8, 3.0), 2)
    # рост продажи от 3% до 25%
    sale_2 = round(sale_1 * random.uniform(1.03, 1.25), 2)

    # продажи (штук за период ~месяц)
    qty_1 = random.randint(500, 3000)
    # падение продаж от −25% до +15%
    qty_2 = max(50, int(qty_1 * random.uniform(0.75, 1.15)))

    # закупки — с запасом
    purchase_qty_1 = int(qty_1 * random.uniform(1.05, 1.20))
    purchase_qty_2 = int(qty_2 * random.uniform(1.05, 1.20))

    # остатки
    stock_start_1 = random.randint(50, 300)
    # остаток на начало 2 = остаток на конец 1
    stock_end_1 = stock_start_1 + purchase_qty_1 - qty_1
    stock_start_2 = max(0, stock_end_1)

    return {
        "Товар": name,
        "Категория": category,
        "Закуп_1": buy_1, "Закуп_2": buy_2,
        "Цена_1": sale_1, "Цена_2": sale_2,
        "Кол_1": qty_1, "Кол_2": qty_2,
        "Закуп_кол_1": purchase_qty_1,
        "Закуп_кол_2": purchase_qty_2,
        "Остаток_нач_1": stock_start_1,
        "Остаток_нач_2": stock_start_2,
    }


def _generate_period_dates(start: date, days: int):
    return [(start + timedelta(days=i)) for i in range(days)]


def _daily_row(day: date, guests: int, products, base_avg_map):
    """Одна строка ежедневных данных."""
    row = {"Дата": day.isoformat(), "Гостей": guests}
    for p in products:
        base = base_avg_map[p["Товар"]]
        # случайное отклонение ±20%
        val = max(0, int(base * random.uniform(0.8, 1.2)))
        row[p["Товар"]] = val
    return row


def main():
    parser = argparse.ArgumentParser(description="Генератор тестовых данных")
    parser.add_argument("--products", type=int, default=40,
                        help="Количество товаров (по умолчанию 40)")
    parser.add_argument("--out", type=str,
                        default="cafe_data_big.xlsx",
                        help="Имя выходного файла")
    parser.add_argument("--seed", type=int, default=42,
                        help="Seed генератора")
    args = parser.parse_args()

    random.seed(args.seed)

    n = args.products
    n_ready = n // 2
    n_drink = n - n_ready

    ready_names = random.sample(READY_NAMES,
                                min(n_ready, len(READY_NAMES)))
    while len(ready_names) < n_ready:
        ready_names.append(f"Товар {len(ready_names) + 1}")

    drink_names = random.sample(DRINK_NAMES,
                                min(n_drink, len(DRINK_NAMES)))
    while len(drink_names) < n_drink:
        drink_names.append(f"Напиток {len(drink_names) + 1}")

    products = []
    for i, name in enumerate(ready_names):
        products.append(_random_product(name, "готовый", i))
    for i, name in enumerate(drink_names):
        products.append(_random_product(name, "напиток", i + 1000))

    # -------- Периоды --------
    p1_start = date(2026, 1, 1)
    p1_end = date(2026, 1, 31)
    p2_start = date(2026, 2, 1)
    p2_end = date(2026, 2, 28)

    guests_1 = 15000
    guests_2 = 13500

    periods_df = pd.DataFrame([
        {"Поле": "Название", "Период 1": "Январь 2026",
         "Период 2": "Февраль 2026"},
        {"Поле": "Дата начала", "Период 1": p1_start.isoformat(),
         "Период 2": p2_start.isoformat()},
        {"Поле": "Дата конца", "Период 1": p1_end.isoformat(),
         "Период 2": p2_end.isoformat()},
        {"Поле": "Сезон", "Период 1": "зима", "Период 2": "зима"},
        {"Поле": "Гостей", "Период 1": guests_1, "Период 2": guests_2},
        {"Поле": "Постоянные издержки, ₽", "Период 1": 300000,
         "Период 2": 320000},
    ])

    # -------- Ежедневные данные --------
    base_map_p1 = {p["Товар"]: p["Кол_1"] / 31 for p in products}
    base_map_p2 = {p["Товар"]: p["Кол_2"] / 28 for p in products}

    daily_rows = []
    for day in _generate_period_dates(p1_start, 31):
        is_weekend = day.weekday() >= 5
        guests = int(random.uniform(350, 550)) if is_weekend \
            else int(random.uniform(250, 400))
        daily_rows.append(_daily_row(day, guests, products, base_map_p1))
    for day in _generate_period_dates(p2_start, 28):
        is_weekend = day.weekday() >= 5
        guests = int(random.uniform(320, 520)) if is_weekend \
            else int(random.uniform(220, 380))
        daily_rows.append(_daily_row(day, guests, products, base_map_p2))
    daily_df = pd.DataFrame(daily_rows)

    # -------- Сезонная история --------
    season_rows = []
    for p in products:
        for season, coef, flow in [
            ("зима", 1.25, 450),
            ("весна", 1.05, 420),
            ("лето", 0.70, 350),
            ("осень", 1.10, 430),
        ]:
            avg_sales = max(5, int(p["Кол_2"] / 28 * coef))
            season_rows.append({
                "Сезон": season,
                "Товар": p["Товар"],
                "Среднее_продаж_в_день": avg_sales,
                "Средний_поток_в_день": flow,
            })
    season_df = pd.DataFrame(season_rows)

    # -------- Запись --------
    products_df = pd.DataFrame(products)

    with pd.ExcelWriter(args.out, engine="xlsxwriter") as w:
        products_df.to_excel(w, sheet_name="Товары", index=False)
        periods_df.to_excel(w, sheet_name="Периоды", index=False)
        daily_df.to_excel(w, sheet_name="Ежедневные данные", index=False)
        season_df.to_excel(w, sheet_name="Сезонная история", index=False)

    print(f"Файл создан: {os.path.abspath(args.out)}")
    print(f"  Товаров: {len(products)}")
    print(f"  Период 1: {p1_start} … {p1_end}")
    print(f"  Период 2: {p2_start} … {p2_end}")
    print(f"  Ежедневных строк: {len(daily_df)}")
    print(f"  Сезонных записей: {len(season_df)}")


if __name__ == "__main__":
    main()
