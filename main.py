import flet as ft
import flet.fastapi as flet_fastapi
import os
import tempfile
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse

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
from views.conciliacao import conciliacao_view
from views.cartao import cartao_view
from menu import get_menu

# Rotas sem sidebar (tela cheia)
ROTAS_PUBLICAS = {"/login"}
# Rotas que não exigem login
ROTAS_SEM_AUTH  = {"/login", "/cadastro"}

ROTAS = {
    "/login":       login_view,
    "/cadastro":    cadastro_view,
    "/":            dashboard_view,
    "/contas":      contas_view,
    "/extrato":     extrato_view,
    "/avulso":      avulso_view,
    "/fixas":       fixas_view,
    "/bancos":      bancos_view,
    "/parcelas":    parcelas_view,
    "/dividas":     dividas_view,
    "/conciliacao": conciliacao_view,
    "/cartao":      cartao_view,
}

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")


def envolver_com_sidebar(page: ft.Page, view: ft.View) -> ft.View:
    """Envolve o conteúdo da view com sidebar lateral."""
    if view.route in ROTAS_PUBLICAS:
        return view

    is_mobile = (page.width or 1200) < 768

    # Remove o menu (sidebar ou menu antigo) do primeiro controle da view
    controles = list(view.controls or [])
    if controles:
        p = controles[0]
        eh_menu = False

        # Caso 1: sidebar novo — Container branco com Column que tem itens de nav
        if isinstance(p, ft.Container) and getattr(p, 'bgcolor', '') in ("#FFFFFF", "#F5F5F5", "#0D2137"):
            eh_menu = True

        # Caso 2: sidebar novo — Container com width=210 (largura do sidebar)
        if isinstance(p, ft.Container) and getattr(p, 'width', 0) == 210:
            eh_menu = True

        # Caso 3: menu mobile antigo — Column com Container azul como primeiro filho
        if isinstance(p, ft.Column):
            filhos = getattr(p, 'controls', [])
            if filhos and isinstance(filhos[0], ft.Container) and getattr(filhos[0], 'bgcolor', '') == "#1565C0":
                eh_menu = True

        # Caso 4: Row que já é o layout com sidebar (duplicação) — não reprocessar
        if isinstance(p, ft.Row) and len(getattr(p, 'controls', [])) >= 2:
            primeiro_filho = p.controls[0]
            if isinstance(primeiro_filho, ft.Container) and getattr(primeiro_filho, 'width', 0) == 210:
                # Já está com sidebar — retorna a view como está
                return view

        if eh_menu:
            controles = controles[1:]

    if is_mobile:
        return ft.View(
            route=view.route,
            bgcolor=view.bgcolor or "#F5F6FA",
            padding=0,
            scroll=ft.ScrollMode.ALWAYS,
            controls=[get_menu(page)] + controles,
        )

    # Desktop: Row com sidebar fixo + conteúdo scrollável à direita
    return ft.View(
        route=view.route,
        bgcolor=view.bgcolor or "#F5F6FA",
        padding=0,
        controls=[
            ft.Row(
                controls=[
                    # Sidebar fixo
                    get_menu(page),
                    # Conteúdo da view original, scrollável
                    ft.Column(
                        controls=controles,
                        scroll=ft.ScrollMode.ALWAYS,
                        expand=True,
                        spacing=0,
                    ),
                ],
                spacing=0,
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        ],
    )


def main(page: ft.Page):
    page.title         = "Finança Simples"
    page.window_width  = 1200
    page.window_height = 900
    page.theme_mode    = ft.ThemeMode.LIGHT
    page.favicon       = "/icons/icon-32x32.png"
    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[ft.Locale("pt", "BR")],
        current_locale=ft.Locale("pt", "BR"),
    )

    init_db()

    def logado() -> bool:
        return page.session.get("user_id") is not None

    def carregar_rota(rota: str):
        page.views.clear()
        if rota not in ROTAS_SEM_AUTH and not logado():
            page.views.append(login_view(page))
            page.update()
            return
        view_fn = ROTAS.get(rota, dashboard_view)
        view_original = view_fn(page)
        view_final = envolver_com_sidebar(page, view_original)
        page.views.append(view_final)
        page.update()

    def route_change(route):
        rota = page.route
        if rota == "/_reload":
            return
        carregar_rota(rota)

    def view_pop(e):
        if len(page.views) > 1:
            page.views.pop()
            top_view = page.views[-1]
            page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop     = view_pop

    def reload_view():
        carregar_rota(page.route)

    page.reload_view = reload_view
    page.go("/login")


# ── FastAPI + Flet ────────────────────────────────────────────────────────────
app = FastAPI()


@app.get("/pdf/{nome_arquivo}")
async def servir_pdf(nome_arquivo: str):
    for pasta in [os.path.join(tempfile.gettempdir(), "pdfs"), tempfile.gettempdir()]:
        caminho = os.path.join(pasta, nome_arquivo)
        if os.path.exists(caminho):
            return FileResponse(caminho, media_type="application/pdf", filename=nome_arquivo)
    return HTMLResponse("<h2>PDF nao encontrado ou expirado.</h2>", status_code=404)


@app.get("/export/{nome_arquivo}")
async def servir_export(nome_arquivo: str):
    pasta_exports = os.path.join(tempfile.gettempdir(), "exports")
    caminho = os.path.join(pasta_exports, nome_arquivo)
    if os.path.exists(caminho):
        if nome_arquivo.endswith(".xlsx"):
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            headers = {"Content-Disposition": f"attachment; filename=\"{nome_arquivo}\""}
        else:
            media_type = "application/pdf"
            headers = {"Content-Disposition": f"inline; filename=\"{nome_arquivo}\""}
        return FileResponse(caminho, media_type=media_type,
                            filename=nome_arquivo, headers=headers)
    return HTMLResponse("<h2>Arquivo nao encontrado ou expirado.</h2>", status_code=404)


UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/", flet_fastapi.app(main, assets_dir=ASSETS_DIR, upload_dir=UPLOAD_DIR))

if __name__ == "__main__":
    porta = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=porta)