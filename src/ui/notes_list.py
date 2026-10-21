import flet as ft

from src.config import load_settings
from src.db_client import DbError, NotesDb


def notes_list_view(page: ft.Page, on_back) -> ft.Control:
    list_column = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)
    progress = ft.ProgressRing(width=20, height=20, visible=False)
    status = ft.Text("", size=12, color=ft.colors.GREY_500)

    def make_item(n: dict) -> ft.Control:
        culture = n.get("culture") or "—"
        desc = n.get("description") or ""
        date = n.get("date") or ""
        created = n.get("created_at") or ""

        return ft.Container(
            padding=10,
            border_radius=8,
            bgcolor=ft.colors.SURFACE_CONTAINER_HIGHEST,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(f"#{n['id']}", size=12, color=ft.colors.GREY_500),
                            ft.Text(date, size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(created, size=11, color=ft.colors.GREY_500),
                        ],
                        spacing=10,
                    ),
                    ft.Text(culture, size=14, weight=ft.FontWeight.BOLD),
                    ft.Text(desc, size=13),
                ],
                spacing=4,
            ),
        )

    def load_data(e=None):
        progress.visible = True
        status.value = ""
        list_column.controls.clear()
        page.update()

        s = load_settings()

        def worker():
            try:
                db = NotesDb(s.db_host, s.db_port, s.db_name, s.db_user, s.db_password)
                notes = db.list_notes(limit=500)
                for n in notes:
                    list_column.controls.append(make_item(n))
                status.value = f"Записей: {len(notes)}"
            except DbError as err:
                status.value = f"Ошибка: {err.message}"
            finally:
                progress.visible = False
                page.update()

        page.run_thread(worker)

    header = ft.Container(
        padding=ft.padding.only(bottom=8),
        content=ft.Row(
            controls=[
                ft.Text("Записи", size=20, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.OutlinedButton("Назад", on_click=lambda e: on_back()),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    footer = ft.Container(
        padding=ft.padding.only(top=8),
        content=ft.Row(
            controls=[
                ft.FilledButton("Обновить", on_click=load_data),
                progress,
                status,
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    root = ft.Column(
        controls=[
            header,
            list_column,
            footer,
        ],
        spacing=0,
        expand=True,
    )

    # первичная загрузка
    load_data()
    return root
