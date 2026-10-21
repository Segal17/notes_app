import datetime
import calendar

import flet as ft

from src.config import load_settings
from src.db_client import DbError, NotesDb
from src.speech import Recorder, SpeechError


MONTHS_RU = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]

SETTINGS_PASSWORD = "rpi"
DEFAULT_ROWS = 4
HISTORY_LIMIT = 20


def _fmt_date(iso: str) -> str:
    if not iso:
        return ""
    try:
        return datetime.date.fromisoformat(iso[:10]).strftime("%d.%m.%Y")
    except ValueError:
        return iso


def note_form_view(page: ft.Page, on_open_settings, on_open_list=None) -> ft.Control:
    today = datetime.date.today()
    state = {"day": today.day, "month": today.month, "year": today.year}

    day_dd = ft.Dropdown(label="День", width=100, value=str(today.day))
    month_dd = ft.Dropdown(
        label="Месяц",
        width=180,
        value=str(today.month),
        options=[ft.dropdown.Option(key=str(i + 1), text=MONTHS_RU[i]) for i in range(12)],
    )
    year_dd = ft.Dropdown(
        label="Год",
        width=120,
        value=str(today.year),
        options=[ft.dropdown.Option(key=str(y), text=str(y)) for y in range(2000, 2101)],
    )

    def refresh_days():
        year = int(year_dd.value)
        month = int(month_dd.value)
        last_day = calendar.monthrange(year, month)[1]
        current = int(day_dd.value) if day_dd.value else 1
        if current > last_day:
            current = last_day
        day_dd.options = [ft.dropdown.Option(key=str(d), text=str(d)) for d in range(1, last_day + 1)]
        day_dd.value = str(current)
        state["day"] = current
        state["month"] = month
        state["year"] = year
        page.update()

    def on_day(e):
        state["day"] = int(day_dd.value)
        page.update()

    def on_month(e):
        state["month"] = int(month_dd.value)
        refresh_days()

    def on_year(e):
        state["year"] = int(year_dd.value)
        refresh_days()

    day_dd.on_change = on_day
    month_dd.on_change = on_month
    year_dd.on_change = on_year

    last_day = calendar.monthrange(today.year, today.month)[1]
    day_dd.options = [ft.dropdown.Option(key=str(d), text=str(d)) for d in range(1, last_day + 1)]

    date_row = ft.Row(
        controls=[day_dd, month_dd, year_dd],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    rows_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    rows = []

    toast_holder = ft.Container()  # держим ссылку, объявим ниже в Stack

    def show_toast(text: str, ok: bool):
        bg = ft.colors.GREEN_600 if ok else ft.colors.RED_600
        toast = ft.Container(
            content=ft.Text(text, color=ft.colors.WHITE, size=14),
            bgcolor=bg,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8,
        )
        toast_holder.content = ft.Row(
            controls=[toast],
            alignment=ft.MainAxisAlignment.CENTER,
        )
        toast_holder.top = 10
        toast_holder.left = 0
        toast_holder.right = 0
        toast_holder.visible = True
        page.update()

        def hide():
            import time
            time.sleep(2.5)
            toast_holder.visible = False
            page.update()

        page.run_thread(hide)

    def remove_row(row):
        rows_column.controls.remove(row["container"])
        rows.remove(row)
        page.update()

    def confirm_delete(row, on_yes):
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Удалить запись?"),
            content=ft.Text("Это действие нельзя отменить."),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: (page.close(dlg), page.update())),
                ft.FilledButton("Удалить", on_click=lambda e: (page.close(dlg), page.update(), on_yes())),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)
        page.update()

    def delete_existing(row, note_id):
        s = load_settings()

        def worker():
            try:
                db = NotesDb(s.db_host, s.db_port, s.db_name, s.db_user, s.db_password)
                db.delete_note(note_id)
                show_toast(f"Запись #{note_id} удалена", True)
                remove_row(row)
            except DbError as err:
                show_toast(err.message, False)

        page.run_thread(worker)

    def add_row(culture_value: str = "", desc_value: str = "", note_id=None, left_label: str | None = None):
        culture_tf = ft.TextField(label="Культура", width=160)
        desc_tf = ft.TextField(label="Описание", expand=True, multiline=True, min_lines=1, max_lines=None)
        if culture_value:
            culture_tf.value = culture_value
        if desc_value:
            desc_tf.value = desc_value

        initial_culture = culture_value
        initial_desc = desc_value

        row_dict = {
            "id": note_id,
            "culture": culture_tf,
            "desc": desc_tf,
            "recorder": Recorder("ru-RU"),
            "busy": False,
            "initial_culture": initial_culture,
            "initial_desc": initial_desc,
        }

        mic_btn = ft.IconButton(icon=ft.icons.MIC, tooltip="Начать/остановить запись")
        mic_progress = ft.ProgressRing(width=16, height=16, visible=False)

        def on_mic_click(e, rd=row_dict, btn=mic_btn, prog=mic_progress, tf=desc_tf):
            if rd["busy"]:
                return
            recorder: Recorder = rd["recorder"]

            if not recorder.is_recording:
                try:
                    recorder.start()
                    btn.icon = ft.icons.STOP
                    show_toast("Запись пошла. Нажми ⏹, чтобы остановить", True)
                except SpeechError as err:
                    show_toast(err.message, False)
                page.update()
                return

            rd["busy"] = True
            btn.disabled = True
            prog.visible = True
            page.update()

            def worker():
                try:
                    text = recorder.stop()
                    current = tf.value or ""
                    tf.value = (current + " " + text) if current else text
                    show_toast("Распознано", True)
                except SpeechError as err:
                    show_toast(err.message, False)
                finally:
                    rd["busy"] = False
                    btn.icon = ft.icons.MIC
                    btn.disabled = False
                    prog.visible = False
                    page.update()

            page.run_thread(worker)

        mic_btn.on_click = on_mic_click

        def on_del(e, rd=row_dict):
            if rd["id"] is None:
                if len(rows) <= 1:
                    return
                remove_row(rd)
            else:
                confirm_delete(rd, lambda: delete_existing(rd, rd["id"]))

        del_btn = ft.IconButton(icon=ft.icons.CLOSE, tooltip="Удалить строку", on_click=on_del)

        id_label = ft.Text(
            left_label if left_label is not None else (f"#{note_id}" if note_id is not None else "новая"),
            size=11,
            color=ft.colors.GREY_500,
            width=70,
        )

        row_container = ft.Row(
            controls=[id_label, culture_tf, desc_tf, mic_btn, mic_progress, del_btn],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        row_dict["container"] = row_container

        rows.append(row_dict)
        rows_column.controls.append(row_container)
        page.update()

    def reset_to_empty():
        for r in list(rows):
            try:
                if r["recorder"].is_recording:
                    r["recorder"].stop()
            except Exception:
                pass
            rows_column.controls.remove(r["container"])
        rows.clear()
        for _ in range(DEFAULT_ROWS):
            add_row()
        page.update()

    def reset_to_create():
        today2 = datetime.date.today()
        day_dd.value = str(today2.day)
        month_dd.value = str(today2.month)
        year_dd.value = str(today2.year)
        last_day2 = calendar.monthrange(today2.year, today2.month)[1]
        day_dd.options = [ft.dropdown.Option(key=str(d), text=str(d)) for d in range(1, last_day2 + 1)]
        state["mode"] = "create"
        date_block.visible = True
        add_row_btn.visible = True
        save_btn.visible = True
        history_btn.text = "Показать историю"
        history_btn.icon = ft.icons.HISTORY
        reset_to_empty()
        page.update()

    for _ in range(DEFAULT_ROWS):
        add_row()

    add_row_btn = ft.OutlinedButton("Добавить запись", icon=ft.icons.ADD)
    add_row_btn.on_click = lambda e: add_row()

    history_btn = ft.OutlinedButton("Показать историю", icon=ft.icons.HISTORY)
    save_btn = ft.FilledButton("Сохранить")
    progress = ft.ProgressRing(width=16, height=16, visible=False)

    clear_btn = ft.OutlinedButton("Очистить", icon=ft.icons.CLEAR)

    def set_busy(busy: bool):
        save_btn.disabled = busy
        add_row_btn.disabled = busy
        history_btn.disabled = busy
        clear_btn.disabled = busy
        progress.visible = busy
        page.update()

    def load_history(e=None):
        set_busy(True)
        s = load_settings()

        def worker():
            try:
                db = NotesDb(s.db_host, s.db_port, s.db_name, s.db_user, s.db_password)
                notes = db.list_notes(limit=HISTORY_LIMIT)

                for r in list(rows):
                    try:
                        if r["recorder"].is_recording:
                            r["recorder"].stop()
                    except Exception:
                        pass
                    rows_column.controls.remove(r["container"])
                rows.clear()

                for n in notes:
                    add_row(
                        n.get("culture") or "",
                        n.get("description") or "",
                        note_id=n["id"],
                        left_label=_fmt_date(n.get("date") or ""),
                    )

                if not notes:
                    for _ in range(DEFAULT_ROWS):
                        add_row()
                    show_toast("Записей нет", False)
                else:
                    show_toast(f"Загружено записей: {len(notes)}", True)

                page.update()
            except DbError as err:
                show_toast(err.message, False)
                if not rows:
                    for _ in range(DEFAULT_ROWS):
                        add_row()
                    page.update()
            finally:
                set_busy(False)

        page.run_thread(worker)

    history_btn.on_click = load_history

    def on_clear(e):
        reset_to_create()
        show_toast("Форма очищена", True)

    clear_btn.on_click = on_clear

    # --- скрытый вход в настройки ---
    password_field = ft.TextField(label="Пароль", password=True, can_reveal_password=True, autofocus=True)

    def close_pwd_dialog(dlg):
        page.close(dlg)
        page.update()

    def try_open_settings(dlg):
        if (password_field.value or "") == SETTINGS_PASSWORD:
            page.close(dlg)
            page.update()
            on_open_settings()
        else:
            page.close(dlg)
            page.update()
            show_toast("Неверный пароль", False)

    pwd_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Вход в настройки"),
        content=password_field,
        actions=[
            ft.TextButton("Отмена", on_click=lambda e: close_pwd_dialog(pwd_dialog)),
            ft.FilledButton("Войти", on_click=lambda e: try_open_settings(pwd_dialog)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def open_settings_guarded(e):
        password_field.value = ""
        page.open(pwd_dialog)
        page.update()

    title = ft.Row(
        controls=[
            ft.GestureDetector(
                content=ft.Text("Н", size=20, weight=ft.FontWeight.BOLD),
                on_tap=open_settings_guarded,
            ),
            ft.Text("овая заметка", size=20, weight=ft.FontWeight.BOLD),
        ],
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    def on_save(e):
        try:
            picked_date = datetime.date(int(year_dd.value), int(month_dd.value), int(day_dd.value))
        except ValueError:
            show_toast("Некорректная дата", False)
            return

        to_update = []
        to_insert = []

        for r in rows:
            culture = (r["culture"].value or "").strip()
            desc = (r["desc"].value or "").strip()
            rid = r["id"]

            if rid is not None:
                if culture != r["initial_culture"] or desc != r["initial_desc"]:
                    to_update.append((rid, culture or None, desc or None))
            else:
                if culture or desc:
                    to_insert.append((culture or None, desc or None))

        if not to_update and not to_insert:
            show_toast("Нет изменений и нет новых записей", False)
            return

        set_busy(True)
        date_iso = picked_date.isoformat()
        s = load_settings()

        def worker():
            updated = 0
            inserted = 0
            try:
                db = NotesDb(s.db_host, s.db_port, s.db_name, s.db_user, s.db_password)
                for rid, culture, desc in to_update:
                    db.update_note(rid, culture, desc)
                    updated += 1
                for culture, desc in to_insert:
                    db.create_note(culture, desc, date_iso)
                    inserted += 1
                show_toast(f"Обновлено: {updated}, добавлено: {inserted}", True)
                reset_to_empty()
            except DbError as err:
                show_toast(f"Ошибка (обновлено {updated}, добавлено {inserted}): {err.message}", False)
            finally:
                set_busy(False)

        page.run_thread(worker)

    save_btn.on_click = on_save

    date_block = ft.Column(
        controls=[
            ft.Text("Дата для новых записей", size=14),
            date_row,
        ],
        spacing=8,
    )

    header_container = ft.Container(
        content=ft.Column(
            controls=[
                title,
                date_block,
                ft.Divider(),
            ],
            spacing=12,
        ),
    )

    footer_container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row([add_row_btn], spacing=8),
                ft.Row([save_btn, history_btn, clear_btn, progress], spacing=12,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ],
            spacing=12,
        ),
    )

    main_column = ft.Column(
        controls=[
            header_container,
            rows_column,
            footer_container,
        ],
        spacing=12,
        expand=True,
    )

    toast_holder.visible = False
    toast_holder.top = 10
    toast_holder.left = 0
    toast_holder.right = 0

    return ft.Stack(
        controls=[main_column, toast_holder],
        expand=True,
    )
