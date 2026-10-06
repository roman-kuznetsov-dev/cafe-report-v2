"""
Класс Analysis — общий анализ кафе (версия 2.0).

Объединяет:
  - базовые метрики (прибыль, наценка, денежный поток, остатки);
  - поток гостей и разложение продаж;
  - сезонность и прогноз;
  - будни/выходные;
  - проверку 5 критериев обоснованности;
  - итоговый вердикт.

Создаётся из cafe_loader.LoadedData.
"""

from dataclasses import dataclass
from typing import List, Dict

from cafe_model import (
    Product, Period, DailyData,
    Flow, Seasonality, SeasonRecord, WeekdayWeekend,
    MAX_DEMAND_DROP_PCT, MIN_PROFIT_GROWTH,
)


# ============================================================
#  СТРУКТУРЫ ОТЧЁТОВ
# ============================================================
@dataclass
class ProductSummary:
    """Сводка по одному товару."""
    name: str
    category: str
    revenue_1: float
    revenue_2: float
    profit_1: float
    profit_2: float
    cash_flow_1: float
    cash_flow_2: float
    markup_1: float
    markup_2: float
    stock_end_1: int
    stock_end_2: int
    stock_value_1: float
    stock_value_2: float

    def delta_profit(self) -> float:
        return self.profit_2 - self.profit_1

    def delta_profit_pct(self) -> float:
        return (self.profit_2 - self.profit_1) / self.profit_1 * 100 \
            if self.profit_1 else 0


@dataclass
class CheckResult:
    """Результат одного критерия по одному товару."""
    product: str
    criterion: str
    before: float
    after: float
    unit: str
    ok: bool


@dataclass
class Verdict:
    """Итоговый вердикт."""
    text: str
    score: int
    total: int
    checks: Dict[str, bool]


# ============================================================
#  ГЛАВНЫЙ КЛАСС
# ============================================================
class Analysis:
    """Общий анализ по одному объекту (загрузка → расчёты)."""

    def __init__(self,
                 products: List[Product],
                 periods: List[Period],
                 daily: DailyData,
                 season_records: List[SeasonRecord]):
        self.products = products
        self.periods = periods
        self.p1, self.p2 = periods[0], periods[1]
        self.daily = daily
        self.season_records = season_records

        # Вспомогательные объекты
        self.flow = Flow(products, periods)
        self.seasonality = Seasonality(season_records)
        self.daily_p1 = (daily.filter_period(self.p1)
                         if len(daily) else daily)
        self.daily_p2 = (daily.filter_period(self.p2)
                         if len(daily) else daily)

        # Считаем один раз
        self.summaries = self._build_summaries()
        self.checks = self._run_checks()
        self.verdict = self._make_verdict()

    # --------------------------------------------------------
    #  СВОДКА ПО ТОВАРАМ
    # --------------------------------------------------------
    def _build_summaries(self) -> List[ProductSummary]:
        result = []
        for p in self.products:
            result.append(ProductSummary(
                name=p.name,
                category=p.category,
                revenue_1=p.revenue(1),
                revenue_2=p.revenue(2),
                profit_1=p.profit(1),
                profit_2=p.profit(2),
                cash_flow_1=p.cash_flow(1),
                cash_flow_2=p.cash_flow(2),
                markup_1=p.markup_pct(1),
                markup_2=p.markup_pct(2),
                stock_end_1=p.stock_end(1),
                stock_end_2=p.stock_end(2),
                stock_value_1=p.stock_value(1),
                stock_value_2=p.stock_value(2),
            ))
        return result

    # --------------------------------------------------------
    #  ИТОГИ ПО ВСЕМ ТОВАРАМ
    # --------------------------------------------------------
    def total_revenue(self, period: int) -> float:
        return sum(p.revenue(period) for p in self.products)

    def total_profit(self, period: int) -> float:
        return sum(p.profit(period) for p in self.products)

    def total_cash_flow(self, period: int) -> float:
        return sum(p.cash_flow(period) for p in self.products)

    def total_stock_value(self, period: int) -> float:
        return sum(p.stock_value(period) for p in self.products)

    def total_profit_delta(self) -> float:
        return self.total_profit(2) - self.total_profit(1)

    def total_profit_delta_pct(self) -> float:
        t1 = self.total_profit(1)
        return (self.total_profit(2) - t1) / t1 * 100 if t1 else 0

    # --------------------------------------------------------
    #  ПОТОК ГОСТЕЙ
    # --------------------------------------------------------
    def flow_summary(self) -> List[Dict]:
        """Конверсия и разложение продаж по каждому товару."""
        result = []
        for p in self.products:
            d = self.flow.decompose(p)
            result.append({
                "Товар": p.name,
                "Конв_1": self.flow.conversion(p, 1),
                "Конв_2": self.flow.conversion(p, 2),
                "ΔКонв_%": self.flow.conversion_change_pct(p),
                "Эффект_потока": d["эффект_потока"],
                "Эффект_конверсии": d["эффект_конверсии"],
                "ΔПродано": d["изменение"],
            })
        return result

    def guests_change_pct(self) -> float:
        g1, g2 = self.p1.guests, self.p2.guests
        return (g2 - g1) / g1 * 100 if g1 else 0

    # --------------------------------------------------------
    #  СЕЗОННОСТЬ
    # --------------------------------------------------------
    def has_season_history(self) -> bool:
        return self.seasonality.has_history()

    def season_coefficients(self) -> Dict[str, Dict[str, float]]:
        return self.seasonality.all_coefficients()

    def season_current(self) -> str:
        return self.p2.season

    def season_forecast_per_product(self) -> List[Dict]:
        if not self.has_season_history():
            return []
        result = []
        for p in self.products:
            conversion = self.flow.conversion(p, 2)
            forecast_daily = self.seasonality.forecast_sales(
                p.name, self.p2.season, conversion)
            forecast_period = forecast_daily * self.p2.days_count()
            result.append({
                "Товар": p.name,
                "Конверсия": conversion,
                "Прогноз_в_день": forecast_daily,
                "Прогноз_за_период": forecast_period,
            })
        return result

    # --------------------------------------------------------
    #  БУДНИ / ВЫХОДНЫЕ
    # --------------------------------------------------------
    def has_daily_data(self) -> bool:
        return len(self.daily) > 0

    def weekday_weekend_for_period(self, period_num: int) -> Dict:
        group = self.daily_p1 if period_num == 1 else self.daily_p2
        if len(group) == 0:
            return {}
        w = WeekdayWeekend(group)
        products_result = {}
        for p in self.products:
            products_result[p.name] = w.summary_for_product(p.name)
        return {
            "guests": w.summary_guests(),
            "products": products_result,
        }

    def weekday_by_day_of_week(self, period_num: int) -> Dict[str, float]:
        group = self.daily_p1 if period_num == 1 else self.daily_p2
        if len(group) == 0:
            return {}
        return WeekdayWeekend(group).by_day_of_week()

    # --------------------------------------------------------
    #  КРИТЕРИИ
    # --------------------------------------------------------
    def _run_checks(self) -> List[CheckResult]:
        checks = []
        for p in self.products:
            m1, m2 = p.markup_pct(1), p.markup_pct(2)
            checks.append(CheckResult(p.name, "Наценка", m1, m2, "%",
                                      m2 >= m1 - 0.5))
            u1, u2 = p.unit_profit(1), p.unit_profit(2)
            checks.append(CheckResult(p.name, "Прибыль/шт", u1, u2, "₽",
                                      u2 >= u1))
            bg, sg = p.price_growth_buy_pct(), p.price_growth_sale_pct()
            checks.append(CheckResult(p.name, "Рост цены vs закупка",
                                      bg, sg, "%", sg >= bg - 0.5))
            drop = p.demand_drop_pct()
            checks.append(CheckResult(p.name, "Падение спроса", 0, drop, "%",
                                      drop <= MAX_DEMAND_DROP_PCT))
        return checks

    # --------------------------------------------------------
    #  ВЕРДИКТ
    # --------------------------------------------------------
    def _make_verdict(self) -> Verdict:
        c1 = all(p.markup_pct(2) >= p.markup_pct(1) - 0.5
                 for p in self.products)
        c2 = all(p.unit_profit(2) >= p.unit_profit(1)
                 for p in self.products)
        c3 = self.total_profit_delta_pct() >= MIN_PROFIT_GROWTH
        c4 = all(p.price_growth_sale_pct()
                 >= p.price_growth_buy_pct() - 0.5
                 for p in self.products)
        c5 = all(p.demand_drop_pct() <= MAX_DEMAND_DROP_PCT
                 for p in self.products)

        flags = {
            "Сохранение наценки": c1,
            "Прибыль с единицы": c2,
            "Общая прибыль": c3,
            "Рост цены vs закупка": c4,
            "Падение спроса": c5,
        }
        score = sum(flags.values())

        if score == 5:
            text = "ПОВЫШЕНИЕ ОБОСНОВАНО"
        elif score == 4:
            text = "ПОВЫШЕНИЕ СКОРЕЕ ОБОСНОВАНО"
        elif score == 3:
            text = "ПОВЫШЕНИЕ СПОРНОЕ"
        else:
            text = "ПОВЫШЕНИЕ НЕ ОБОСНОВАНО"

        return Verdict(text=text, score=score, total=5, checks=flags)

    # --------------------------------------------------------
    #  ПРЕДУПРЕЖДЕНИЯ О ДАННЫХ
    # --------------------------------------------------------
    def data_warnings(self) -> List[str]:
        warnings = []
        for p in self.products:
            for period in (1, 2):
                err = p.stock_error(period)
                if err:
                    warnings.append(err)
            mism = p.stock_mismatch()
            if mism:
                warnings.append(mism)
        return warnings