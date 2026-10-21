import flet as ft

from src.config import Settings, load_settings, save_settings
from src.db_client import DbError, NotesDb


def settings_view(page: ft.Page, on_back) -> ft.Control:
    s = load_settings()

    host_field = ft.TextField(label="Хост (IP малинки)", value=s.db_host)
    port_field = ft.TextField(label="Порт", value=str(s.db_port), keyboard_type=ft.KeyboardType.NUMBER)
    db_field = ft.TextField(label="База данных", value=s.db_name)
    user_field = ft.TextField(label="Пользователь", value=s.db_user)
    pass_field = ft.TextField(label="Пароль", value=s.db_password, password=True, can_reveal_password=True)

    check_btn = ft.ElevatedButton("Проверить подключение")
    save_btn = ft.FilledButton("Сохранить")
    progress = ft.ProgressRing(width=16, height=16, visible=False)

    def show_snack(text: str, ok: bool):
        page.open(ft.SnackBar(
            content=ft.Text(text),
            bgcolor=ft.colors.GREEN_600 if ok else ft.colors.RED_600,
        ))

    def set_busy(busy: bool):
        check_btn.disabled = busy
        save_btn.disabled = busy
        progress.visible = busy
        page.update()

    def collect() -> Settings | None:
        try:
            port = int((port_field.value or "").strip())
        except ValueError:
            show_snack("Порт должен быть числом", False)
            return None
        host = (host_field.value or "").strip()
        dbname = (db_field.value or "").strip()
        user = (user_field.value or "").strip()
        password = pass_field.value or ""
        if not host or not dbname or not user:
            show_snack("Заполните хост, базу и пользователя", False)
            return None
        return Settings(db_host=host, db_port=port, db_name=dbname, db_user=user, db_password=password)

    def on_check(e):
        cfg = collect()
        if not cfg:
            return
        set_busy(True)
        def worker():
            try:
                NotesDb(cfg.db_host, cfg.db_port, cfg.db_name, cfg.db_user, cfg.db_password).health()
                show_snack("Подключение OK", True)
            except DbError as err:
                show_snack(err.message, False)
            finally:
                set_busy(False)
        page.run_thread(worker)

    def on_save(e):
        cfg = collect()
        if not cfg:
            return
        save_settings(cfg)
        show_snack("Сохранено", True)

    check_btn.on_click = on_check
    save_btn.on_click = on_save

    return ft.Column(
        controls=[
            ft.Text("Настройки БД", size=20, weight=ft.FontWeight.BOLD),
            host_field, port_field, db_field, user_field, pass_field,
            ft.Row([check_btn, progress], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            save_btn,
            ft.OutlinedButton("Назад", on_click=lambda e: on_back()),
        ],
        spacing=12,
        expand=True,
    )
