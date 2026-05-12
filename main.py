import flet as ft
import os
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

# Rotas que não exigem login
ROTAS_PUBLICAS = {"/login", "/cadastro"}


def main(page: ft.Page):
    page.title = "FINANÇA SIMPLES - Versão Oficial"

    # Configurações de layout para Web
    page.window_width = 1200
    page.window_height = 900
    page.theme_mode = ft.ThemeMode.LIGHT

    # Configuração de Localização (Moeda e Data em PT-BR)
    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[ft.Locale("pt", "BR")],
        current_locale=ft.Locale("pt", "BR"),
    )

    # Inicializa o banco de dados PostgreSQL
    init_db()

    def logado() -> bool:
        """Verifica se o ID do utilizador está presente na sessão atual."""
        return page.session.get("user_id") is not None

    def route_change(route):
        """Gerencia a navegação entre as diferentes visualizações (views)."""
        page.views.clear()

        # Proteção de acesso: se não estiver logado, redireciona para login
        if page.route not in ROTAS_PUBLICAS and not logado():
            page.views.append(login_view(page))
            page.update()
            return

        # Mapeamento de rotas
        rotas = {
            "/login": login_view,
            "/cadastro": cadastro_view,
            "/": dashboard_view,
            "/contas": contas_view,
            "/extrato": extrato_view,
            "/avulso": avulso_view,
            "/fixas": fixas_view,
            "/bancos": bancos_view,
            "/parcelas": parcelas_view,
            "/dividas": dividas_view,
        }

        # Busca a função da view correspondente ou carrega o dashboard por padrão
        view_fn = rotas.get(page.route)
        if view_fn:
            page.views.append(view_fn(page))
        else:
            page.views.append(dashboard_view(page))

        page.update()

    def view_pop(e):
        """Gerencia o comportamento do botão 'voltar' do navegador."""
        if len(page.views) > 1:
            page.views.pop()
            top_view = page.views[-1]
            page.go(top_view.route)

    # Vincula os eventos de navegação
    page.on_route_change = route_change
    page.on_view_pop = view_pop

    # Inicia a aplicação na tela de login
    page.go("/login")


if __name__ == "__main__":
    # Configuração específica para ambiente WEB (Render / Railway)
    # Obtém a porta definida pelo servidor ou utiliza a 8080 como padrão local
    porta = int(os.getenv("PORT", 8080))

    ft.app(
        target=main,
        view=ft.AppView.WEB_BROWSER,
        port=porta,
        host="0.0.0.0"  # Permite conexões externas no servidor
    )


## if __name__ == "__main__":
##     ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8080)

## - if __name__ == "__main__":
## -     ft.app(target=main)