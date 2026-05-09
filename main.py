import flet as ft
from database import init_db
from views.dashboard import dashboard_view
from views.contas import contas_view
from views.extrato import extrato_view
from views.avulso import avulso_view
from views.fixas import fixas_view
from views.cadastro import cadastro_view
from views.bancos import bancos_view
from views.login import login_view
from views.parcelas import parcelas_view
from views.dividas import dividas_view

ROTAS_PUBLICAS = {"/login", "/cadastro"}


def main(page: ft.Page):
    page.title = "FINANÇA SIMPLES - Versão Oficial"
    page.window_width  = 1200
    page.window_height = 900
    page.theme_mode    = ft.ThemeMode.LIGHT

    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[ft.Locale("pt", "BR")],
        current_locale=ft.Locale("pt", "BR"),
    )

    init_db()

    def logado() -> bool:
        return page.session.get("user_id") is not None

    def route_change(route):
        page.views.clear()

        if page.route not in ROTAS_PUBLICAS and not logado():
            page.views.append(login_view(page))
            page.update()
            return

        rotas = {
            "/login":    login_view,
            "/cadastro": cadastro_view,
            "/":         dashboard_view,
            "/contas":   contas_view,
            "/extrato":  extrato_view,
            "/avulso":   avulso_view,
            "/fixas":    fixas_view,
            "/bancos":   bancos_view,
            "/parcelas": parcelas_view,
            "/dividas":  dividas_view,
        }

        view_fn = rotas.get(page.route)
        if view_fn:
            page.views.append(view_fn(page))
        else:
            page.views.append(dashboard_view(page))

        page.update()

    def view_pop(e):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop     = view_pop
    page.go("/login")


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8080)

## - if __name__ == "__main__":
## -     ft.app(target=main)