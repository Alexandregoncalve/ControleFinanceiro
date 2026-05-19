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

ROTAS_PUBLICAS = {"/login", "/cadastro"}

ROTAS = {
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

    def carregar_rota(rota: str):
        page.views.clear()
        if rota not in ROTAS_PUBLICAS and not logado():
            page.views.append(login_view(page))
            page.update()
            return
        view_fn = ROTAS.get(rota, dashboard_view)
        page.views.append(view_fn(page))
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
        rota_atual = page.route
        carregar_rota(rota_atual)

    page.reload_view = reload_view
    page.go("/login")


# ── FastAPI com Flet montado + endpoint PDF ───────────────────────────────────
app = FastAPI()

@app.get("/pdf/{nome_arquivo}")
async def servir_pdf(nome_arquivo: str):
    """Serve PDFs gerados pelo extrato."""
    caminho = os.path.join(tempfile.gettempdir(), nome_arquivo)
    if not os.path.exists(caminho):
        return HTMLResponse("<h2>PDF não encontrado ou expirado.</h2>", status_code=404)
    return FileResponse(
        caminho,
        media_type="application/pdf",
        filename=nome_arquivo,
    )

# Monta Flet dentro do FastAPI
app.mount("/", flet_fastapi.app(main))


if __name__ == "__main__":
    porta = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=porta)