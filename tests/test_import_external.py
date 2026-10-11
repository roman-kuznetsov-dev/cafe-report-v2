"""
Unit-тесты для tools/import_external.py.

Проверяют:
  - чтение xlsx и csv;
  - signature столбцов (стабильность);
  - работу с маппингами (сохранение, загрузка, поиск);
  - автоугадывание маппинга;
  - сворачивание дубликатов;
  - применение маппинга;
  - полный цикл import_data (без интерактивного диалога).

Тесты с временными файлами используют pytest tmp_path.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                "..", "tools")))

import import_external as imp
import pandas as pd
import pytest


# ============================================================
#  ФИКСТУРЫ
# ============================================================
@pytest.fixture
def sample_df():
    """Простой DataFrame с дубликатами для проверки сворачивания."""
    return pd.DataFrame({
        "Артикул": ["A1", "A2", "A3", "A4"],
        "Наименование": ["Чипсы Lays", "Чипсы Lays", "Кофе", "Кофе"],
        "Категория": ["готовый", "готовый", "напиток", "напиток"],
        "Закуп.Цена": [55, 55, 32, 32],
        "Цена": [110, 110, 130, 130],
        "Кол-во": [40, 60, 100, 80],
    })


@pytest.fixture
def sample_xlsx(sample_df, tmp_path):
    """Сохраняет sample_df как xlsx во временную папку."""
    path = tmp_path / "test_export.xlsx"
    sample_df.to_excel(path, index=False)
    return str(path)


@pytest.fixture
def sample_csv(sample_df, tmp_path):
    """Сохраняет sample_df как csv."""
    path = tmp_path / "test_export.csv"
    sample_df.to_csv(path, index=False, encoding="utf-8")
    return str(path)


@pytest.fixture
def isolated_mappings(tmp_path, monkeypatch):
    """Изолирует MAPPINGS_FILE — временный путь вместо реального."""
    temp_mappings = tmp_path / "test_mappings.json"
    monkeypatch.setattr(imp, "MAPPINGS_FILE", str(temp_mappings))
    return str(temp_mappings)


# ============================================================
#  ТЕСТЫ: ЧТЕНИЕ ФАЙЛА
# ============================================================
def test_read_file_xlsx(sample_xlsx):
    df = imp.read_file(sample_xlsx)
    assert len(df) == 4
    assert "Наименование" in df.columns


def test_read_file_csv(sample_csv):
    df = imp.read_file(sample_csv)
    assert len(df) == 4
    assert "Наименование" in df.columns


def test_read_file_missing():
    with pytest.raises(FileNotFoundError):
        imp.read_file("несуществующий_файл.xlsx")


def test_read_file_bad_format(tmp_path):
    path = tmp_path / "file.txt"
    path.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError, match="Формат не поддерживается"):
        imp.read_file(str(path))


# ============================================================
#  ТЕСТЫ: СИГНАТУРА СТОЛБЦОВ
# ============================================================
def test_signature_stable():
    """Один и тот же набор столбцов — одинаковая signature."""
    sig1 = imp.columns_signature(["A", "B", "C"])
    sig2 = imp.columns_signature(["A", "B", "C"])
    assert sig1 == sig2


def test_signature_order_independent():
    """Порядок столбцов не влияет на signature."""
    sig1 = imp.columns_signature(["A", "B", "C"])
    sig2 = imp.columns_signature(["C", "A", "B"])
    assert sig1 == sig2


def test_signature_different_sets():
    """Разные наборы столбцов — разные signature."""
    sig1 = imp.columns_signature(["A", "B", "C"])
    sig2 = imp.columns_signature(["A", "B", "D"])
    assert sig1 != sig2


# ============================================================
#  ТЕСТЫ: РАБОТА С МАППИНГАМИ
# ============================================================
def test_mappings_start_empty(isolated_mappings):
    """Если файла нет — mappings пустой."""
    data = imp.load_mappings()
    assert data == {"mappings": []}


def test_add_and_find_mapping(isolated_mappings):
    """Добавили маппинг — нашли его по signature."""
    imp.add_mapping(
        signature="abc123",
        name="Тест формат",
        columns=["A", "B", "C"],
        mapping={"Товар": "A", "Цена_1": "B"},
    )

    found = imp.find_mapping("abc123")
    assert found is not None
    assert found["name"] == "Тест формат"
    assert found["mapping"]["Товар"] == "A"


def test_find_mapping_not_exists(isolated_mappings):
    """Нет маппинга с таким signature — None."""
    assert imp.find_mapping("нет_такого") is None


def test_add_mapping_overwrites(isolated_mappings):
    """Повторное добавление с тем же signature — заменяет старый."""
    imp.add_mapping("abc", "Первый", ["A"], {"Товар": "A"})
    imp.add_mapping("abc", "Второй", ["B"], {"Товар": "B"})

    data = imp.load_mappings()
    assert len(data["mappings"]) == 1
    assert data["mappings"][0]["name"] == "Второй"


# ============================================================
#  ТЕСТЫ: АВТОУГАДЫВАНИЕ МАППИНГА
# ============================================================
def test_guess_mapping_russian():
    """Угадывает по русским именам столбцов."""
    cols = ["Наименование", "Категория", "Закуп.Цена", "Цена", "Кол-во"]
    guessed = imp.guess_mapping(cols)
    assert guessed.get("Товар") == "Наименование"
    assert guessed.get("Категория") == "Категория"
    assert guessed.get("Закуп_1") == "Закуп.Цена"
    assert guessed.get("Цена_1") == "Цена"
    assert guessed.get("Кол_1") == "Кол-во"


def test_guess_mapping_english():
    """Угадывает по английским именам."""
    cols = ["name", "category", "cost", "price", "qty"]
    guessed = imp.guess_mapping(cols)
    assert guessed.get("Товар") == "name"
    assert guessed.get("Закуп_1") == "cost"
    assert guessed.get("Цена_1") == "price"
    assert guessed.get("Кол_1") == "qty"


def test_guess_mapping_unknown():
    """Ничего не угадали — пустой словарь."""
    cols = ["X1", "X2", "X3"]
    guessed = imp.guess_mapping(cols)
    assert guessed == {}


# ============================================================
#  ТЕСТЫ: СВОРАЧИВАНИЕ ДУБЛИКАТОВ
# ============================================================
def test_collapse_duplicates_sum():
    """Сворачивает дубликаты, суммируя числовые столбцы."""
    df = pd.DataFrame({
        "Товар": ["A", "A", "B"],
        "Кол": [10, 20, 30],
        "Цена": [5, 5, 7],
    })
    result = imp.collapse_duplicates(
        df, "Товар", {"Кол": "sum", "Цена": "mean"})

    assert len(result) == 2
    a = result[result["Товар"] == "A"].iloc[0]
    assert a["Кол"] == 30
    assert a["Цена"] == 5


def test_collapse_duplicates_no_duplicates():
    """Нет дубликатов — результат не меняется."""
    df = pd.DataFrame({
        "Товар": ["A", "B", "C"],
        "Кол": [10, 20, 30],
    })
    result = imp.collapse_duplicates(df, "Товар", {"Кол": "sum"})
    assert len(result) == 3


def test_collapse_duplicates_empty_rules():
    """Пустые правила — просто уникальные значения по ключу."""
    df = pd.DataFrame({
        "Товар": ["A", "A", "B"],
        "Кол": [10, 20, 30],
    })
    result = imp.collapse_duplicates(df, "Товар", {})
    assert len(result) == 2


# ============================================================
#  ТЕСТЫ: ПРИМЕНЕНИЕ МАППИНГА
# ============================================================
def test_apply_mapping_basic(sample_df):
    """Простой маппинг — переименование и отбор столбцов."""
    mapping = {
        "Товар": "Наименование",
        "Категория": "Категория",
        "Закуп_1": "Закуп.Цена",
        "Цена_1": "Цена",
        "Кол_1": "Кол-во",
    }
    result = imp.apply_mapping(sample_df, mapping, collapse=False)

    assert "Товар" in result.columns
    assert "Цена_1" in result.columns
    assert "Артикул" not in result.columns
    assert len(result) == 4


def test_apply_mapping_collapses(sample_df):
    """С коллапсом — 2 уникальных товара из 4 строк."""
    mapping = {
        "Товар": "Наименование",
        "Категория": "Категория",
        "Закуп_1": "Закуп.Цена",
        "Цена_1": "Цена",
        "Кол_1": "Кол-во",
    }
    result = imp.apply_mapping(sample_df, mapping, collapse=True)

    assert len(result) == 2
    chip = result[result["Товар"] == "Чипсы Lays"].iloc[0]
    assert chip["Кол_1"] == 100   # 40 + 60


def test_apply_mapping_no_product():
    """Маппинг без «Товар» — ошибка."""
    df = pd.DataFrame({"A": [1, 2]})
    with pytest.raises(ValueError, match="Товар"):
        imp.apply_mapping(df, {"Цена_1": "A"})


# ============================================================
#  ТЕСТЫ: ПОЛНЫЙ ЦИКЛ import_data
# ============================================================
def test_import_data_with_existing_mapping(
        sample_xlsx, tmp_path, isolated_mappings, monkeypatch):
    """Полный цикл: маппинг уже сохранён → диалог не вызывается."""
    # Создаём выгрузку и «регистрируем» её формат
    df = imp.read_file(sample_xlsx)
    sig = imp.columns_signature(df.columns)

    mapping = {
        "Товар": "Наименование",
        "Категория": "Категория",
        "Закуп_1": "Закуп.Цена",
        "Цена_1": "Цена",
        "Кол_1": "Кол-во",
    }
    imp.add_mapping(sig, "Тест", list(df.columns), mapping)

    # Запускаем импорт — dialog_func не должен вызываться
    def dialog_should_not_be_called(columns, sig):
        raise AssertionError("Диалог не должен вызываться!")

    out = tmp_path / "result.xlsx"
    imp.import_data(
        input_path=sample_xlsx,
        output_path=str(out),
        dialog_func=dialog_should_not_be_called,
        collapse=True,
    )

    assert out.exists()
    result_df = pd.read_excel(out, sheet_name="Товары")
    assert len(result_df) == 2


def test_import_data_no_mapping_no_dialog(sample_xlsx, tmp_path, isolated_mappings):
    """Маппинга нет и dialog_func не задан → ошибка."""
    out = tmp_path / "result.xlsx"
    with pytest.raises(ValueError, match="dialog_func"):
        imp.import_data(
            input_path=sample_xlsx,
            output_path=str(out),
            dialog_func=None,
            collapse=True,
        )


def test_import_data_with_dialog_func(
        sample_xlsx, tmp_path, isolated_mappings, monkeypatch):
    """Маппинга нет — вызывается dialog_func."""
    # Мок input(), чтобы не вводить имя формата вручную
    monkeypatch.setattr("builtins.input", lambda *args: "Тест формат")

    def fake_dialog(columns, sig):
        return {
            "Товар": "Наименование",
            "Категория": "Категория",
            "Закуп_1": "Закуп.Цена",
            "Цена_1": "Цена",
            "Кол_1": "Кол-во",
        }

    out = tmp_path / "result.xlsx"
    imp.import_data(
        input_path=sample_xlsx,
        output_path=str(out),
        dialog_func=fake_dialog,
        collapse=True,
    )

    assert out.exists()
    result_df = pd.read_excel(out, sheet_name="Товары")
    assert len(result_df) == 2
