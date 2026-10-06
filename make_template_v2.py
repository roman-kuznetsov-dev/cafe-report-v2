"""
Создаёт шаблон данных cafe_data.xlsx версии 2.0.

4 листа:
  1. Товары              — данные по каждому товару
  2. Периоды             — общие данные о двух периодах
  3. Ежедневные данные   — по дням (для потока и будни/выходные)
  4. Сезонная история    — средние по сезонам (опционально)

Запуск:  python make_template_v2.py
"""

import os
import xlsxwriter


OUT = "cafe_data.xlsx"

# ============================================================
#  ДАННЫЕ ДЛЯ ПРИМЕРА (заказчик заменит)
# ============================================================

# Лист "Товары": (Название, Категория, Закуп1, Закуп2, Цена1, Цена2,
#                 Кол1, Кол2, Закуп_кол1, Закуп_кол2, Остаток_нач1, Остаток_нач2)
TOVARY = [
    ("ПРИМЕР: Чипсы",   "готовый", 45, 55, 90, 110, 3500, 3100, 5000, 4500, 800, 2300),
    ("ПРИМЕР: Печенье", "готовый", 30, 38, 70,  85, 4300, 3900, 5000, 4500, 500, 1200),
    ("ПРИМЕР: Шоколад", "готовый", 60, 75, 120, 150, 2400, 2100, 3000, 2500, 300, 900),
    ("ПРИМЕР: Кофе",    "напиток", 25, 32, 100, 130, 5800, 6300, 7000, 7000, 500, 1700),
    ("ПРИМЕР: Чай",     "напиток", 10, 14, 60,  80, 7200, 6600, 8000, 7500, 400, 1200),
    ("ПРИМЕР: Вода",    "напиток", 15, 20, 50,  65, 8500, 6200, 9000, 7000, 200, 700),
]

# Лист "Периоды"
PERIODS_HEADERS = ["Поле", "Период 1", "Период 2"]
PERIODS_DATA = [
    ("Название",                  "ПРИМЕР: Январь 2026",   "ПРИМЕР: Февраль 2026"),
    ("Дата начала",               "2026-01-01",            "2026-02-01"),
    ("Дата конца",                "2026-01-31",            "2026-02-28"),
    ("Сезон (зима/весна/лето/осень)", "зима",              "зима"),
    ("Гостей",                   500               450),
    ("Постоянные издержки, ₽",    30000,                   32000),
]

# Лист "Ежедневные данные" — генерируем пример для 31 дня января
# (заказчик заменит на реальные продажи)
DAILY_PRODUCTS = ["ПРИМЕР: Чипсы", "ПРИМЕР: Печенье", "ПРИМЕР: Шоколад",
                  "ПРИМЕР: Кофе", "ПРИМЕР: Чай", "ПРИМЕР: Вода"]

# Примерные средние продажи в будни и выходные (для генерации примера)
DAILY_WEEKDAY_AVG = [110, 140, 75, 190, 240, 280]
DAILY_WEEKEND_AVG = [180, 190, 110, 260, 300, 350]
DAILY_WEEKDAY_GUESTS = 420
DAILY_WEEKEND_GUESTS = 680

# Лист "Сезонная история" — 4 сезона × товары
SEASON_HISTORY = [
    # (Сезон, Товар, Среднее продаж в день, Средний поток в день)
    ("зима",  "ПРИМЕР: Чипсы",   145, 550),
    ("весна", "ПРИМЕР: Чипсы",   110, 470),
    ("лето",  "ПРИМЕР: Чипсы",    80, 400),
    ("осень", "ПРИМЕР: Чипсы",   120, 500),
    ("зима",  "ПРИМЕР: Кофе",    240, 550),
    ("весна", "ПРИМЕР: Кофе",    200, 470),
    ("лето",  "ПРИМЕР: Кофе",    130, 400),
    ("осень", "ПРИМЕР: Кофе",    210, 500),
    ("зима",  "ПРИМЕР: Вода",     50, 550),
    ("весна", "ПРИМЕР: Вода",     90, 470),
    ("лето",  "ПРИМЕР: Вода",    320, 400),
    ("осень", "ПРИМЕР: Вода",     70, 500),
]

# Категории для выпадающего списка
CATEGORIES = ["готовый", "напиток"]
SEASONS = ["зима", "весна", "лето", "осень"]


# ============================================================
#  ГЕНЕРАЦИЯ ШАБЛОНА
# ============================================================
def main():
    import datetime as dt
    import random
    random.seed(42)  # чтобы пример был всегда одинаковый

    wb = xlsxwriter.Workbook(OUT)

    # ---------- общие форматы ----------
    fmt_warn = wb.add_format({"bold": True, "font_color": "#C00000",
                              "font_size": 12, "bg_color": "#FFF2CC",
                              "border": 1, "align": "left", "valign": "vcenter"})
    fmt_head = wb.add_format({"bold": True, "bg_color": "#305496",
                              "font_color": "white", "border": 1,
                              "align": "center", "valign": "vcenter",
                              "text_wrap": True})
    fmt_text = wb.add_format({"border": 1, "align": "left", "valign": "vcenter"})
    fmt_num = wb.add_format({"border": 1, "align": "center",
                             "num_format": "#,##0.00"})
    fmt_int = wb.add_format({"border": 1, "align": "center",
                             "num_format": "0"})
    fmt_title = wb.add_format({"bold": True, "font_size": 13,
                               "bg_color": "#D9E1F2", "border": 1})
    fmt_note = wb.add_format({"italic": True, "font_color": "#666",
                              "text_wrap": True, "valign": "top"})

    # ============================================================
    #  ЛИСТ 1. "Товары"
    # ============================================================
    ws = wb.add_worksheet("Товары")

    ws.merge_range(0, 0, 0, 11,
                   "⚠ Это ПРИМЕР. Замените данные на свои перед запуском программы. "
                   "Строку-предупреждение удалите.",
                   fmt_warn)

    tovar_headers = [
        ("Товар",         "Название товара"),
        ("Категория",     "готовый или напиток"),
        ("Закуп_1",       "Закупочная цена в 1 периоде, ₽"),
        ("Закуп_2",       "Закупочная цена во 2 периоде, ₽"),
        ("Цена_1",        "Цена продажи в 1 периоде, ₽"),
        ("Цена_2",        "Цена продажи во 2 периоде, ₽"),
        ("Кол_1",         "Продано штук в 1 периоде"),
        ("Кол_2",         "Продано штук во 2 периоде"),
        ("Закуп_кол_1",   "Закуплено штук в 1 периоде"),
        ("Закуп_кол_2",   "Закуплено штук во 2 периоде"),
        ("Остаток_нач_1", "Остаток на начало 1 периода, шт"),
        ("Остаток_нач_2", "Остаток на начало 2 периода, шт"),
    ]
    for c, (h, note) in enumerate(tovar_headers):
        ws.write(1, c, h, fmt_head)
        ws.write_comment(1, c, note, {"width": 260, "height": 90})

    for r, row_data in enumerate(TOVARY, start=2):
        name, cat, z1, z2, c1, c2, k1, k2, zk1, zk2, ost1, ost2 = row_data
        ws.write_string(r, 0, name, fmt_text)
        ws.write_string(r, 1, cat, fmt_text)
        ws.write_number(r, 2, z1, fmt_num)
        ws.write_number(r, 3, z2, fmt_num)
        ws.write_number(r, 4, c1, fmt_num)
        ws.write_number(r, 5, c2, fmt_num)
        ws.write_number(r, 6, k1, fmt_int)
        ws.write_number(r, 7, k2, fmt_int)
        ws.write_number(r, 8, zk1, fmt_int)
        ws.write_number(r, 9, zk2, fmt_int)
        ws.write_number(r, 10, ost1, fmt_int)
        ws.write_number(r, 11, ost2, fmt_int)

    # Выпадающий список категорий
    ws.data_validation(2, 1, 500, 1, {
        "validate": "list", "source": CATEGORIES,
        "input_title": "Категория",
        "error_title": "Неверно",
        "error_message": "Только: готовый или напиток",
    })

    ws.set_column(0, 0, 22)
    ws.set_column(1, 1, 12)
    ws.set_column(2, 11, 14)
    ws.freeze_panes(2, 0)

    # ============================================================
    #  ЛИСТ 2. "Периоды"
    # ============================================================
    ws = wb.add_worksheet("Периоды")
    ws.merge_range(0, 0, 0, 2,
                   "⚠ Это ПРИМЕР. Заполните данные о периодах.",
                   fmt_warn)
    for c, h in enumerate(PERIODS_HEADERS):
        ws.write(1, c, h, fmt_head)
    for r, (field, v1, v2) in enumerate(PERIODS_DATA, start=2):
        ws.write_string(r, 0, field, fmt_text)
        if isinstance(v1, (int, float)):
            ws.write_number(r, 1, v1, fmt_num)
        else:
            ws.write_string(r, 1, str(v1), fmt_text)
        if isinstance(v2, (int, float)):
            ws.write_number(r, 2, v2, fmt_num)
        else:
            ws.write_string(r, 2, str(v2), fmt_text)

    # Список сезонов
    ws.data_validation(5, 1, 5, 2, {
        "validate": "list", "source": SEASONS,
        "input_title": "Сезон",
        "error_title": "Неверно",
        "error_message": "Один из: зима, весна, лето, осень",
    })

    ws.set_column(0, 0, 32)
    ws.set_column(1, 2, 22)

    # ============================================================
    #  ЛИСТ 3. "Ежедневные данные"
    # ============================================================
    ws = wb.add_worksheet("Ежедневные данные")
    n_cols = 2 + len(DAILY_PRODUCTS)  # Дата + Гостей + товары
    ws.merge_range(0, 0, 0, n_cols - 1,
                   "⚠ Это ПРИМЕР. Заполните реальными продажами по дням. "
                   "Дату пишите в формате ГГГГ-ММ-ДД, например 2026-01-15.",
                   fmt_warn)

    daily_headers = [("Дата", "Дата в формате 2026-01-01"),
                     ("Гостей", "Сколько людей зашло в кафе в этот день")]
    for p in DAILY_PRODUCTS:
        daily_headers.append((p, f"Продано: {p}"))

    for c, (h, note) in enumerate(daily_headers):
        ws.write(1, c, h, fmt_head)
        ws.write_comment(1, c, note, {"width": 220, "height": 70})

    # Генерируем 31 день января 2026
    start = dt.date(2026, 1, 1)
    for i in range(31):
        day = start + dt.timedelta(days=i)
        r = i + 2
        is_weekend = day.weekday() >= 5
        guests_base = DAILY_WEEKEND_GUESTS if is_weekend else DAILY_WEEKDAY_GUESTS
        guests = max(1, int(guests_base + random.randint(-40, 40)))

        ws.write_string(r, 0, day.isoformat(), fmt_text)
        ws.write_number(r, 1, guests, fmt_int)

        base_avg = DAILY_WEEKEND_AVG if is_weekend else DAILY_WEEKDAY_AVG
        for j, avg in enumerate(base_avg):
            noise = random.randint(-int(avg * 0.15), int(avg * 0.15))
            val = max(0, avg + noise)
            ws.write_number(r, 2 + j, val, fmt_int)

    ws.set_column(0, 0, 12)
    ws.set_column(1, 1, 10)
    ws.set_column(2, n_cols - 1, 14)
    ws.freeze_panes(2, 0)

    # ============================================================
    #  ЛИСТ 4. "Сезонная история"
    # ============================================================
    ws = wb.add_worksheet("Сезонная история")
    ws.merge_range(0, 0, 0, 3,
                   "⚠ Это ПРИМЕР. Заполните средние продажи и поток за прошлые сезоны. "
                   "Если истории нет — оставьте лист пустым, "
                   "и вкладка «Сезонность» покажет только текущий сезон.",
                   fmt_warn)

    sh_headers = [
        ("Сезон", "зима / весна / лето / осень"),
        ("Товар", "Название товара (как в листе «Товары»)"),
        ("Среднее_продаж_в_день", "Средние продажи штук в день за этот сезон"),
        ("Средний_поток_в_день", "Средний поток гостей в день за этот сезон"),
    ]
    for c, (h, note) in enumerate(sh_headers):
        ws.write(1, c, h, fmt_head)
        ws.write_comment(1, c, note, {"width": 260, "height": 80})

    for r, (season, tovar, sale, flow) in enumerate(SEASON_HISTORY, start=2):
        ws.write_string(r, 0, season, fmt_text)
        ws.write_string(r, 1, tovar, fmt_text)
        ws.write_number(r, 2, sale, fmt_int)
        ws.write_number(r, 3, flow, fmt_int)

    ws.data_validation(2, 0, 500, 0, {
        "validate": "list", "source": SEASONS,
        "input_title": "Сезон",
    })

    ws.set_column(0, 0, 10)
    ws.set_column(1, 1, 22)
    ws.set_column(2, 3, 24)
    ws.freeze_panes(2, 0)

    # ============================================================
    #  ЛИСТ 5. "Инструкция"
    # ============================================================
    ws = wb.add_worksheet("Инструкция")
    ws.set_column(0, 0, 120)
    lines = [
        ("КАК ЗАПОЛНЯТЬ ШАБЛОН (версия 2.0)", True),
        ("", False),
        ("Лист 1. «Товары»", True),
        ("  По одной строке на каждый товар. 12 столбцов:", False),
        ("  Товар, Категория, Закуп_1, Закуп_2, Цена_1, Цена_2,", False),
        ("  Кол_1, Кол_2, Закуп_кол_1, Закуп_кол_2, Остаток_нач_1, Остаток_нач_2", False),
        ("  • Закуп_кол — сколько штук КУПИЛИ у поставщика.", False),
        ("  • Остаток_нач — сколько штук было на складе на начало периода.", False),
        ("  • Проверка: Остаток_нач + Закуп_кол − Кол = остаток на конец.", False),
        ("", False),
        ("Лист 2. «Периоды»", True),
        ("  Общие данные за два периода: даты, сезон, постоянные издержки.", False),
        ("  Сезон — одно из: зима, весна, лето, осень.", False),
        ("", False),
        ("Лист 3. «Ежедневные данные»", True),
        ("  По одной строке на КАЖДЫЙ ДЕНЬ каждого периода.", False),
        ("  Дата в формате 2026-01-15 (год-месяц-день).", False),
        ("  Гостей — сколько людей зашло в кафе за день.", False),
        ("  Далее — столбцы по каждому товару: сколько продано за день.", False),
        ("  День недели и месяц программа определит сама.", False),
        ("  Если этих данных нет — оставьте лист пустым.", False),
        ("", False),
        ("Лист 4. «Сезонная история»", True),
        ("  Средние продажи и поток за ПРОШЛЫЕ сезоны (для прогноза).", False),
        ("  Если истории нет — оставьте лист пустым.", False),
        ("", False),
        ("ОБЩИЕ ПРАВИЛА", True),
        ("  • Заголовки не переименовывать и не удалять.", False),
        ("  • Числа без «₽», «шт.», пробелов.", False),
        ("  • Пустых ячеек быть не должно: ставьте 0.", False),
        ("  • Перед запуском программы сохраните файл (Ctrl+S).", False),
    ]
    fmt_h = wb.add_format({"bold": True, "font_size": 12, "font_color": "#305496"})
    fmt_t = wb.add_format({"text_wrap": True, "valign": "top"})
    for i, (text, is_h) in enumerate(lines):
        ws.write(i, 0, text, fmt_h if is_h else fmt_t)

    wb.close()
    print(f"Шаблон создан: {os.path.abspath(OUT)}")
    print("Откройте файл в Excel и проверьте 5 листов.")


if __name__ == "__main__":
    main()