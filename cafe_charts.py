"""
Генерация графиков для отчёта кафе (версия 2.0).

Создаёт PNG-файлы:
  1. chart_prices.png       — динамика цен (закупка vs продажа)
  2. chart_profit.png       — прибыль по товарам за 2 периода
  3. chart_demand.png       — падение спроса по товарам
  4. chart_guests.png       — поток гостей по периодам
  5. chart_weekday.png      — будни vs выходные (если есть данные)
  6. chart_seasonality.png  — коэффициенты сезонности (если есть история)
  7. chart_breakeven.png    — точка безубыточности vs факт
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from cafe_analysis import Analysis

plt.rcParams["font.family"] = "DejaVu Sans"


def _save(fig, out_dir: str, name: str):
    path = os.path.join(out_dir, name)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _short_labels(names, max_len=14):
    return [n if len(n) <= max_len else n[:max_len - 1] + "…"
            for n in names]


# ============================================================
#  1. ЦЕНЫ
# ============================================================
def _chart_prices(a: Analysis, out_dir: str):
    products = a.products
    names = _short_labels([p.name for p in products])
    x = list(range(len(names)))

    fig, ax = plt.subplots(figsize=(max(10, len(names) * 0.5), 5))
    w = 0.2
    ax.bar([i - 1.5 * w for i in x],
           [p.purchase_price_1 for p in products],
           width=w, label="Закупка 1", color="#8ecae6")
    ax.bar([i - 0.5 * w for i in x],
           [p.purchase_price_2 for p in products],
           width=w, label="Закупка 2", color="#219ebc")
    ax.bar([i + 0.5 * w for i in x],
           [p.sale_price_1 for p in products],
           width=w, label="Цена кафе 1", color="#fb8500")
    ax.bar([i + 1.5 * w for i in x],
           [p.sale_price_2 for p in products],
           width=w, label="Цена кафе 2", color="#e63946")

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_ylabel("Цена, ₽")
    ax.set_title("Динамика цен: закупка и продажа")
    ax.legend()
    _save(fig, out_dir, "chart_prices.png")


# ============================================================
#  2. ПРИБЫЛЬ
# ============================================================
def _chart_profit(a: Analysis, out_dir: str):
    products = a.products
    names = _short_labels([p.name for p in products])
    x = list(range(len(names)))

    fig, ax = plt.subplots(figsize=(max(10, len(names) * 0.5), 5))
    ax.bar([i - 0.2 for i in x],
           [p.profit(1) for p in products],
           width=0.4, label="Прибыль 1", color="#90be6d")
    ax.bar([i + 0.2 for i in x],
           [p.profit(2) for p in products],
           width=0.4, label="Прибыль 2", color="#43aa8b")

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_ylabel("Прибыль, ₽")
    ax.set_title("Прибыль по товарам: до и после повышения цен")
    ax.legend()
    _save(fig, out_dir, "chart_profit.png")


# ============================================================
#  3. ПАДЕНИЕ СПРОСА
# ============================================================
def _chart_demand(a: Analysis, out_dir: str):
    products = a.products
    names = _short_labels([p.name for p in products])
    drops = [p.demand_drop_pct() for p in products]

    fig, ax = plt.subplots(figsize=(max(10, len(names) * 0.5), 5))
    colors = ["#43aa8b" if d <= 30 else "#e63946" for d in drops]
    ax.bar(names, drops, color=colors)
    ax.axhline(30, color="red", linestyle="--", label="Порог 30%")
    ax.set_ylabel("Падение продаж, %")
    ax.set_title("Падение спроса по товарам")
    ax.tick_params(axis="x", rotation=30)
    ax.legend()
    _save(fig, out_dir, "chart_demand.png")


# ============================================================
#  4. ПОТОК ГОСТЕЙ
# ============================================================
def _chart_guests(a: Analysis, out_dir: str):
    fig, ax = plt.subplots(figsize=(8, 5))
    labels = [a.p1.name, a.p2.name]
    values = [a.p1.guests, a.p2.guests]
    colors = ["#457b9d", "#1d3557"]

    bars = ax.bar(labels, values, color=colors, width=0.5)
    ymax = max(values) if values else 1
    for b, v in zip(bars, values, strict=True):
        ax.text(b.get_x() + b.get_width() / 2, v + ymax * 0.02,
                f"{v:,}".replace(",", " "),
                ha="center", fontsize=11)

    if values[0]:
        delta = (values[1] - values[0]) / values[0] * 100
        ax.set_title(f"Поток гостей за период\nИзменение: {delta:+.1f}%")
    else:
        ax.set_title("Поток гостей за период")

    ax.set_ylabel("Человек")
    _save(fig, out_dir, "chart_guests.png")


# ============================================================
#  5. БУДНИ И ВЫХОДНЫЕ
# ============================================================
def _chart_weekday(a: Analysis, out_dir: str):
    if not a.has_daily_data():
        return
    w1 = a.weekday_weekend_for_period(1)
    w2 = a.weekday_weekend_for_period(2)

    # Собираем данные только по периодам, где есть daily
    labels = []
    values = []
    colors = []

    if w1:
        labels.append(f"{a.p1.name}\nбудни")
        values.append(w1["guests"]["будни"])
        colors.append("#a8dadc")
        labels.append(f"{a.p1.name}\nвыходные")
        values.append(w1["guests"]["выходные"])
        colors.append("#457b9d")

    if w2:
        labels.append(f"{a.p2.name}\nбудни")
        values.append(w2["guests"]["будни"])
        colors.append("#a8dadc")
        labels.append(f"{a.p2.name}\nвыходные")
        values.append(w2["guests"]["выходные"])
        colors.append("#1d3557")

    if not values:
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    x = list(range(len(values)))
    bars = ax.bar(x, values, color=colors, width=0.6)
    ymax = max(values) if values else 1
    for b, v in zip(bars, values, strict=True):
        ax.text(b.get_x() + b.get_width() / 2, v + ymax * 0.02,
                f"{v:,.0f}".replace(",", " "),
                ha="center", fontsize=10)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Среднее число гостей в день")
    ax.set_title("Будни vs выходные")
    _save(fig, out_dir, "chart_weekday.png")


# ============================================================
#  6. СЕЗОННОСТЬ
# ============================================================
def _chart_seasonality(a: Analysis, out_dir: str):
    if not a.has_season_history():
        return
    coef = a.season_coefficients()
    if not coef:
        return

    products = list(coef.keys())[:10]
    seasons = ["зима", "весна", "лето", "осень"]
    x = list(range(len(products)))
    w = 0.2
    colors = ["#1d3557", "#457b9d", "#a8dadc", "#e63946"]

    fig, ax = plt.subplots(figsize=(max(10, len(products) * 0.8), 5))
    for i, s in enumerate(seasons):
        values = [coef[p].get(s, 0) for p in products]
        ax.bar([j + (i - 1.5) * w for j in x], values,
               width=w, label=s, color=colors[i])

    ax.axhline(1.0, color="gray", linestyle=":", label="Средний уровень (1.0)")
    ax.set_xticks(x)
    ax.set_xticklabels(_short_labels(products, 12), rotation=30, ha="right")
    ax.set_ylabel("Коэффициент сезонности")
    ax.set_title("Сезонность по товарам (коэффициент)")
    ax.legend(loc="upper right")
    _save(fig, out_dir, "chart_seasonality.png")


# ============================================================
#  7. ТОЧКА БЕЗУБЫТОЧНОСТИ
# ============================================================
def _chart_breakeven(a: Analysis, out_dir: str):
    be = a.breakeven_simple(2)
    valid = [r for r in be if isinstance(r["ТБ_шт"], (int, float))]
    if not valid:
        return

    names = _short_labels([r["Товар"] for r in valid])
    tb = [r["ТБ_шт"] for r in valid]
    sold = [r["Продано"] for r in valid]

    x = list(range(len(names)))
    fig, ax = plt.subplots(figsize=(max(10, len(names) * 0.7), 5))
    ax.bar([i - 0.2 for i in x], tb, width=0.4,
           label="ТБ (нужно продать)", color="#f4a261")
    ax.bar([i + 0.2 for i in x], sold, width=0.4,
           label="Продано фактически", color="#2a9d8f")

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_ylabel("Штук за период")
    ax.set_title(f"Точка безубыточности vs Факт ({a.p2.name})")
    ax.legend()
    _save(fig, out_dir, "chart_breakeven.png")


# ============================================================
#  ГЛАВНАЯ ФУНКЦИЯ
# ============================================================
def make_charts(a: Analysis, out_dir: str = "."):
    """Создаёт все графики. Возвращает список созданных файлов."""
    os.makedirs(out_dir, exist_ok=True)
    created = []

    _chart_prices(a, out_dir)
    created.append(os.path.join(out_dir, "chart_prices.png"))

    _chart_profit(a, out_dir)
    created.append(os.path.join(out_dir, "chart_profit.png"))

    _chart_demand(a, out_dir)
    created.append(os.path.join(out_dir, "chart_demand.png"))

    _chart_guests(a, out_dir)
    created.append(os.path.join(out_dir, "chart_guests.png"))

    _chart_weekday(a, out_dir)
    if os.path.exists(os.path.join(out_dir, "chart_weekday.png")):
        created.append(os.path.join(out_dir, "chart_weekday.png"))

    _chart_seasonality(a, out_dir)
    if os.path.exists(os.path.join(out_dir, "chart_seasonality.png")):
        created.append(os.path.join(out_dir, "chart_seasonality.png"))

    _chart_breakeven(a, out_dir)
    if os.path.exists(os.path.join(out_dir, "chart_breakeven.png")):
        created.append(os.path.join(out_dir, "chart_breakeven.png"))

    return created
