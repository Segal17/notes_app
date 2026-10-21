import flet as ft

from src.ui.note_form import note_form_view
from src.ui.notes_list import notes_list_view
from src.ui.settings import settings_view


def main(page: ft.Page):
    page.title = "Заметки"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 16
    page.window.width = 620
    page.window.height = 780

    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[
            ft.Locale(language_code="ru", country_code="RU"),
            ft.Locale(language_code="en", country_code="US"),
        ],
        current_locale=ft.Locale(language_code="ru", country_code="RU"),
    )

    def show_form():
        page.clean()
        page.add(note_form_view(
            page,
            on_open_settings=show_settings,
            on_open_list=show_list,
        ))
        page.update()

    def show_settings():
        page.clean()
        page.add(settings_view(page, on_back=show_form))
        page.update()

    def show_list():
        page.clean()
        page.add(notes_list_view(page, on_back=show_form))
        page.update()

    show_form()


if __name__ == "__main__":
    ft.app(target=main)
