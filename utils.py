import flet as ft
from database import get_connection


def formatar_moeda_input(e):
    if not e.control.value:
        return
    v = e.control.value.replace("R$", "").strip()

    if "," in v:
        try:
            valor = float(v.replace(".", "").replace(",", "."))
            e.control.value = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            e.control.value = "0,00"
    else:
        v_limpo = v.replace(".", "").replace(",", "")
        try:
            valor = float(v_limpo)
            e.control.value = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            e.control.value = "0,00"

    e.control.update()


def limpar_valor(txt: str) -> float:
    if not txt:
        return 0.0
    txt = txt.strip().replace("R$", "").strip()
    try:
        if "," in txt and "." in txt:
            return float(txt.replace(".", "").replace(",", "."))
        elif "," in txt:
            return float(txt.replace(",", "."))
        elif "." in txt:
            partes = txt.split(".")
            if len(partes[-1]) == 2:
                return float(txt)
            else:
                return float(txt.replace(".", ""))
        else:
            return float(txt)
    except ValueError:
        return 0.0


def verificar_admin(page: ft.Page, acao):
    """Exibe diálogo de confirmação antes de executar ação destrutiva."""

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar Exclusão"),
        content=ft.Text("Tem certeza que deseja apagar este registro?\nEsta ação não pode ser desfeita."),
    )

    def confirmar(e):
        dlg.open = False
        page.update()
        acao()

    def cancelar(e):
        dlg.open = False
        page.update()

    dlg.actions = [
        ft.TextButton("Cancelar", on_click=cancelar),
        ft.ElevatedButton(
            "Excluir", bgcolor=ft.colors.RED_700, color=ft.colors.WHITE,
            on_click=confirmar
        ),
    ]
    dlg.actions_alignment = ft.MainAxisAlignment.END

    page.overlay.append(dlg)
    dlg.open = True
    page.update()


def sair(page: ft.Page):
    """Limpa sessão e redireciona para login."""
    page.session.clear()
    page.go("/login")