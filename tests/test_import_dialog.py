"""
Тесты для интерактивного диалога import_external.interactive_dialog.
Используют моки input(), чтобы не вводить данные вручную.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                "..", "tools")))

import import_external as imp
import pytest


# ============================================================
#  ВСПОМОГАТЕЛЬНЫЙ МОК
# ============================================================
class InputMocker:
    """Возвращает заранее подготовленные ответы на input()."""
    def __init__(self, answers):
        self.answers = list(answers)
        self.index = 0

    def __call__(self, *args, **kwargs):
        if self.index >= len(self.answers):
            raise AssertionError(
                f"Закончились ответы. Всего ответов: {len(self.answers)}")
        answer = self.answers[self.index]
        self.index += 1
        return answer


# ============================================================
#  ТЕСТЫ
# ============================================================
def test_dialog_full_mapping(monkeypatch):
    """
    Полный маппинг: пользователь вводит номера столбцов.
    Столбцы: [0] Артикул [1] Наименование [2] Категория
             [3] Закуп.Цена [4] Цена [5] Кол-во
    """
    columns = ["Артикул", "Наименование", "Категория",
               "Закуп.Цена", "Цена", "Кол-во"]

    # Поля спрашиваются в порядке:
    # Товар, Категория, Закуп_1, Цена_1, Кол_1,
    # Закуп_кол_1, Остаток_нач_1, Закуп_2, Цена_2, Кол_2
    # На необязательные — пустой ввод (Enter).
    answers = [
        "1",   # Товар = Наименование
        "2",   # Категория = Категория
        "3",   # Закуп_1 = Закуп.Цена
        "4",   # Цена_1 = Цена
        "5",   # Кол_1 = Кол-во
        "",    # Закуп_кол_1 — пропустить
        "",    # Остаток_нач_1 — пропустить
        "",    # Закуп_2 — пропустить
        "",    # Цена_2 — пропустить
        "",    # Кол_2 — пропустить
        "д",   # подтвердить маппинг
    ]
    monkeypatch.setattr("builtins.input", InputMocker(answers))

    mapping = imp.interactive_dialog(columns, "test_sig")
    assert mapping["Товар"] == "Наименование"
    assert mapping["Категория"] == "Категория"
    assert mapping["Закуп_1"] == "Закуп.Цена"
    assert mapping["Цена_1"] == "Цена"
    assert mapping["Кол_1"] == "Кол-во"
    assert "Закуп_2" not in mapping


def test_dialog_skip_optional(monkeypatch):
    """Все необязательные — пропущены."""
    columns = ["Товар", "Цена"]

    answers = [
        "0",   # Товар = Товар
        "",    # Категория — пропустить
        "1",   # Закуп_1 = Цена (единственный вариант)
        "1",   # Цена_1 = Цена
        "1",   # Кол_1 = Цена (грубо, но для теста)
        "", "", "", "", "",   # все необязательные
        "д",
    ]
    monkeypatch.setattr("builtins.input", InputMocker(answers))

    mapping = imp.interactive_dialog(columns, "test_sig")
    # Обязательные заполнены, опциональные — нет
    assert "Товар" in mapping
    assert "Закуп_1" in mapping
    assert "Закуп_2" not in mapping


def test_dialog_by_name(monkeypatch):
    """Пользователь вводит имена столбцов вместо номеров."""
    columns = ["Наименование", "Цена"]

    answers = [
        "Наименование",   # Товар
        "",               # Категория — пропустить
        "Цена",           # Закуп_1
        "Цена",           # Цена_1
        "Цена",           # Кол_1
        "", "", "", "", "",
        "д",
    ]
    monkeypatch.setattr("builtins.input", InputMocker(answers))

    mapping = imp.interactive_dialog(columns, "test_sig")
    assert mapping["Товар"] == "Наименование"


def test_dialog_rejects_unknown(monkeypatch):
    """Неизвестное имя → повторный запрос."""
    columns = ["Наименование", "Цена"]

    answers = [
        "Чепуха",         # Товар — не найдёт
        "0",              # попробует снова — номер
        "",               # Категория — пропустить
        "1",              # Закуп_1
        "1",              # Цена_1
        "1",              # Кол_1
        "", "", "", "", "",
        "д",
    ]
    monkeypatch.setattr("builtins.input", InputMocker(answers))

    mapping = imp.interactive_dialog(columns, "test_sig")
    assert mapping["Товар"] == "Наименование"


def test_dialog_declined(monkeypatch):
    """Пользователь не подтвердил маппинг → ошибка."""
    columns = ["Наименование", "Цена"]

    answers = [
        "0", "", "1", "1", "1",
        "", "", "", "", "",
        "н",   # не подтверждаем
    ]
    monkeypatch.setattr("builtins.input", InputMocker(answers))

    with pytest.raises(ValueError, match="не подтверждён"):
        imp.interactive_dialog(columns, "test_sig")
