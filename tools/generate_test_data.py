"""
Реалистичный генератор тестовых данных cafe_data.xlsx.

Особенности:
  - Каждый запуск без --seed создаёт РАЗНЫЕ данные.
  - У каждого товара — свой профиль: базовая цена, наценка,
    популярность, эластичность, сезонный паттерн.
  - Будни и выходные имеют разный поток.
  - Сезонность: зимой — кофе и чипсы, летом — вода и мороженое.
  - Случайный шум делает данные «живыми».
  - Ежедневные данные — за ОБА периода.

Запуск:
    python tools/generate_test_data.py
    python tools/generate_test_data.py --products 60 --out big.xlsx
    python tools/generate_test_data.py --seed 42   (повторяемо)
"""

import argparse
import os
import random
from datetime import date, timedelta

import pandas as pd

# ============================================================
#  КАТАЛОГ ТОВАРОВ С ПРОФИЛЯМИ
# ============================================================
# Профиль: (имя, категория, базовая_закупка, целевая_наценка_%,
#           базовая_популярность_в_день, эластичность,
#           сезонный_паттерн)
#   сезонный_паттерн: 'зима' | 'лето' | 'всесезонный'
# ============================================================
PRODUCT_CATALOG = [
    # Готовые товары (снеки)
    ("Чипсы Lays",         "готовый", 60,  90,  25, 0.9, "зима"),
    ("Чипсы Pringles",     "готовый", 130, 80,   8, 0.7, "зима"),
    ("Печенье Oreo",       "готовый", 55,  95,  12, 0.6, "всесезонный"),
    ("Печенье Юбилейное",  "готовый", 40,  85,  15, 0.5, "всесезонный"),
    ("Шоколад Milka",      "готовый", 90,  100, 10, 0.8, "зима"),
    ("Шоколад Alpen Gold", "готовый", 70,  95,  12, 0.7, "зима"),
    ("Батончик Snickers",  "готовый", 45,  110, 20, 0.9, "всесезонный"),
    ("Батончик Twix",      "готовый", 45,  110, 18, 0.9, "всесезонный"),
    ("Сухарики Кириешки",  "готовый", 20,  120, 30, 1.1, "зима"),
    ("Крекеры TUC",        "готовый", 55,  90,  10, 0.6, "всесезонный"),
    ("Жвачка Orbit",       "готовый", 30,  130, 25, 0.8, "всесезонный"),
    ("Жвачка Dirol",       "готовый", 30,  130, 22, 0.8, "всесезонный"),
    ("Конфеты Skittles",   "готовый", 60,  100, 15, 0.7, "всесезонный"),
    ("M&M's",              "готовый", 70,  95,  12, 0.7, "всесезонный"),
    ("Попкорн",            "готовый", 35,  110, 18, 0.9, "зима"),
    ("Начос",              "готовый", 50,  105, 14, 0.8, "зима"),
    ("Кукурузные палочки", "готовый", 25,  120, 20, 0.9, "всесезонный"),
    ("Вафли",              "готовый", 35,  100, 15, 0.7, "всесезонный"),
    ("Мороженое рожок",    "готовый", 40,  110, 22, 0.6, "лето"),
    ("Мороженое стакан",   "готовый", 55,  100, 15, 0.6, "лето"),
    # Напитки
    ("Кофе американо",     "напиток", 15,  300, 45, 0.7, "зима"),
    ("Кофе капучино",      "напиток", 25,  280, 35, 0.7, "зима"),
    ("Кофе латте",         "напиток", 28,  270, 30, 0.7, "зима"),
    ("Кофе эспрессо",      "напиток", 12,  350, 20, 0.6, "зима"),
    ("Чай чёрный",         "напиток", 8,   400, 40, 0.5, "зима"),
    ("Чай зелёный",        "напиток", 8,   400, 30, 0.5, "всесезонный"),
    ("Чай фруктовый",      "напиток", 10,  380, 25, 0.6, "зима"),
    ("Кола",               "напиток", 30,  150, 35, 0.8, "лето"),
    ("Спрайт",             "напиток", 30,  150, 25, 0.8, "лето"),
    ("Фанта",              "напиток", 30,  150, 22, 0.8, "лето"),
    ("Вода без газа",      "напиток", 12,  200, 55, 0.4, "лето"),
    ("Вода с газом",       "напиток", 14,  200, 45, 0.4, "лето"),
    ("Сок апельсиновый",   "напиток", 30,  150, 20, 0.7, "лето"),
    ("Сок яблочный",       "напиток", 28,  150, 18, 0.7, "всесезонный"),
    ("Смузи",              "напиток", 55,  200, 12, 0.9, "лето"),
    ("Какао",              "напиток", 20,  250, 20, 0.7, "зима"),
]


# ============================================================
#  ПЕРИОДЫ
# ============================================================
PERIODS = [
    {"name": "Январь 2026", "start": date(2026, 1, 1),
     "end": date(2026, 1, 31), "season": "зима"},
    {"name": "Февраль 2026", "start": date(2026, 2, 1),
     "end": date(2026, 2, 28), "season": "зима"},
]


# ============================================================
#  ВСПОМОГАТЕЛЬНЫЕ
# ============================================================
def _noise(value: float, sigma: float = 0.15) -> float:
    """Добавляет случайный шум ±sigma к значению."""
    return value * random.uniform(1 - sigma, 1 + sigma)


def _seasonal_factor(profile_season: str, period_season: str) -> float:
    """Множитель популярности в зависимости от сезона."""
    if profile_season == "всесезонный":
        return 1.0
    if profile_season == period_season:
        return random.uniform(1.3, 1.6)
    return random.uniform(0.4, 0.7)


def _weekend_factor(is_weekend: bool) -> float:
    """В выходные поток выше."""
    return 1.5 if is_weekend else 1.0


# ============================================================
#  ГЛАВНАЯ ЛОГИКА
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Реалистичный генератор данных")
    parser.add_argument("--products", type=int, default=20,
                        help="Сколько товаров (макс 36)")
    parser.add_argument("--out", type=str, default="cafe_data_big.xlsx",
                        help="Имя выходного файла")
    parser.add_argument("--seed", type=int, default=None,
                        help="Seed для повторяемости (по умолчанию — разный)")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    n = min(args.products, len(PRODUCT_CATALOG))
    catalog = random.sample(PRODUCT_CATALOG, n)

    # -------- Профили товаров --------
    products_rows = []
    profiles = {}   # {имя: профиль}

    for profile in catalog:
        name, cat, base_buy, target_markup, base_pop, elast, season_pref = profile
        profiles[name] = {
            "season_pref": season_pref,
            "base_pop": base_pop,
        }

        # --- Период 1 ---
        buy1 = round(_noise(base_buy, 0.05), 2)
        markup1 = _noise(target_markup, 0.05)
        sale1 = round(buy1 * (1 + markup1 / 100), 2)

        # --- Период 2 ---
        buy2 = round(buy1 * random.uniform(1.05, 1.25), 2)
        buy2 = round(_noise(buy2, 0.03), 2)
        markup2 = markup1 * random.uniform(0.9, 1.05)
        sale2 = round(buy2 * (1 + markup2 / 100), 2)

        # --- Продажи по периодам ---
        days1 = (PERIODS[0]["end"] - PERIODS[0]["start"]).days + 1
        days2 = (PERIODS[1]["end"] - PERIODS[1]["start"]).days + 1

        sf1 = _seasonal_factor(season_pref, PERIODS[0]["season"])
        sf2 = _seasonal_factor(season_pref, PERIODS[1]["season"])

        daily1 = _noise(base_pop, 0.15) * sf1
        daily2 = _noise(base_pop, 0.15) * sf2

        qty1 = int(daily1 * days1)
        qty2 = int(daily2 * days2)

        # Эффект эластичности
        price_change = (sale2 - sale1) / sale1 if sale1 else 0
        qty2 = int(qty2 * (1 - elast * price_change))

        qty1 = max(20, qty1)
        qty2 = max(20, qty2)

        # Закупки с запасом
        purchase1 = int(qty1 * random.uniform(1.05, 1.20))
        purchase2 = int(qty2 * random.uniform(1.05, 1.20))

        # Остатки
        stock1 = random.randint(20, 100)
        stock_end1 = stock1 + purchase1 - qty1
        stock2 = max(0, stock_end1)

        products_rows.append({
            "Товар": name,
            "Категория": cat,
            "Закуп_1": buy1,
            "Закуп_2": buy2,
            "Цена_1": sale1,
            "Цена_2": sale2,
            "Кол_1": qty1,
            "Кол_2": qty2,
            "Закуп_кол_1": purchase1,
            "Закуп_кол_2": purchase2,
            "Остаток_нач_1": stock1,
            "Остаток_нач_2": stock2,
        })

    products_df = pd.DataFrame(products_rows)

    # -------- Ежедневные данные за ОБА периода --------
    daily_rows = []
    guests_total_1 = 0
    guests_total_2 = 0

    for idx, period in enumerate(PERIODS):
        current = period["start"]
        season = period["season"]

        while current <= period["end"]:
            is_weekend = current.weekday() >= 5
            base_guests = 350 if is_weekend else 250
            guests = int(_noise(base_guests, 0.15))
            guests = max(50, guests)

            if idx == 0:
                guests_total_1 += guests
            else:
                guests_total_2 += guests

            row = {"Дата": current.isoformat(), "Гостей": guests}

            for name, prof in profiles.items():
                sf = _seasonal_factor(prof["season_pref"], season)
                wf = _weekend_factor(is_weekend)
                daily = _noise(prof["base_pop"], 0.25) * sf * wf
                daily = max(0, daily)
                row[name] = int(daily)

            daily_rows.append(row)
            current += timedelta(days=1)

    daily_df = pd.DataFrame(daily_rows)

    # -------- Периоды --------
    periods_df = pd.DataFrame([
        {"Поле": "Название",
         "Период 1": PERIODS[0]["name"],
         "Период 2": PERIODS[1]["name"]},
        {"Поле": "Дата начала",
         "Период 1": PERIODS[0]["start"].isoformat(),
         "Период 2": PERIODS[1]["start"].isoformat()},
        {"Поле": "Дата конца",
         "Период 1": PERIODS[0]["end"].isoformat(),
         "Период 2": PERIODS[1]["end"].isoformat()},
        {"Поле": "Сезон",
         "Период 1": PERIODS[0]["season"],
         "Период 2": PERIODS[1]["season"]},
        {"Поле": "Гостей",
         "Период 1": guests_total_1,
         "Период 2": guests_total_2},
        {"Поле": "Постоянные издержки, ₽",
         "Период 1": random.randint(250000, 400000),
         "Период 2": random.randint(250000, 400000)},
    ])

    # -------- Сезонная история --------
    season_rows = []
    for name, prof in profiles.items():
        for season in ["зима", "весна", "лето", "осень"]:
            if prof["season_pref"] == season:
                factor = 1.5
            elif prof["season_pref"] == "всесезонный":
                factor = 1.0
            else:
                factor = 0.6

            avg_sales = max(2, int(prof["base_pop"] * factor))
            flow = int(_noise(400, 0.05))
            season_rows.append({
                "Сезон": season,
                "Товар": name,
                "Среднее_продаж_в_день": avg_sales,
                "Средний_поток_в_день": flow,
            })
    season_df = pd.DataFrame(season_rows)

    # -------- Запись --------
    with pd.ExcelWriter(args.out, engine="xlsxwriter") as w:
        products_df.to_excel(w, sheet_name="Товары", index=False)
        periods_df.to_excel(w, sheet_name="Периоды", index=False)
        daily_df.to_excel(w, sheet_name="Ежедневные данные", index=False)
        season_df.to_excel(w, sheet_name="Сезонная история", index=False)

    print(f"Файл создан: {os.path.abspath(args.out)}")
    print(f"  Товаров: {len(products_df)}")
    print(f"  Период 1: {PERIODS[0]['start']} … {PERIODS[0]['end']}")
    print(f"  Период 2: {PERIODS[1]['start']} … {PERIODS[1]['end']}")
    print(f"  Ежедневных строк: {len(daily_df)}")
    print(f"  Сезонных записей: {len(season_df)}")
    print(f"  Гостей в 1 периоде: {guests_total_1}")
    print(f"  Гостей во 2 периоде: {guests_total_2}")


if __name__ == "__main__":
    main()
