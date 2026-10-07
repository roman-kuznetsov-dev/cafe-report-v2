"""
Экспорт Analysis в Excel с подсветкой (версия 2.0).

Создаёт 9 листов:
  1. Сводка
  2. Обоснованность
  3. Закупки и остатки
  4. Денежный поток
  5. Поток гостей
  6. Сезонность
  7. Будни и выходные
  8. Категории
  9. Безубыточность
"""

import pandas as pd

from cafe_analysis import Analysis


# ============================================================
#  ЗАГОЛОВКИ
# ============================================================
def _write_headers(ws, columns, fmt, row=0):
    for c, name in enumerate(columns):
        ws.write(row, c, name, fmt)


# ============================================================
#  ЛИСТ 1. Сводка
# ============================================================
def _sheet_summary(a: Analysis):
    rows = []
    for s in a.summaries:
        rows.append({
            "Товар": s.name,
            "Категория": s.category,
            "Выручка_1": round(s.revenue_1, 2),
            "Выручка_2": round(s.revenue_2, 2),
            "Прибыль_1": round(s.profit_1, 2),
            "Прибыль_2": round(s.profit_2, 2),
            "Δ Прибыль": round(s.delta_profit(), 2),
            "Δ Прибыль_%": round(s.delta_profit_pct(), 1),
            "Наценка_1_%": round(s.markup_1, 1),
            "Наценка_2_%": round(s.markup_2, 1),
        })
    return pd.DataFrame(rows)

def _sheet_period_warnings(a: Analysis):
    """Лист с предупреждениями о периодах."""
    warnings = a.period_warnings()
    if not warnings:
        return pd.DataFrame([{
            "Статус": "OK",
            "Предупреждение": "Периоды сопоставимы. Сравнение корректно."
        }])
    rows = [{"Статус": "⚠", "Предупреждение": w} for w in warnings]
    return pd.DataFrame(rows)

# ============================================================
#  ЛИСТ 2. Обоснованность
# ============================================================
def _sheet_justification(a: Analysis):
    rows = []
    for c in a.checks:
        rows.append({
            "Товар": c.product,
            "Критерий": c.criterion,
            "Было": round(c.before, 2),
            "Стало": round(c.after, 2),
            "Ед.": c.unit,
            "Результат": "OK" if c.ok else "НЕТ",
        })
    rows.append({
        "Товар": "ВСЕГО",
        "Критерий": "Общая прибыль",
        "Было": round(a.total_profit(1), 2),
        "Стало": round(a.total_profit(2), 2),
        "Ед.": "₽",
        "Результат": f"{'OK' if a.verdict.checks['Общая прибыль'] else 'НЕТ'} "
                     f"({a.total_profit_delta_pct():+.1f}%)",
    })
    rows.append({"Товар": "", "Критерий": "", "Было": "", "Стало": "",
                 "Ед.": "", "Результат": ""})
    rows.append({
        "Товар": "ВЕРДИКТ",
        "Критерий": a.verdict.text,
        "Было": f"{a.verdict.score}/{a.verdict.total}",
        "Стало": "", "Ед.": "", "Результат": "",
    })
    return pd.DataFrame(rows)


# ============================================================
#  ЛИСТ 3. Закупки и остатки
# ============================================================
def _sheet_stock(a: Analysis):
    rows = []
    for p in a.products:
        rows.append({
            "Товар": p.name,
            "Остаток_нач_1": p.stock_start_1,
            "Закуплено_1": p.purchase_qty_1,
            "Продано_1": p.qty_1,
            "Остаток_кон_1": p.stock_end(1),
            "Стоимость_остатка_1": round(p.stock_value(1), 2),
            "Остаток_нач_2": p.stock_start_2,
            "Закуплено_2": p.purchase_qty_2,
            "Продано_2": p.qty_2,
            "Остаток_кон_2": p.stock_end(2),
            "Стоимость_остатка_2": round(p.stock_value(2), 2),
        })
    rows.append({
        "Товар": "ИТОГО",
        "Остаток_нач_1": "", "Закуплено_1": "", "Продано_1": "",
        "Остаток_кон_1": "",
        "Стоимость_остатка_1": round(a.total_stock_value(1), 2),
        "Остаток_нач_2": "", "Закуплено_2": "", "Продано_2": "",
        "Остаток_кон_2": "",
        "Стоимость_остатка_2": round(a.total_stock_value(2), 2),
    })
    return pd.DataFrame(rows)


# ============================================================
#  ЛИСТ 4. Денежный поток
# ============================================================
def _sheet_cashflow(a: Analysis):
    rows = []
    for s in a.summaries:
        rows.append({
            "Товар": s.name,
            "Управленческая_прибыль_1": round(s.profit_1, 2),
            "Управленческая_прибыль_2": round(s.profit_2, 2),
            "Денежный_поток_1": round(s.cash_flow_1, 2),
            "Денежный_поток_2": round(s.cash_flow_2, 2),
            "Разница_1": round(s.profit_1 - s.cash_flow_1, 2),
            "Разница_2": round(s.profit_2 - s.cash_flow_2, 2),
        })
    rows.append({
        "Товар": "ИТОГО",
        "Управленческая_прибыль_1": round(a.total_profit(1), 2),
        "Управленческая_прибыль_2": round(a.total_profit(2), 2),
        "Денежный_поток_1": round(a.total_cash_flow(1), 2),
        "Денежный_поток_2": round(a.total_cash_flow(2), 2),
        "Разница_1": round(a.total_profit(1) - a.total_cash_flow(1), 2),
        "Разница_2": round(a.total_profit(2) - a.total_cash_flow(2), 2),
    })
    return pd.DataFrame(rows)


# ============================================================
#  ЛИСТ 5. Поток гостей
# ============================================================
def _sheet_flow(a: Analysis):
    rows = []
    for r in a.flow_summary():
        rows.append({
            "Товар": r["Товар"],
            "Конверсия_1": round(r["Конв_1"], 4),
            "Конверсия_2": round(r["Конв_2"], 4),
            "ΔКонверсия_%": round(r["ΔКонв_%"], 2),
            "Влияние_потока": round(r["Эффект_потока"], 2),
            "Влияние_конверсии": round(r["Эффект_конверсии"], 2),
            "ΔПродано": r["ΔПродано"],
        })
    return pd.DataFrame(rows)


# ============================================================
#  ЛИСТ 6. Сезонность
# ============================================================
def _sheet_seasonality(a: Analysis):
    if not a.has_season_history():
        return pd.DataFrame([{
            "Сообщение": "Нет данных о сезонной истории. "
                         "Заполните лист «Сезонная история»."
        }])

    coef = a.season_coefficients()
    rows = []
    for product, seasons in coef.items():
        row = {"Товар": product}
        for s, v in seasons.items():
            row[s] = round(v, 3)
        rows.append(row)
    df_coef = pd.DataFrame(rows)

    f_rows = a.season_forecast_per_product()
    df_forecast = pd.DataFrame([{
        "Товар": f["Товар"],
        "Конверсия": round(f["Конверсия"], 4),
        "Прогноз_в_день": round(f["Прогноз_в_день"], 2),
        "Прогноз_за_период": round(f["Прогноз_за_период"], 2),
    } for f in f_rows])

    return df_coef, df_forecast


# ============================================================
#  ЛИСТ 7. Будни и выходные
# ============================================================
def _sheet_weekday_weekend(a: Analysis):
    if not a.has_daily_data():
        return pd.DataFrame([{
            "Сообщение": "Нет ежедневных данных. "
                         "Заполните лист «Ежедневные данные»."
        }])

    rows = []
    for period_num, period_name in [(1, a.p1.name), (2, a.p2.name)]:
        w = a.weekday_weekend_for_period(period_num)
        if not w:
            continue
        g = w["guests"]
        rows.append({
            "Период": period_name,
            "Товар": "(гости)",
            "Будни": round(g["будни"], 2),
            "Выходные": round(g["выходные"], 2),
            "Индекс_вых": round(g["индекс_вых"], 2),
        })
        for name, vals in w["products"].items():
            rows.append({
                "Период": period_name,
                "Товар": name,
                "Будни": round(vals["будни"], 2),
                "Выходные": round(vals["выходные"], 2),
                "Индекс_вых": round(vals["индекс_вых"], 2),
            })
    return pd.DataFrame(rows)


# ============================================================
#  ЛИСТ 8. Категории
# ============================================================
def _sheet_categories(a: Analysis):
    cats = sorted({p.category for p in a.products})
    rows = []
    for cat in cats:
        items = [p for p in a.products if p.category == cat]
        rows.append({
            "Категория": cat,
            "Выручка_1": round(sum(p.revenue(1) for p in items), 2),
            "Выручка_2": round(sum(p.revenue(2) for p in items), 2),
            "Прибыль_1": round(sum(p.profit(1) for p in items), 2),
            "Прибыль_2": round(sum(p.profit(2) for p in items), 2),
            "Δ Прибыль": round(
                sum(p.profit(2) - p.profit(1) for p in items), 2),
        })
    return pd.DataFrame(rows)


# ============================================================
#  ЛИСТ 9. Безубыточность
# ============================================================
def _sheet_breakeven(a: Analysis):
    df_be = pd.DataFrame(a.breakeven_simple(2))
    df_cafe = pd.DataFrame([a.breakeven_cafe_total(1),
                            a.breakeven_cafe_total(2)])
    return df_be, df_cafe


# ============================================================
#  ГЛАВНАЯ ФУНКЦИЯ
# ============================================================
def export_to_excel(analysis: Analysis, out_path: str):
    """Сохраняет отчёт в Excel с подсветкой (9 листов)."""
    df_summary = _sheet_summary(analysis)
    df_just = _sheet_justification(analysis)
    df_stock = _sheet_stock(analysis)
    df_cash = _sheet_cashflow(analysis)
    df_flow = _sheet_flow(analysis)
    season_result = _sheet_seasonality(analysis)
    df_weekday = _sheet_weekday_weekend(analysis)
    df_cat = _sheet_categories(analysis)
    df_be, df_be_cafe = _sheet_breakeven(analysis)
    df_warnings = _sheet_period_warnings(analysis)

    with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
        # --- Запись данных ---
        df_warnings.to_excel(writer, sheet_name="Предупреждения", index=False)
        df_summary.to_excel(writer, sheet_name="Сводка", index=False)
        df_just.to_excel(writer, sheet_name="Обоснованность", index=False)
        df_stock.to_excel(writer, sheet_name="Закупки и остатки", index=False)
        df_cash.to_excel(writer, sheet_name="Денежный поток", index=False)
        df_flow.to_excel(writer, sheet_name="Поток гостей", index=False)

        if isinstance(season_result, tuple):
            df_coef, df_forecast = season_result
            df_coef.to_excel(writer, sheet_name="Сезонность", index=False)
            df_forecast.to_excel(writer, sheet_name="Сезонность",
                                 index=False, startrow=len(df_coef) + 3)
        else:
            season_result.to_excel(writer, sheet_name="Сезонность",
                                   index=False)

        df_weekday.to_excel(writer, sheet_name="Будни и выходные",
                            index=False)
        df_cat.to_excel(writer, sheet_name="Категории", index=False)

        df_be.to_excel(writer, sheet_name="Безубыточность", index=False)
        df_be_cafe.to_excel(writer, sheet_name="Безубыточность",
                            index=False, startrow=len(df_be) + 3)

        # --- Форматирование ---
        wb = writer.book
        fmt_head = wb.add_format({
            "bold": True, "bg_color": "#305496", "font_color": "white",
            "border": 1, "align": "center", "valign": "vcenter",
            "text_wrap": True})
        fmt_ok = wb.add_format({"bg_color": "#C6EFCE",
                                "font_color": "#006100", "border": 1})
        fmt_bad = wb.add_format({"bg_color": "#FFC7CE",
                                 "font_color": "#9C0006", "border": 1})
        fmt_money = wb.add_format({"num_format": "#,##0.00", "border": 1})
        fmt_pct = wb.add_format({"num_format": '0.0"%"', "border": 1})
        fmt_int = wb.add_format({"num_format": "0", "border": 1})
        fmt_title = wb.add_format({"bold": True, "font_size": 12,
                                   "bg_color": "#D9E1F2", "border": 1})

        # Предупреждения
        ws = writer.sheets["Предупреждения"]
        _write_headers(ws, df_warnings.columns, fmt_head)
        ws.set_column(0, 0, 10)
        ws.set_column(1, 1, 120)

        fmt_warn_row = wb.add_format({"bg_color": "#FFF2CC",
                               "font_color": "#7F6000",
                               "border": 1, "text_wrap": True})
        for i in range(len(df_warnings)):
            ws.write(i + 1, 0, df_warnings.iloc[i, 0], fmt_warn_row)
            ws.write(i + 1, 1, df_warnings.iloc[i, 1], fmt_warn_row)

        # Сводка
        ws = writer.sheets["Сводка"]
        _write_headers(ws, df_summary.columns, fmt_head)
        ws.set_column(0, 1, 14)
        for c, name in enumerate(df_summary.columns):
            if "Прибыль" in name or "Выручка" in name:
                ws.set_column(c, c, 14, fmt_money)
            elif "%" in name:
                ws.set_column(c, c, 12, fmt_pct)
            else:
                ws.set_column(c, c, 12)

        # Обоснованность
        ws = writer.sheets["Обоснованность"]
        _write_headers(ws, df_just.columns, fmt_head)
        ws.set_column(0, 0, 22)
        ws.set_column(1, 1, 22)
        ws.set_column(2, 4, 12)
        ws.set_column(5, 5, 18)
        for i, row in df_just.iterrows():
            result = str(row["Результат"])
            if result.startswith("OK"):
                ws.write(i + 1, 5, result, fmt_ok)
            elif result.startswith("НЕТ"):
                for c in range(len(df_just.columns)):
                    ws.write(i + 1, c, row.iloc[c], fmt_bad)

        # Закупки и остатки
        ws = writer.sheets["Закупки и остатки"]
        _write_headers(ws, df_stock.columns, fmt_head)
        ws.set_column(0, 0, 14)
        for c in range(1, len(df_stock.columns)):
            if "Стоимость" in df_stock.columns[c]:
                ws.set_column(c, c, 18, fmt_money)
            else:
                ws.set_column(c, c, 14, fmt_int)

        # Денежный поток
        ws = writer.sheets["Денежный поток"]
        _write_headers(ws, df_cash.columns, fmt_head)
        ws.set_column(0, 0, 14)
        for c in range(1, len(df_cash.columns)):
            ws.set_column(c, c, 22, fmt_money)

        # Поток гостей
        ws = writer.sheets["Поток гостей"]
        _write_headers(ws, df_flow.columns, fmt_head)
        ws.set_column(0, 0, 14)
        for c, name in enumerate(df_flow.columns):
            if "Конв" in name:
                ws.set_column(c, c, 14, fmt_money)
            elif "%" in name:
                ws.set_column(c, c, 14, fmt_pct)
            else:
                ws.set_column(c, c, 18, fmt_money)

        # Сезонность
        ws = writer.sheets["Сезонность"]
        if isinstance(season_result, tuple):
            df_coef, df_forecast = season_result
            _write_headers(ws, df_coef.columns, fmt_head)
            ws.set_column(0, 0, 18)
            for c in range(1, len(df_coef.columns)):
                ws.set_column(c, c, 12, fmt_money)
            start = len(df_coef) + 3
            ws.merge_range(start, 0, start, 3,
                           "ПРОГНОЗ ПРОДАЖ НА БУДУЩИЙ ПЕРИОД "
                           "(сезон текущего)",
                           fmt_title)
            _write_headers(ws, df_forecast.columns, fmt_head, row=start + 1)
            for c in range(len(df_forecast.columns)):
                ws.set_column(c, c, 20, fmt_money)

        # Будни и выходные
        ws = writer.sheets["Будни и выходные"]
        _write_headers(ws, df_weekday.columns, fmt_head)
        ws.set_column(0, 1, 16)
        for c in range(2, len(df_weekday.columns)):
            ws.set_column(c, c, 16, fmt_money)

        # Категории
        ws = writer.sheets["Категории"]
        _write_headers(ws, df_cat.columns, fmt_head)
        ws.set_column(0, 0, 18)
        for c in range(1, len(df_cat.columns)):
            ws.set_column(c, c, 18, fmt_money)

        # Безубыточность
        ws = writer.sheets["Безубыточность"]
        _write_headers(ws, df_be.columns, fmt_head)
        ws.set_column(0, 0, 18)
        for c in range(1, len(df_be.columns)):
            ws.set_column(c, c, 16, fmt_money)

        start_cafe = len(df_be) + 3
        ws.merge_range(start_cafe - 1, 0, start_cafe - 1, 4,
                       "ОБЩАЯ ТОЧКА БЕЗУБЫТОЧНОСТИ КАФЕ",
                       fmt_title)
        _write_headers(ws, df_be_cafe.columns, fmt_head, row=start_cafe)
        for c in range(len(df_be_cafe.columns)):
            ws.set_column(c, c, 18)

    return out_path
