"""
Модель расчётов кафе (версия 2.0).

Здесь:
  - Product            — товар (цены, продажи)
  - Purchase           — закупки (закупили, продали, остаток)
  - Period             — период (даты, сезон, издержки, гости)
  - Flow               — конверсия, разложение продаж по факторам
  - Seasonality        — коэффициенты сезонности, прогноз
  - WeekdayWeekend     — будни/выходные
  - Analysis           — общий анализ (объединяет всё)
  - load_from_excel    — загрузка всех данных

Этот модуль НЕ имеет GUI. Его использует cafe_gui.py.
"""

from dataclasses import dataclass
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "DejaVu Sans"


# ============================================================
#  НАСТРОЙКИ
# ============================================================
ELASTICITY = 0.8           # эластичность спроса (для прогноза)
MAX_DEMAND_DROP_PCT = 30   # порог падения спроса
MIN_PROFIT_GROWTH = 0      # минимальный рост прибыли, %
FORECAST_STEPS = [-20, -10, -5, 0, 5, 10, 15, 20, 30]

SEASONS = ["зима", "весна", "лето", "осень"]


# ============================================================
#  ТОВАР
# ============================================================
@dataclass
class Product:
    name: str
    category: str
    purchase_price_1: float
    purchase_price_2: float
    sale_price_1: float
    sale_price_2: float
    qty_1: int
    qty_2: int
    # новое в v2.0:
    purchase_qty_1: int = 0
    purchase_qty_2: int = 0
    stock_start_1: int = 0
    stock_start_2: int = 0

    # ---------- базовые ----------
    def revenue(self, period: int) -> float:
        price = self.sale_price_1 if period == 1 else self.sale_price_2
        qty = self.qty_1 if period == 1 else self.qty_2
        return price * qty

    def cost_of_goods_sold(self, period: int) -> float:
        """Себестоимость проданного (управленческий учёт)."""
        price = self.purchase_price_1 if period == 1 else self.purchase_price_2
        qty = self.qty_1 if period == 1 else self.qty_2
        return price * qty

    def purchase_expense(self, period: int) -> float:
        """Денег ушло на закупку (кассовый учёт)."""
        price = self.purchase_price_1 if period == 1 else self.purchase_price_2
        qty = self.purchase_qty_1 if period == 1 else self.purchase_qty_2
        return price * qty

    def profit(self, period: int) -> float:
        """Управленческая прибыль (выручка − себестоимость проданного)."""
        return self.revenue(period) - self.cost_of_goods_sold(period)

    def cash_flow(self, period: int) -> float:
        """Денежный поток (выручка − расходы на закупку)."""
        return self.revenue(period) - self.purchase_expense(period)

    # ---------- остатки ----------
    def stock_end(self, period: int) -> int:
        """Остаток на конец периода."""
        start = self.stock_start_1 if period == 1 else self.stock_start_2
        purchased = self.purchase_qty_1 if period == 1 else self.purchase_qty_2
        sold = self.qty_1 if period == 1 else self.qty_2
        return start + purchased - sold

    def stock_value(self, period: int) -> float:
        """Стоимость остатка в рублях (по закупочной цене)."""
        price = self.purchase_price_1 if period == 1 else self.purchase_price_2
        return price * self.stock_end(period)

    def stock_error(self, period: int) -> str | None:
        """Проверка баланса. Возвращает текст ошибки или None."""
        end = self.stock_end(period)
        if end < 0:
            return (f"Товар «{self.name}», период {period}: "
                    f"отрицательный остаток ({end} шт). "
                    f"Продано больше, чем было на складе.")
        return None

    def stock_mismatch(self) -> str | None:
        """Остаток конца 1 периода должен совпасть с началом 2."""
        end1 = self.stock_end(1)
        start2 = self.stock_start_2
        if end1 != start2:
            return (f"Товар «{self.name}»: остаток на конец 1 периода "
                    f"({end1}) ≠ остаток на начало 2 периода ({start2}). "
                    f"Проверьте данные.")
        return None

    # ---------- наценка/прибыль на единицу ----------
    def unit_profit(self, period: int) -> float:
        sale = self.sale_price_1 if period == 1 else self.sale_price_2
        buy = self.purchase_price_1 if period == 1 else self.purchase_price_2
        return sale - buy

    def markup_pct(self, period: int) -> float:
        buy = self.purchase_price_1 if period == 1 else self.purchase_price_2
        return self.unit_profit(period) / buy * 100 if buy else 0

    def demand_drop_pct(self) -> float:
        return (self.qty_1 - self.qty_2) / self.qty_1 * 100 if self.qty_1 else 0

    def price_growth_buy_pct(self) -> float:
        return ((self.purchase_price_2 - self.purchase_price_1)
                / self.purchase_price_1 * 100) if self.purchase_price_1 else 0

    def price_growth_sale_pct(self) -> float:
        return ((self.sale_price_2 - self.sale_price_1)
                / self.sale_price_1 * 100) if self.sale_price_1 else 0
                # ============================================================
#  ПЕРИОД
# ============================================================
@dataclass
class Period:
    name: str                       # "Январь 2026"
    date_start: date                # 2026-01-01
    date_end: date                  # 2026-01-31
    season: str                     # зима/весна/лето/осень
    fixed_costs: float              # постоянные издержки, ₽
    guests: int = 0                 # всего гостей за период

    def days_count(self) -> int:
        return (self.date_end - self.date_start).days + 1

    def guests_per_day(self) -> float:
        return self.guests / self.days_count() if self.days_count() else 0

    def validate(self) -> str | None:
        if self.season not in SEASONS:
            return (f"Период «{self.name}»: сезон «{self.season}» "
                    f"не из списка {SEASONS}")
        if self.date_end < self.date_start:
            return f"Период «{self.name}»: дата конца раньше начала"
        return None
        # ============================================================
#  ЕЖЕДНЕВНЫЕ ДАННЫЕ
# ============================================================
@dataclass
class DailyRow:
    """Одна строка: один день, все товары."""
    date: date
    guests: int
    sales: dict[str, int]     # {имя_товара: продано}

    def weekday(self) -> int:
        """0 = понедельник, 6 = воскресенье."""
        return self.date.weekday()

    def is_weekend(self) -> bool:
        return self.weekday() >= 5

    def is_weekday(self) -> bool:
        return not self.is_weekend()


class DailyData:
    """Все ежедневные данные за период."""

    def __init__(self, rows: list[DailyRow]):
        self.rows = sorted(rows, key=lambda r: r.date)

    def __len__(self):
        return len(self.rows)

    def __iter__(self):
        return iter(self.rows)

    def filter_period(self, p: "Period") -> "DailyData":
        """Оставляет строки внутри периода."""
        return DailyData([r for r in self.rows
                          if p.date_start <= r.date <= p.date_end])

    def guests_total(self) -> int:
        return sum(r.guests for r in self.rows)

    def sales_total(self, product: str) -> int:
        return sum(r.sales.get(product, 0) for r in self.rows)

    def by_weekday_type(self) -> dict[str, "DailyData"]:
        """Разбить на будни и выходные."""
        weekdays = [r for r in self.rows if r.is_weekday()]
        weekends = [r for r in self.rows if r.is_weekend()]
        return {
            "будни": DailyData(weekdays),
            "выходные": DailyData(weekends),
        }

    def by_day_of_week(self) -> dict[str, "DailyData"]:
        """Разбить по дням недели (пн, вт, …)."""
        names = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
        result = {n: [] for n in names}
        for r in self.rows:
            result[names[r.weekday()]].append(r)
        return {k: DailyData(v) for k, v in result.items()}
        # ============================================================
#  ПОТОК ГОСТЕЙ
# ============================================================
class Flow:
    """
    Конверсия и разложение изменения продаж на:
      - эффект потока (гостей стало меньше/больше);
      - эффект конверсии (на одного гостя стали покупать чаще/реже).
    """

    def __init__(self, products: list[Product], periods: list[Period]):
        self.products = products
        self.p1, self.p2 = periods[0], periods[1]

    def conversion(self, product: Product, period: int) -> float:
        """Сколько штук товара в среднем купил один гость."""
        guests = self.p1.guests if period == 1 else self.p2.guests
        qty = product.qty_1 if period == 1 else product.qty_2
        return qty / guests if guests else 0

    def conversion_change_pct(self, product: Product) -> float:
        c1 = self.conversion(product, 1)
        c2 = self.conversion(product, 2)
        return (c2 - c1) / c1 * 100 if c1 else 0

    def decompose(self, product: Product) -> dict[str, float]:
        """
        Разложение Δпродаж на влияние потока и конверсии.
        """
        g1, g2 = self.p1.guests, self.p2.guests
        c1 = self.conversion(product, 1)
        c2 = self.conversion(product, 2)

        flow_effect = (g2 - g1) * c1
        conv_effect = g2 * (c2 - c1)
        total = product.qty_2 - product.qty_1

        return {
            "продано_1": product.qty_1,
            "продано_2": product.qty_2,
            "изменение": total,
            "эффект_потока": flow_effect,
            "эффект_конверсии": conv_effect,
            "проверка": flow_effect + conv_effect,
        }
        # ============================================================
#  СЕЗОННОСТЬ
# ============================================================
@dataclass
class SeasonRecord:
    season: str
    product: str
    avg_sales_per_day: float
    avg_flow_per_day: float


class Seasonality:
    """
    Коэффициенты сезонности по товарам + прогноз продаж.
    """

    def __init__(self, records: list[SeasonRecord]):
        self.records = records

    def has_history(self) -> bool:
        return len(self.records) > 0

    def average_sales_all_seasons(self, product: str) -> float:
        """Средние продажи товара за день по всем сезонам."""
        vals = [r.avg_sales_per_day for r in self.records
                if r.product == product]
        return sum(vals) / len(vals) if vals else 0

    def coefficient(self, product: str, season: str) -> float:
        """
        Коэффициент сезонности:
          Коэф = средние_продажи(товар, сезон) / средние(товар, все сезоны)
        """
        avg = self.average_sales_all_seasons(product)
        if not avg:
            return 0
        for r in self.records:
            if r.product == product and r.season == season:
                return r.avg_sales_per_day / avg
        return 0

    def all_coefficients(self) -> dict[str, dict[str, float]]:
        """{товар: {сезон: коэффициент}}."""
        products = sorted({r.product for r in self.records})
        result = {}
        for p in products:
            result[p] = {s: self.coefficient(p, s) for s in SEASONS}
        return result

    def avg_flow(self, season: str) -> float:
        """Средний поток в день для сезона."""
        vals = [r.avg_flow_per_day for r in self.records
                if r.season == season]
        return sum(vals) / len(vals) if vals else 0

    def forecast_sales(self, product: str, season: str,
                       conversion: float) -> float:
        """
        Прогноз продаж товара в день на будущий период:
          поток(сезон) × конверсия(товар) × коэффициент_сезонности
        """
        flow = self.avg_flow(season)
        coef = self.coefficient(product, season)
        return flow * conversion * coef if coef else 0
        # ============================================================
#  БУДНИ И ВЫХОДНЫЕ
# ============================================================
class WeekdayWeekend:
    """
    Анализ будней и выходных по ежедневным данным.
    """

    def __init__(self, daily: DailyData):
        self.daily = daily

    def has_data(self) -> bool:
        return len(self.daily) > 0

    def avg_per_day(self, group: DailyData,
                    product: str | None = None) -> float:
        """Среднее значение в день: либо гости, либо продажи товара."""
        if len(group) == 0:
            return 0
        if product is None:
            return group.guests_total() / len(group)
        return group.sales_total(product) / len(group)

    def summary_for_product(self, product: str) -> dict[str, float]:
        parts = self.daily.by_weekday_type()
        wd = self.avg_per_day(parts["будни"], product)
        we = self.avg_per_day(parts["выходные"], product)
        return {
            "будни": wd,
            "выходные": we,
            "индекс_вых": we / wd if wd else 0,
        }

    def summary_guests(self) -> dict[str, float]:
        parts = self.daily.by_weekday_type()
        wd = self.avg_per_day(parts["будни"])
        we = self.avg_per_day(parts["выходные"])
        return {
            "будни": wd,
            "выходные": we,
            "индекс_вых": we / wd if wd else 0,
        }

    def by_day_of_week(self, product: str | None = None) -> dict[str, float]:
        """Средние по каждому дню недели (пн…вс)."""
        parts = self.daily.by_day_of_week()
        return {name: self.avg_per_day(group, product)
                for name, group in parts.items()}
