import flet as ft
from datetime import datetime
from database import autenticar, get_connection, get_cursor


def login_view(page: ft.Page):
    login_input = ft.TextField(
        label="E-mail ou usuário", width=300, border_radius=10,
        on_submit=lambda e: fazer_login(e)
    )
    senha_input = ft.TextField(
        label="Senha", width=300, border_radius=10,
        password=True, can_reveal_password=True,
        on_submit=lambda e: fazer_login(e)
    )
    erro_text = ft.Text("", color=ft.colors.RED_600, size=13)
    carregando = ft.ProgressRing(width=24, height=24, visible=False)

    def verificar_fixas_pendentes(uid):
        try:
            mes_str = datetime.now().strftime("%m/%Y")
            conn = get_connection()
            cur = get_cursor(conn)
            cur.execute("""
                SELECT s.nome FROM subcontas s
                WHERE s.fixa = 1
                AND s.usuario_id = %s
                AND s.id NOT IN (
                    SELECT subconta_id FROM transacoes
                    WHERE data LIKE %s AND usuario_id = %s
                )
                ORDER BY s.nome
            """, (uid, f"%{mes_str}", uid))
            pendentes = [r["nome"] for r in cur.fetchall()]
            conn.close()
            return pendentes
        except Exception as ex:
            print(f"[login] verificar_fixas: {ex}")
            return []

    def mostrar_alerta_fixas(pendentes):
        # Definição das funções internas primeiro
        def ir_fixas(e):
            dlg.open = False
            page.update()
            page.go("/fixas")

        def ir_dashboard(e):
            dlg.open = False
            page.update()
            # Se já estivermos no /, apenas fechamos
            if page.route != "/":
                page.go("/")

        lista_contas = ft.Column(
            controls=[
                ft.Row([
                    ft.Icon(ft.icons.WARNING_AMBER, color=ft.colors.ORANGE_700, size=16),
                    ft.Text(nome, size=13),
                ], spacing=6)
                for nome in pendentes
            ],
            spacing=4,
            scroll=ft.ScrollMode.AUTO,
            height=min(len(pendentes) * 32, 200),
        )

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.icons.NOTIFICATION_IMPORTANT, color=ft.colors.ORANGE_700),
                ft.Text("⚠️ Contas Fixas Pendentes", size=16, weight="bold"),
            ], spacing=8),
            content=ft.Column([
                ft.Text(
                    f"Você tem {len(pendentes)} conta(s) fixa(s) não lançada(s) este mês:",
                    size=13, color=ft.colors.GREY_700,
                ),
                ft.Divider(),
                lista_contas,
                ft.Divider(),
                ft.Text("Deseja ir para a tela de Contas Fixas agora?",
                        size=13, weight="bold"),
            ], spacing=8, tight=True),
            actions=[
                ft.TextButton("Agora não", on_click=ir_dashboard),
                ft.ElevatedButton(
                    "📋 IR PARA CONTAS FIXAS",
                    bgcolor=ft.colors.ORANGE_700,
                    color=ft.colors.WHITE,
                    on_click=ir_fixas,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # O segredo: adicionamos ao overlay e abrimos
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def fazer_login(e):
        erro_text.value = ""
        carregando.visible = True
        page.update()

        login_val = login_input.value.strip()
        senha_val = senha_input.value

        if not login_val or not senha_val:
            erro_text.value = "Preencha e-mail e senha."
            carregando.visible = False
            page.update()
            return

        usuario = autenticar(login_val, senha_val)
        carregando.visible = False

        if usuario:
            # 1. Guarda os dados na sessão
            page.session.set("user_id", usuario["id"])
            page.session.set("user_nome", usuario["nome"])

            # 2. Busca as pendências
            pendentes = verificar_fixas_pendentes(usuario["id"])

            # 3. NAVEGA PRIMEIRO (Isso limpa a view de login)
            page.go("/")

            # 4. EXIBE O ALERTA POR ÚLTIMO
            # Como o alerta é modal e está no overlay da page,
            # ele persistirá sobre a nova tela carregada
            if pendentes:
                mostrar_alerta_fixas(pendentes)
        else:
            erro_text.value = "E-mail ou senha incorretos."
            senha_input.value = ""
            senha_input.focus()
            page.update()

    def ir_cadastro(e):
        page.go("/cadastro")

    return ft.View(
        route="/login",
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Container(
                expand=True,
                alignment=ft.alignment.center,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12,
                    controls=[
                        ft.Icon(ft.icons.ACCOUNT_BALANCE, size=72, color=ft.colors.BLUE_700),
                        ft.Text("FINANÇA SIMPLES", size=26, weight="bold", color="#1565C0"),
                        ft.Text("Acesse sua conta", size=14, color=ft.colors.GREY_600),
                        ft.Divider(height=10, color="transparent"),
                        login_input,
                        senha_input,
                        erro_text,
                        carregando,
                        ft.ElevatedButton(
                            "ENTRAR", width=300, height=45,
                            bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE,
                            on_click=fazer_login,
                        ),
                        ft.Divider(height=8, color="transparent"),
                        ft.Row([
                            ft.Text("Não tem conta?", size=13, color=ft.colors.GREY_600),
                            ft.TextButton(
                                "Criar conta",
                                on_click=ir_cadastro,
                                style=ft.ButtonStyle(color="#1565C0"),
                            ),
                        ], alignment=ft.MainAxisAlignment.CENTER, spacing=4),
                    ],
                ),
            )
        ],
    )