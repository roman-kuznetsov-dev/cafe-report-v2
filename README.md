# ☕ Кафе — расчёт прибыли и обоснованности цен

[![CI](https://github.com/roman-kuznetsov-dev/cafe-report-v2/actions/workflows/ci.yml/badge.svg)](https://github.com/roman-kuznetsov-dev/cafe-report-v2/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-77%20passed-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-91%25-green)]()

Программа для кафе: считает прибыль за два периода, проверяет
обоснованность повышения цен, анализирует поток гостей, сезонность
и точку безубыточности.

## Возможности

- 📊 **Сводка** — прибыль и наценка по товарам
- ✅ **Обоснованность** — проверка повышения цен по 5 критериям
- 🚚 **Закупки** — остатки и их стоимость
- 💰 **Денежный поток** vs управленческая прибыль
- 👥 **Поток гостей** — конверсия и разложение продаж
- 📅 **Сезонность** — коэффициенты по сезонам
- 🗓 **Будни/выходные** — средние и индекс выходного дня
- 📉 **Безубыточность** — сколько продать, чтобы покрыть расходы
- 📤 **Экспорт в Excel** — 9 листов + 7 графиков PNG

## Установка

    git clone https://github.com/roman-kuznetsov-dev/cafe-report-v2.git
    cd cafe-report-v2
    python -m venv venv
    venv\Scripts\activate          # Windows
    pip install -r requirements.txt

## Запуск

    python cafe_gui.py

## Данные

Файл `cafe_data.xlsx` содержит 4 листа:

- **Товары** — закупки, цены, продажи, остатки
- **Периоды** — даты, сезон, гостей, постоянные издержки
- **Ежедневные данные** — по дням: гости + продажи
- **Сезонная история** — средние по сезонам

Для генерации тестовых данных:

    python tools/generate_test_data.py --products 30

## Тесты

    pytest -v                    # запуск тестов
    pytest --cov=.               # с покрытием
    ruff check .                 # линтер

## Архитектура

```

cafe_model.py       — модель (Product, Period, Flow, Seasonality)
cafe_loader.py      — загрузка из Excel
cafe_analysis.py    — общий анализ
cafe_exporter.py    — экспорт в Excel
cafe_charts.py      — генерация графиков
cafe_gui.py         — GUI (tkinter)
tools/              — генератор данных
tests/              — unit-тесты (77, покрытие 91%)

```

## Стек

Python 3.11+ · pandas · xlsxwriter · matplotlib · tkinter · pytest · ruff · GitHub Actions
