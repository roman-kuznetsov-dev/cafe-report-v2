"""
Веб-версия программы кафе на Streamlit.

Использует те же модули, что и десктопная версия:
    - cafe_loader     — загрузка данных
    - cafe_analysis   — анализ (прибыль, вердикт, безубыточность)
    - cafe_exporter   — экспорт в Excel
    - cafe_charts     — генерация графиков
    - cafe_optimizer  — оптимизация цен

Запуск локально:
    streamlit run app.py

Деплой:
    Streamlit Cloud — см. docs/DEPLOY.md
"""

import os
import tempfile

import pandas as pd
import streamlit as st

from cafe_analysis import Analysis
from cafe_exporter import export_to_excel
from cafe_loader import load_all
from cafe_optimizer import optimize_all

st.set_page_config(
    page_title="Кафе — расчёт прибыли",
    page_icon="☕",
    layout="wide",
)


# ============================================================
#  ЗАГОЛОВОК
# ============================================================
st.title("☕ Кафе — расчёт прибыли")
st.markdown(
    "Загрузите файл `cafe_data.xlsx` — программа рассчитает прибыль, "
    "проверит обоснованность повышения цен и предложит оптимальные цены."
)


# ============================================================
#  БОКОВАЯ ПАНЕЛЬ — НАСТРОЙКИ
# ============================================================
with st.sidebar:
    st.header("Настройки")

    elasticity = st.slider(
        "Эластичность спроса",
        min_value=0.0, max_value=2.0, value=0.8, step=0.1,
        help="0 — спрос не реагирует на цену; 1 — пропорционально."
    )

    # Сохраняем в cafe_model, чтобы модули использовали это значение
    import cafe_model
    cafe_model.ELASTICITY = elasticity

    st.markdown("---")
    st.caption(
        "Загрузите файл `cafe_data.xlsx` с 4 листами: "
        "Товары, Периоды, Ежедневные данные, Сезонная история."
    )


# ============================================================
#  ЗАГРУЗКА ФАЙЛА
# ============================================================
uploaded = st.file_uploader(
    "Выберите файл с данными кафе",
    type=["xlsx", "xls"],
    help="Файл должен быть в формате cafe_data.xlsx"
)

if not uploaded:
    st.info("👆 Загрузите файл, чтобы увидеть отчёт.")
    st.stop()


# ============================================================
#  СОХРАНЯЕМ ФАЙЛ ВО ВРЕМЕННУЮ ПАПКУ
# ============================================================
with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
    tmp.write(uploaded.read())
    tmp_path = tmp.name


# ============================================================
#  ЗАГРУЗКА ДАННЫХ И АНАЛИЗ
# ============================================================
try:
    data = load_all(tmp_path)
    analysis = Analysis(
        data.products, data.periods, data.daily, data.season_records)
except Exception as e:
    st.error(f"Ошибка при чтении файла: {e}")
    os.unlink(tmp_path)
    st.stop()

os.unlink(tmp_path)


# ============================================================
#  ВЕРДИКТ И ПРЕДУПРЕЖДЕНИЯ
# ============================================================
verdict = analysis.verdict

if verdict.score == 5:
    st.success(f"**Вердикт: {verdict.text}** ({verdict.score}/5)")
elif verdict.score >= 3:
    st.warning(f"**Вердикт: {verdict.text}** ({verdict.score}/5)")
else:
    st.error(f"**Вердикт: {verdict.text}** ({verdict.score}/5)")

# Предупреждения о периодах
period_warnings = analysis.period_warnings()
if period_warnings:
    with st.expander(f"⚠ Предупреждений о периодах: {len(period_warnings)}"):
        for w in period_warnings:
            st.warning(w)


# ============================================================
#  ВКЛАДКИ
# ============================================================
tab_summary, tab_just, tab_stock, tab_flow, tab_be, tab_whatif = st.tabs([
    "📊 Сводка",
    "✅ Обоснованность",
    "🚚 Закупки",
    "👥 Поток гостей",
    "📉 Безубыточность",
    "💡 Что-если",
])


# ============================================================
#  ВКЛАДКА 1. СВОДКА
# ============================================================
with tab_summary:
    rows = []
    for s in analysis.summaries:
        rows.append({
            "Товар": s.name,
            "Категория": s.category,
            "Выручка 1": round(s.revenue_1, 2),
            "Выручка 2": round(s.revenue_2, 2),
            "Прибыль 1": round(s.profit_1, 2),
            "Прибыль 2": round(s.profit_2, 2),
            "Δ Прибыль": round(s.delta_profit(), 2),
            "Δ Прибыль %": round(s.delta_profit_pct(), 1),
            "Наценка 1 %": round(s.markup_1, 1),
            "Наценка 2 %": round(s.markup_2, 1),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Базовая прибыль",
                f"{analysis.total_profit(1):,.0f} ₽".replace(",", " "))
    col2.metric("Текущая прибыль",
                f"{analysis.total_profit(2):,.0f} ₽".replace(",", " "))
    delta = analysis.total_profit_delta()
    col3.metric("Δ Прибыль",
                f"{delta:+,.0f} ₽".replace(",", " "),
                f"{analysis.total_profit_delta_pct():+.1f}%")


# ============================================================
#  ВКЛАДКА 2. ОБОСНОВАННОСТЬ
# ============================================================
with tab_just:
    rows = []
    for c in analysis.checks:
        rows.append({
            "Товар": c.product,
            "Критерий": c.criterion,
            "Было": round(c.before, 2),
            "Стало": round(c.after, 2),
            "Ед.": c.unit,
            "Результат": "✅ OK" if c.ok else "❌ НЕТ",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ============================================================
#  ВКЛАДКА 3. ЗАКУПКИ
# ============================================================
with tab_stock:
    rows = []
    for p in analysis.products:
        rows.append({
            "Товар": p.name,
            "Остаток нач. 1": p.stock_start_1,
            "Закуплено 1": p.purchase_qty_1,
            "Продано 1": p.qty_1,
            "Остаток кон. 1": p.stock_end(1),
            "Стоимость 1": round(p.stock_value(1), 2),
            "Остаток нач. 2": p.stock_start_2,
            "Закуплено 2": p.purchase_qty_2,
            "Продано 2": p.qty_2,
            "Остаток кон. 2": p.stock_end(2),
            "Стоимость 2": round(p.stock_value(2), 2),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ============================================================
#  ВКЛАДКА 4. ПОТОК ГОСТЕЙ
# ============================================================
with tab_flow:
    rows = []
    for r in analysis.flow_summary():
        rows.append({
            "Товар": r["Товар"],
            "Конверсия 1": round(r["Конв_1"], 4),
            "Конверсия 2": round(r["Конв_2"], 4),
            "Δ Конверсия %": round(r["ΔКонв_%"], 2),
            "Влияние потока": round(r["Эффект_потока"], 2),
            "Влияние конверсии": round(r["Эффект_конверсии"], 2),
            "Δ Продано": r["ΔПродано"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ============================================================
#  ВКЛАДКА 5. БЕЗУБЫТОЧНОСТЬ
# ============================================================
with tab_be:
    rows = []
    for r in analysis.breakeven_simple(2):
        rows.append({
            "Товар": r["Товар"],
            "Прибыль/шт": r["Прибыль_шт"],
            "ТБ (шт)": r["ТБ_шт"],
            "Продано": r["Продано"],
            "Запас (шт)": r["Запас_шт"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.subheader("Общая точка безубыточности кафе")
    cafe_total = pd.DataFrame([
        analysis.breakeven_cafe_total(1),
        analysis.breakeven_cafe_total(2),
    ])
    st.dataframe(cafe_total, use_container_width=True)


# ============================================================
#  ВКЛАДКА 6. ЧТО-ЕСЛИ (ОПТИМИЗАТОР)
# ============================================================
with tab_whatif:
    st.markdown("**Меняйте цены товаров и смотрите прогноз прибыли.**")

    if st.button("💡 Найти оптимум для всех товаров"):
        st.session_state["optimize"] = True

    # Оптимизация
    if st.session_state.get("optimize"):
        results = optimize_all(
            analysis.products, period=2, elasticity=elasticity)
        optimal_prices = {r.product: r.optimal_price for r in results}
        st.session_state["optimal_prices"] = optimal_prices
        st.session_state["optimize"] = False

    optimal_prices = st.session_state.get("optimal_prices", {})

    # Формируем таблицу прогноза
    rows = []
    for p in analysis.products:
        base_price = p.sale_price_2
        new_price = optimal_prices.get(p.name, base_price)
        base_qty = p.qty_2
        purchase = p.purchase_price_2

        delta_pct = (new_price - base_price) / base_price * 100 \
            if base_price else 0
        new_qty = base_qty * (1 - elasticity * delta_pct / 100)
        new_qty = max(0, new_qty)

        base_profit = (base_price - purchase) * base_qty
        new_profit = (new_price - purchase) * new_qty

        rows.append({
            "Товар": p.name,
            "Текущая цена": round(base_price, 2),
            "Новая цена": round(new_price, 2),
            "Δ %": round(delta_pct, 1),
            "Продажа (было → стало)": f"{base_qty} → {int(round(new_qty))}",
            "Прибыль (было → стало)":
                f"{base_profit:.0f} → {new_profit:.0f}",
            "Δ Прибыль": round(new_profit - base_profit, 2),
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # Суммарная прибыль
    base_total = sum(
        (p.sale_price_2 - p.purchase_price_2) * p.qty_2
        for p in analysis.products)
    new_total = sum(
        (optimal_prices.get(p.name, p.sale_price_2) - p.purchase_price_2)
        * max(0, p.qty_2 * (1 - elasticity *
                            ((optimal_prices.get(p.name, p.sale_price_2)
                              - p.sale_price_2) / p.sale_price_2 * 100)
                            / 100))
        for p in analysis.products)

    col1, col2, col3 = st.columns(3)
    col1.metric("Базовая прибыль",
                f"{base_total:,.0f} ₽".replace(",", " "))
    col2.metric("Прогноз прибыли",
                f"{new_total:,.0f} ₽".replace(",", " "))
    col3.metric("Δ Прибыль",
                f"{new_total - base_total:+,.0f} ₽".replace(",", " "),
                f"{(new_total - base_total) / base_total * 100:+.1f}%"
                if base_total else "")


# ============================================================
#  ЭКСПОРТ В EXCEL
# ============================================================
st.markdown("---")
st.subheader("📥 Скачать отчёт")

if st.button("Подготовить отчёт Excel"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        out_path = tmp.name

    try:
        export_to_excel(analysis, out_path)
        with open(out_path, "rb") as f:
            data_bytes = f.read()

        st.download_button(
            label="💾 Скачать cafe_report.xlsx",
            data=data_bytes,
            file_name="cafe_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        st.error(f"Ошибка при экспорте: {e}")
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)
