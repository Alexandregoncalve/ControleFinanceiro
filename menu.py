import flet as ft
from utils import sair


def get_menu(page: ft.Page):
    nome_usuario = page.session.get("user_nome") or ""

    return ft.Container(
        content=ft.Row(
            [
                ft.Text("FINANÇA SIMPLES", size=20, weight="bold"),
                ft.Row([
                    ft.ElevatedButton("DASHBOARD",   on_click=lambda _: page.go("/"),          bgcolor="black",   color="white"),
                    ft.ElevatedButton("EXTRATO",      on_click=lambda _: page.go("/extrato"),   bgcolor="grey",    color="white"),
                    ft.ElevatedButton("CONTAS FIXAS", on_click=lambda _: page.go("/fixas"),     bgcolor="red",     color="white"),
                    ft.ElevatedButton("AVULSO",       on_click=lambda _: page.go("/avulso"),    bgcolor="orange",  color="white"),
                    ft.ElevatedButton("PARCELAS",     on_click=lambda _: page.go("/parcelas"),  bgcolor="#00838F", color="white"),
                    ft.ElevatedButton("CONTAS",       on_click=lambda _: page.go("/contas"),    bgcolor="blue",    color="white"),
                    ft.ElevatedButton("BANCOS",       on_click=lambda _: page.go("/bancos"),    bgcolor="green",   color="white"),
                    ft.ElevatedButton("DÍVIDAS",      on_click=lambda _: page.go("/dividas"),   bgcolor="#B71C1C", color="white"),
                    ft.ElevatedButton("CADASTRO",     on_click=lambda _: page.go("/cadastro"),  bgcolor="purple",  color="white"),
                ], spacing=8),
                ft.Row([
                    ft.Text(f"👤 {nome_usuario}", size=13, color=ft.colors.GREY_700),
                    ft.ElevatedButton(
                        "SAIR", bgcolor=ft.colors.RED_700, color="white",
                        icon=ft.icons.LOGOUT,
                        on_click=lambda _: sair(page),
                    ),
                ], spacing=8),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=15,
        bgcolor="#F5F5F5",
        border_radius=10,
    )