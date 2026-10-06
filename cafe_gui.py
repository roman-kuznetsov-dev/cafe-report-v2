"""
Графическое окно программы кафе (версия 2.0).

Автозагрузка: при запуске ищет cafe_data.xlsx рядом с программой.
Отчёт: сохраняется с датой в имени.
Все файлы создаются в папке программы.

Запуск при разработке:  python cafe_gui.py
Сборка EXE:             pyinstaller --onefile --windowed --name CafeReport cafe_gui.py
"""

import os
import sys
import tkinter as tk
import traceback
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import matplotlib

matplotlib.use("Agg")


VERSION = "2.0"

# Папка программы
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

DEFAULT_DATA = os.path.join(BASE_DIR, "cafe_data.xlsx")
if not os.path.exists(DEFAULT_DATA):
    csv_alt = os.path.join(BASE_DIR, "cafe_data.csv")
    if os.path.exists(csv_alt):
        DEFAULT_DATA = csv_alt


# ============================================================
#  ОКНО
# ============================================================
class CafeApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Кафе — расчёт прибыли (v{VERSION})")
        self.root.geometry("1180x720")
        self.root.minsize(950, 600)

        self.data = None        # LoadedData
        self.analysis = None    # Analysis
        self.file_path = None

        self._build_ui()
        self.root.after(100, self.try_autoload)

    # ---------- интерфейс ----------
    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Button(top, text="📂 Открыть другой файл…",
                   command=self.open_file).pack(side="left")
        ttk.Button(top, text="🧮 Пересчитать",
                   command=self.recalc).pack(side="left", padx=6)
        ttk.Button(top, text="💾 Сохранить отчёт",
                   command=self.save_report).pack(side="left", padx=6)
        ttk.Button(top, text="📁 Открыть папку программы",
                   command=self.open_folder).pack(side="left", padx=6)

        self.lbl_file = ttk.Label(top, text="…", foreground="gray")
        self.lbl_file.pack(side="left", padx=12)

        # Вкладки
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.tabs = {}
        for key, title in [
            ("summary", "Сводка"),
            ("just", "Обоснованность"),
            ("stock", "Закупки"),
            ("cash", "Денежный поток"),
            ("flow", "Поток гостей"),
            ("season", "Сезонность"),
            ("weekday", "Будни/выходные"),
            ("settings", "Настройки"),
        ]:
            frame = ttk.Frame(self.nb)
            self.nb.add(frame, text=title)
            self.tabs[key] = frame

        self.trees = {}
        for key in ["summary", "just", "stock", "cash",
                    "flow", "season", "weekday"]:
            self.trees[key] = self._make_tree(self.tabs[key])

        self._build_settings_tab(self.tabs["settings"])

        # статус
        self.lbl_verdict = ttk.Label(self.root, text="Готово к работе",
                                     font=("Segoe UI", 11, "bold"))
        self.lbl_verdict.pack(fill="x", padx=10, pady=(0, 10))

    def _build_settings_tab(self, parent):
        frm = ttk.Frame(parent, padding=20)
        frm.pack(fill="x")

        ttk.Label(frm, text="Эластичность спроса "
                            "(0 — не реагирует, 1 — пропорционально):"
                  ).grid(row=0, column=0, sticky="w")
        self.var_elast = tk.DoubleVar(value=0.8)
        ttk.Scale(frm, from_=0, to=2, variable=self.var_elast,
                  orient="horizontal", length=300).grid(
            row=0, column=1, sticky="w", padx=8)
        self.lbl_elast = ttk.Label(frm, text="0.80")
        self.lbl_elast.grid(row=0, column=2)
        self.var_elast.trace_add(
            "write",
            lambda *_: self.lbl_elast.config(
                text=f"{self.var_elast.get():.2f}"))

        ttk.Label(frm, text="Постоянные издержки за период, ₽:"
                  ).grid(row=1, column=0, sticky="w", pady=8)
        self.var_fixed = tk.DoubleVar(value=30000.0)
        ttk.Entry(frm, textvariable=self.var_fixed,
                  width=15).grid(row=1, column=1, sticky="w", padx=8)

        ttk.Button(frm, text="Применить и пересчитать",
                   command=self.recalc).grid(
            row=2, column=0, columnspan=3, pady=12)

        ttk.Label(frm,
                  text="Примечание: постоянные издержки за периоды "
                       "берутся из листа «Периоды» файла данных.",
                  foreground="gray", wraplength=700
                  ).grid(row=3, column=0, columnspan=3,
                         sticky="w", pady=(20, 0))

    def _make_tree(self, parent):
        tree = ttk.Treeview(parent, columns=("col1",), show="headings")
        tree.pack(fill="both", expand=True, side="left")

        ysb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        ysb.pack(fill="y", side="right")
        tree.configure(yscrollcommand=ysb.set)
        return tree

    # ---------- действия ----------
    def try_autoload(self):
        if os.path.exists(DEFAULT_DATA):
            self.file_path = DEFAULT_DATA
            self.lbl_file.config(
                text=f"Файл: {os.path.basename(DEFAULT_DATA)}",
                foreground="black")
            self.recalc()
        else:
            self.lbl_file.config(
                text="cafe_data.xlsx не найден — нажмите «Открыть другой файл»",
                foreground="#b00")

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Выберите файл с данными кафе",
            initialdir=BASE_DIR,
            filetypes=[("Excel/CSV", "*.xlsx *.xls *.csv"),
                       ("Все файлы", "*.*")])
        if not path:
            return
        self.file_path = path
        self.lbl_file.config(text=f"Файл: {os.path.basename(path)}",
                             foreground="black")
        self.recalc()

    def recalc(self):
        if not self.file_path:
            messagebox.showinfo("Нет файла",
                                "Сначала откройте файл с данными.")
            return

        import cafe_model
        cafe_model.ELASTICITY = self.var_elast.get()

        try:
            from cafe_analysis import Analysis
            from cafe_loader import load_all

            self.data = load_all(self.file_path)
            self.analysis = Analysis(
                self.data.products,
                self.data.periods,
                self.data.daily,
                self.data.season_records,
            )
        except Exception as e:
            messagebox.showerror("Ошибка загрузки или расчёта",
                                 f"{e}\n\n{traceback.format_exc()}")
            return

        self._fill_all_tabs()

        v = self.analysis.verdict
        self.lbl_verdict.config(
            text=f"Вердикт: {v.text}  ({v.score}/{v.total})")

    def save_report(self):
        if not self.analysis:
            messagebox.showinfo("Нет данных", "Сначала загрузите файл.")
            return

        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        default_name = f"cafe_report_{stamp}.xlsx"
        out = filedialog.asksaveasfilename(
            title="Куда сохранить отчёт",
            initialdir=BASE_DIR,
            initialfile=default_name,
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if not out:
            return

        try:
            from cafe_exporter import export_to_excel
            export_to_excel(self.analysis, out)
        except Exception as e:
            messagebox.showerror("Ошибка сохранения",
                                 f"{e}\n\n{traceback.format_exc()}")
            return

        messagebox.showinfo("Готово", f"Отчёт сохранён:\n{out}")
        try:
            if sys.platform.startswith("win"):
                os.startfile(out)
        except Exception:
            pass

    def open_folder(self):
        if sys.platform.startswith("win"):
            os.startfile(BASE_DIR)
        elif sys.platform == "darwin":
            os.system(f'open "{BASE_DIR}"')
        else:
            os.system(f'xdg-open "{BASE_DIR}"')

    # ---------- заполнение таблиц ----------
    def _set_table(self, tree, columns, rows):
        tree.delete(*tree.get_children())
        tree["columns"] = columns
        tree["show"] = "headings"
        for c in columns:
            tree.heading(c, text=c)
            tree.column(c, width=130, anchor="center")
        for row in rows:
            tree.insert("", "end", values=row)

    def _fill_all_tabs(self):
        a = self.analysis

        # ---- Сводка ----
        rows = []
        for s in a.summaries:
            rows.append([
                s.name, s.category,
                f"{s.revenue_1:.2f}", f"{s.revenue_2:.2f}",
                f"{s.profit_1:.2f}", f"{s.profit_2:.2f}",
                f"{s.delta_profit():+.2f}",
                f"{s.delta_profit_pct():+.1f}%",
                f"{s.markup_1:.1f}%", f"{s.markup_2:.1f}%",
            ])
        self._set_table(self.trees["summary"],
                        ["Товар", "Категория", "Выручка1", "Выручка2",
                         "Прибыль1", "Прибыль2", "Δ Прибыль",
                         "Δ Прибыль%", "Наценка1", "Наценка2"], rows)

        # ---- Обоснованность ----
        rows = []
        for c in a.checks:
            rows.append([
                c.product, c.criterion,
                f"{c.before:.2f}", f"{c.after:.2f}", c.unit,
                "OK" if c.ok else "НЕТ",
            ])
        self._set_table(self.trees["just"],
                        ["Товар", "Критерий", "Было", "Стало",
                         "Ед.", "Результат"], rows)

        # ---- Закупки ----
        rows = []
        for p in a.products:
            rows.append([
                p.name,
                p.stock_start_1, p.purchase_qty_1, p.qty_1,
                p.stock_end(1), f"{p.stock_value(1):.2f}",
                p.stock_start_2, p.purchase_qty_2, p.qty_2,
                p.stock_end(2), f"{p.stock_value(2):.2f}",
            ])
        self._set_table(self.trees["stock"],
                        ["Товар",
                         "Остаток_нач_1", "Закуп_1", "Продано_1",
                         "Остаток_кон_1", "Стоим_1",
                         "Остаток_нач_2", "Закуп_2", "Продано_2",
                         "Остаток_кон_2", "Стоим_2"], rows)

        # ---- Денежный поток ----
        rows = []
        for s in a.summaries:
            rows.append([
                s.name,
                f"{s.profit_1:.2f}", f"{s.profit_2:.2f}",
                f"{s.cash_flow_1:.2f}", f"{s.cash_flow_2:.2f}",
                f"{s.profit_1 - s.cash_flow_1:.2f}",
                f"{s.profit_2 - s.cash_flow_2:.2f}",
            ])
        self._set_table(self.trees["cash"],
                        ["Товар",
                         "Упр.прибыль 1", "Упр.прибыль 2",
                         "Ден.поток 1", "Ден.поток 2",
                         "Разница 1", "Разница 2"], rows)

        # ---- Поток гостей ----
        rows = []
        for r in a.flow_summary():
            rows.append([
                r["Товар"],
                f"{r['Конв_1']:.4f}", f"{r['Конв_2']:.4f}",
                f"{r['ΔКонв_%']:+.2f}%",
                f"{r['Эффект_потока']:+.2f}",
                f"{r['Эффект_конверсии']:+.2f}",
                r["ΔПродано"],
            ])
        self._set_table(self.trees["flow"],
                        ["Товар", "Конв1", "Конв2", "ΔКонв%",
                         "Влияние потока", "Влияние конверсии",
                         "ΔПродано"], rows)

        # ---- Сезонность ----
        if a.has_season_history():
            coef = a.season_coefficients()
            rows = []
            for product, seasons in coef.items():
                row = [product]
                for s in ["зима", "весна", "лето", "осень"]:
                    v = seasons.get(s, 0)
                    row.append(f"{v:.3f}" if v else "—")
                rows.append(row)
            self._set_table(self.trees["season"],
                            ["Товар", "Зима", "Весна",
                             "Лето", "Осень"], rows)
        else:
            self._set_table(self.trees["season"],
                            ["Сообщение"],
                            [["Нет сезонной истории — "
                              "заполните лист «Сезонная история»"]])

        # ---- Будни/выходные ----
        if a.has_daily_data():
            rows = []
            for pnum, pname in [(1, a.p1.name), (2, a.p2.name)]:
                w = a.weekday_weekend_for_period(pnum)
                if not w:
                    continue
                g = w["guests"]
                rows.append([pname, "(гости)",
                             f"{g['будни']:.1f}", f"{g['выходные']:.1f}",
                             f"{g['индекс_вых']:.2f}"])
                for name, vals in w["products"].items():
                    rows.append([
                        pname, name,
                        f"{vals['будни']:.1f}", f"{vals['выходные']:.1f}",
                        f"{vals['индекс_вых']:.2f}"])
            self._set_table(self.trees["weekday"],
                            ["Период", "Товар", "Будни",
                             "Выходные", "Индекс вых."], rows)
        else:
            self._set_table(self.trees["weekday"],
                            ["Сообщение"],
                            [["Нет ежедневных данных — "
                              "заполните лист «Ежедневные данные»"]])


if __name__ == "__main__":
    root = tk.Tk()
    app = CafeApp(root)
    root.mainloop()
