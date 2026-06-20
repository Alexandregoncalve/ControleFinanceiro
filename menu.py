import flet as ft
from utils import sair

MENU_GRUPOS = [
    ("GERAL", [
        ("Dashboard",   "/",             ft.icons.DASHBOARD_OUTLINED),
        ("Extrato",     "/extrato",      ft.icons.LIST_ALT_OUTLINED),
        ("Conciliação", "/conciliacao",  ft.icons.COMPARE_ARROWS),
    ]),
    ("LANÇAMENTOS", [
        ("Contas Fixas",      "/fixas",    ft.icons.REPEAT),
        ("Avulso",            "/avulso",   ft.icons.ADD_CIRCLE_OUTLINE),
        ("Parcelas",          "/parcelas", ft.icons.CALENDAR_TODAY_OUTLINED),
        ("Cartão de Crédito", "/cartao",   ft.icons.CREDIT_CARD_OUTLINED),
    ]),
    ("FINANCEIRO", [
        ("Contas",  "/contas",  ft.icons.ACCOUNT_BALANCE_WALLET_OUTLINED),
        ("Bancos",  "/bancos",  ft.icons.ACCOUNT_BALANCE_OUTLINED),
        ("Dívidas", "/dividas", ft.icons.WARNING_AMBER_OUTLINED),
    ]),
    ("CONFIGURAÇÕES", [
        ("Cadastro", "/cadastro", ft.icons.PERSON_OUTLINE),
    ]),
]

COR_SIDEBAR      = "#FFFFFF"
COR_SIDEBAR_ITEM = "#555555"
COR_ACTIVE_BG    = "#E3F2FD"
COR_ACTIVE_TEXT  = "#1565C0"
COR_ACTIVE_BORDA = "#1565C0"
COR_GRUPO_LABEL  = "#AAAAAA"
COR_TOPBAR       = "white"
LARGURA_SIDEBAR  = 210


def get_menu(page: ft.Page):
    nome_usuario = page.session.get("user_nome") or ""
    rota_atual   = page.route or "/"
    is_mobile    = (page.width or 1200) < 768

    # ── MENU MOBILE (mantido igual ao original) ───────────────────────────
    if is_mobile:
        titulo_pagina = "Finança Simples"
        for _, itens in MENU_GRUPOS:
            for label, rota, _ in itens:
                if rota == rota_atual:
                    titulo_pagina = label
                    break

        state    = {"aberto": False}
        menu_col = ft.Column([], spacing=0, visible=False)

        def fechar():
            state["aberto"] = False
            menu_col.visible = False
            page.update()

        def ir_para(rota):
            fechar()
            page.go(rota)

        def fazer_sair(_):
            fechar()
            sair(page)

        itens_mobile = []
        for grupo, itens in MENU_GRUPOS:
            itens_mobile.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16, vertical=6),
                    bgcolor="#F5F6FA",
                    content=ft.Text(grupo, size=10, weight="bold", color="#888"),
                )
            )
            for label, rota, icone in itens:
                def make_click(r):
                    def click(_): ir_para(r)
                    return click
                itens_mobile.append(
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=16, vertical=12),
                        border=ft.border.only(bottom=ft.BorderSide(1, "#EEEEEE")),
                        bgcolor="white",
                        content=ft.Row([
                            ft.Icon(icone, size=16, color="#1565C0"),
                            ft.Text(label, size=14, expand=True),
                            ft.Icon(ft.icons.CHEVRON_RIGHT, size=14, color="#AAAAAA"),
                        ], spacing=10),
                        on_click=make_click(rota),
                        ink=True,
                    )
                )

        itens_mobile.append(
            ft.Container(
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                bgcolor="#FFEBEE",
                content=ft.Row([
                    ft.Icon(ft.icons.LOGOUT, size=16, color=ft.colors.RED_700),
                    ft.Text("Sair", size=14, color=ft.colors.RED_700),
                ], spacing=10),
                on_click=fazer_sair,
                ink=True,
            )
        )
        menu_col.controls = itens_mobile

        def toggle_menu(_):
            state["aberto"] = not state["aberto"]
            menu_col.visible = state["aberto"]
            page.update()

        barra = ft.Container(
            bgcolor=COR_SIDEBAR,
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            content=ft.Row([
                ft.IconButton(
                    icon=ft.icons.MENU, icon_color="white",
                    icon_size=24, on_click=toggle_menu,
                    padding=ft.padding.all(4),
                ),
                ft.Text(titulo_pagina, size=15, weight="bold", color="white", expand=True),
                ft.Text(nome_usuario[:15], size=11, color=ft.colors.BLUE_100),
            ]),
        )
        return ft.Column(controls=[barra, menu_col], spacing=0)

    # ── MENU DESKTOP — SIDEBAR LATERAL ───────────────────────────────────
    iniciais = "".join(p[0].upper() for p in nome_usuario.split()[:2]) if nome_usuario else "?"

    def nav_item(label, rota, icone):
        ativo = rota_atual == rota
        return ft.Container(
            content=ft.Container(
                content=ft.Row([
                    ft.Icon(icone, size=16,
                            color=COR_ACTIVE_TEXT if ativo else COR_SIDEBAR_ITEM),
                    ft.Text(label, size=13,
                            color=COR_ACTIVE_TEXT if ativo else COR_SIDEBAR_ITEM,
                            weight="bold" if ativo else "normal"),
                ], spacing=10),
                padding=ft.padding.symmetric(horizontal=14, vertical=9),
                bgcolor=COR_ACTIVE_BG if ativo else "transparent",
                border_radius=20,
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=2),
            on_click=lambda _, r=rota: page.go(r),
            ink=True,
        )

    grupos_col = []
    for grupo, itens in MENU_GRUPOS:
        grupos_col.append(
            ft.Container(
                content=ft.Text(grupo, size=10, weight="bold", color=COR_GRUPO_LABEL),
                padding=ft.padding.only(left=16, top=14, bottom=4),
            )
        )
        for label, rota, icone in itens:
            grupos_col.append(nav_item(label, rota, icone))

    sidebar = ft.Container(
        width=LARGURA_SIDEBAR,
        bgcolor=COR_SIDEBAR,
        border=ft.border.only(right=ft.BorderSide(1, "#E0E0E0")),
        content=ft.Column([
            # Logo
            ft.Container(
                content=ft.Row([
                    ft.Container(
                        width=32, height=32, border_radius=8,
                        gradient=ft.LinearGradient(
                            begin=ft.alignment.top_left,
                            end=ft.alignment.bottom_right,
                            colors=["#1565C0", "#2E7D32"],
                        ),
                        content=ft.Icon(ft.icons.SHOW_CHART, color="white", size=18),
                        alignment=ft.alignment.center,
                    ),
                    ft.Column([
                        ft.Row([
                            ft.Text("Finança", size=13, weight="bold", color="#1565C0"),
                            ft.Text("Simples", size=13, weight="bold", color="#2E7D32"),
                        ], spacing=4),
                    ], spacing=0),
                ], spacing=10),
                padding=ft.padding.symmetric(horizontal=16, vertical=18),
                border=ft.border.only(bottom=ft.BorderSide(1, "#E0E0E0")),
            ),

            # Itens de navegação
            ft.Container(
                content=ft.Column(grupos_col, spacing=0),
                expand=True,
            ),

            # Rodapé com usuário e sair
            ft.Container(
                content=ft.Row([
                    ft.Container(
                        width=28, height=28, border_radius=14,
                        gradient=ft.LinearGradient(
                            begin=ft.alignment.top_left,
                            end=ft.alignment.bottom_right,
                            colors=["#1565C0", "#2E7D32"],
                        ),
                        content=ft.Text(iniciais, size=11, weight="bold", color="white"),
                        alignment=ft.alignment.center,
                    ),
                    ft.Text(
                        nome_usuario[:18] if nome_usuario else "Usuário",
                        size=12, color="#555555", expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.icons.LOGOUT,
                        icon_color="#C62828",
                        icon_size=16,
                        tooltip="Sair",
                        on_click=lambda _: sair(page),
                        padding=ft.padding.all(4),
                    ),
                ], spacing=8),
                padding=ft.padding.symmetric(horizontal=12, vertical=12),
                border=ft.border.only(top=ft.BorderSide(1, "#E0E0E0")),
            ),
        ], spacing=0, expand=True),
        expand=False,
    )

    return sidebar


def layout_com_sidebar(page: ft.Page, conteudo: ft.Control) -> ft.View:
    """
    Retorna um ft.View completo com sidebar lateral + conteúdo.
    Use no lugar de ft.View(...) em todas as views.
    """
    is_mobile = (page.width or 1200) < 768

    if is_mobile:
        return ft.View(
            route=page.route,
            bgcolor="#F5F6FA",
            padding=0,
            scroll=ft.ScrollMode.ALWAYS,
            controls=[
                get_menu(page),
                conteudo,
            ],
        )

    return ft.View(
        route=page.route,
        bgcolor="#F5F6FA",
        padding=0,
        controls=[
            ft.Row([
                get_menu(page),
                ft.Container(expand=True, content=conteudo),
            ], spacing=0, expand=True, vertical_alignment=ft.CrossAxisAlignment.START),
        ],
    )