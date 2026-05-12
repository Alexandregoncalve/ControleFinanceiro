import flet as ft
from menu import get_menu
from database import db_session  # Usando a função de segurança que você já tem
from utils import limpar_valor, formatar_moeda_input
from datetime import datetime

# Paleta de cores para os cards de banco
CORES_BANCO = [
    "#1565C0",  # Azul
    "#2E7D32",  # Verde
    "#6A1B9A",  # Roxo
    "#00838F",  # Ciano
    "#E65100",  # Laranja
    "#AD1457",  # Rosa
    "#4527A0",  # Índigo
    "#37474F",  # Cinza escuro
]


def bancos_view(page: ft.Page):
    uid = page.session.get("user_id")
    state = {"editing_banco_id": None, "editing_cartao_id": None}

    nome_banco_f = ft.TextField(label="Nome do Banco", width=250)
    saldo_inicial_f = ft.TextField(label="Saldo Inicial", width=180, on_blur=formatar_moeda_input)
    # NOVO CAMPO: DATA INICIAL
    data_inicial_f = ft.TextField(
        label="Data Inicial (DD/MM/AAAA)",
        width=180,
        value=datetime.now().strftime("%d/%m/%Y")
    )
    msg_banco = ft.Text("", size=13)

    nome_cartao_f = ft.TextField(label="Nome do Cartão", width=200)
    tipo_cartao_f = ft.Dropdown(
        label="Tipo", width=150,
        options=[
            ft.dropdown.Option("Crédito"),
            ft.dropdown.Option("Débito"),
            ft.dropdown.Option("Ambos"),
        ]
    )
    limite_f = ft.TextField(label="Limite (ex: 5.000,00)", width=180, on_blur=formatar_moeda_input)
    banco_dd = ft.Dropdown(label="Banco vinculado", width=220, options=[])
    msg_cartao = ft.Text("", size=13)

    lista_bancos_col = ft.Column([], spacing=12)
    lista_cartoes_col = ft.Column([], spacing=12)

    def fmt(v):
        return f"R$ {v:_.2f}".replace(".", ",").replace("_", ".")

    def carregar_banco_dd():
        try:
            with db_session() as cur:
                cur.execute("SELECT id, nome_banco FROM bancos WHERE usuario_id=%s ORDER BY nome_banco", (uid,))
                bancos = cur.fetchall()
            banco_dd.options = [ft.dropdown.Option(str(b[0]), b[1]) for b in bancos]
            page.update()
        except Exception as ex:
            print(f"[bancos] carregar_banco_dd: {ex}")

    def card_banco(b, cor):
        # b[0]=id, b[1]=nome, b[2]=saldo, b[3]=data
        return ft.Container(
            width=280,
            border_radius=14,
            bgcolor=cor,
            padding=ft.padding.all(18),
            shadow=ft.BoxShadow(blur_radius=10, color=ft.colors.with_opacity(0.22, "black"), offset=ft.Offset(2, 4)),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.ACCOUNT_BALANCE, color="white", size=28),
                    ft.Text(b[1], color="white", weight="bold", size=16, expand=True),
                ], spacing=10),
                ft.Divider(color=ft.colors.with_opacity(0.3, "white"), height=18),
                ft.Row([
                    ft.Column([
                        ft.Text("Saldo Inicial", color=ft.colors.with_opacity(0.75, "white"), size=11),
                        ft.Text(fmt(b[2] or 0), color="white", size=20, weight="bold"),
                    ]),
                    ft.Column([
                        ft.Text("Início", color=ft.colors.with_opacity(0.75, "white"), size=11),
                        ft.Text(b[3] if len(b) > 3 else "—", color="white", size=13),
                    ], alignment=ft.MainAxisAlignment.END)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(color=ft.colors.with_opacity(0.3, "white"), height=18),
                ft.Row([
                    ft.TextButton("✏️ Editar", style=ft.ButtonStyle(color="white"),
                                  on_click=lambda _, b=b: preparar_edicao_banco(b)),
                    ft.TextButton("🗑️ Excluir", style=ft.ButtonStyle(color=ft.colors.RED_200),
                                  on_click=lambda _, bid=b[0]: excluir_banco(bid)),
                ], alignment=ft.MainAxisAlignment.END),
            ], spacing=4),
        )

    def card_cartao(c, banco_map):
        tipo_cor = {"Crédito": "#E65100", "Débito": "#2E7D32", "Ambos": "#6A1B9A"}.get(c[2], "#37474F")
        return ft.Container(
            width=280,
            border_radius=14,
            bgcolor=tipo_cor,
            padding=ft.padding.all(18),
            shadow=ft.BoxShadow(blur_radius=10, color=ft.colors.with_opacity(0.22, "black"), offset=ft.Offset(2, 4)),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.CREDIT_CARD, color="white", size=28),
                    ft.Text(c[1], color="white", weight="bold", size=16, expand=True),
                ], spacing=10),
                ft.Container(bgcolor=ft.colors.with_opacity(0.2, "white"), border_radius=6,
                             padding=ft.padding.symmetric(horizontal=8, vertical=4),
                             content=ft.Text(c[2], color="white", size=11, weight="bold")),
                ft.Divider(color=ft.colors.with_opacity(0.3, "white"), height=18),
                ft.Row([
                    ft.Column([ft.Text("Limite", color=ft.colors.with_opacity(0.75, "white"), size=11),
                               ft.Text(fmt(c[3] or 0), color="white", size=16, weight="bold")]),
                    ft.Column([ft.Text("Banco", color=ft.colors.with_opacity(0.75, "white"), size=11),
                               ft.Text(banco_map.get(c[4], "—"), color="white", size=13)]),
                ], spacing=30),
                ft.Divider(color=ft.colors.with_opacity(0.3, "white"), height=18),
                ft.Row([
                    ft.TextButton("✏️ Editar", style=ft.ButtonStyle(color="white"),
                                  on_click=lambda _, c=c: preparar_edicao_cartao(c)),
                    ft.TextButton("🗑️ Excluir", style=ft.ButtonStyle(color=ft.colors.RED_200),
                                  on_click=lambda _, cid=c[0]: excluir_cartao(cid)),
                ], alignment=ft.MainAxisAlignment.END),
            ], spacing=4),
        )

    def carregar_listas():
        try:
            with db_session() as cur:
                cur.execute(
                    "SELECT id, nome_banco, saldo_inicial, COALESCE(data_criacao, '') FROM bancos WHERE usuario_id=%s ORDER BY nome_banco",
                    (uid,))
                bancos = cur.fetchall()
                cur.execute(
                    "SELECT id, nome_cartao, tipo, limite, banco_id FROM cartoes WHERE usuario_id=%s ORDER BY nome_cartao",
                    (uid,))
                cartoes = cur.fetchall()

            banco_map = {b[0]: b[1] for b in bancos}
            lista_bancos_col.controls.clear()
            lista_bancos_col.controls.append(ft.Row(
                [card_banco(b, CORES_BANCO[i % len(CORES_BANCO)]) for i, b in enumerate(bancos)] if bancos else [
                    ft.Text("Nenhum banco cadastrado.", color=ft.colors.GREY_500, italic=True)], wrap=True, spacing=16))

            lista_cartoes_col.controls.clear()
            lista_cartoes_col.controls.append(ft.Row([card_cartao(c, banco_map) for c in cartoes] if cartoes else [
                ft.Text("Nenhum cartão cadastrado.", color=ft.colors.GREY_500, italic=True)], wrap=True, spacing=16))

            carregar_banco_dd()
            page.update()
        except Exception as ex:
            print(f"[bancos] carregar_listas: {ex}")

    def salvar_banco(e):
        nome = nome_banco_f.value.strip()
        saldo = limpar_valor(saldo_inicial_f.value.strip() or "0")
        data = data_inicial_f.value.strip()
        if not nome:
            msg_banco.value = "⚠️ Informe o nome do banco.";
            msg_banco.color = ft.colors.ORANGE_700;
            page.update();
            return
        try:
            with db_session() as cur:
                if state["editing_banco_id"]:
                    cur.execute(
                        "UPDATE bancos SET nome_banco=%s, saldo_inicial=%s, data_criacao=%s WHERE id=%s AND usuario_id=%s",
                        (nome, saldo, data, state["editing_banco_id"], uid))
                    state["editing_banco_id"] = None
                else:
                    cur.execute(
                        "INSERT INTO bancos (nome_banco, saldo_inicial, data_criacao, usuario_id) VALUES (%s, %s, %s, %s)",
                        (nome, saldo, data, uid))
            msg_banco.value = "✅ Salvo com sucesso!";
            msg_banco.color = ft.colors.GREEN_700
            nome_banco_f.value = saldo_inicial_f.value = ""
            data_inicial_f.value = datetime.now().strftime("%d/%m/%Y")
            btn_salvar_banco.text = "SALVAR BANCO"
            carregar_listas()
        except Exception as ex:
            msg_banco.value = "❌ Erro ao salvar banco.";
            msg_banco.color = ft.colors.RED_700;
            page.update()

    def preparar_edicao_banco(b):
        state["editing_banco_id"] = b[0]
        nome_banco_f.value = b[1]
        saldo_inicial_f.value = f'{b[2] or 0:_.2f}'.replace(".", ",").replace("_", ".")
        data_inicial_f.value = b[3] if b[3] else datetime.now().strftime("%d/%m/%Y")
        btn_salvar_banco.text = "ATUALIZAR BANCO"
        page.update()

    def excluir_banco(bid):
        try:
            with db_session() as cur:
                cur.execute("DELETE FROM bancos WHERE id=%s AND usuario_id=%s", (bid, uid))
            carregar_listas()
        except:
            pass

    def salvar_cartao(e):
        nome, tipo, limite, bid = nome_cartao_f.value.strip(), tipo_cartao_f.value, limpar_valor(
            limite_f.value.strip() or "0"), banco_dd.value
        if not nome or not tipo or not bid:
            msg_cartao.value = "⚠️ Preencha todos os campos.";
            msg_cartao.color = ft.colors.ORANGE_700;
            page.update();
            return
        try:
            with db_session() as cur:
                if state["editing_cartao_id"]:
                    cur.execute(
                        "UPDATE cartoes SET nome_cartao=%s, tipo=%s, limite=%s, banco_id=%s WHERE id=%s AND usuario_id=%s",
                        (nome, tipo, limite, int(bid), state["editing_cartao_id"], uid))
                    state["editing_cartao_id"] = None
                else:
                    cur.execute(
                        "INSERT INTO cartoes (nome_cartao, tipo, limite, banco_id, usuario_id) VALUES (%s, %s, %s, %s, %s)",
                        (nome, tipo, limite, int(bid), uid))
            msg_cartao.value = "✅ Cartão salvo!";
            msg_cartao.color = ft.colors.GREEN_700
            nome_cartao_f.value = limite_f.value = "";
            tipo_cartao_f.value = banco_dd.value = None
            btn_salvar_cartao.text = "SALVAR CARTÃO"
            carregar_listas()
        except:
            msg_cartao.value = "❌ Erro ao salvar cartão.";
            msg_cartao.color = ft.colors.RED_700;
            page.update()

    def preparar_edicao_cartao(c):
        state["editing_cartao_id"] = c[0]
        nome_cartao_f.value, tipo_cartao_f.value, limite_f.value, banco_dd.value = c[1], c[
            2], f'{c[3] or 0:_.2f}'.replace(".", ",").replace("_", "."), str(c[4])
        btn_salvar_cartao.text = "ATUALIZAR CARTÃO";
        page.update()

    def excluir_cartao(cid):
        try:
            with db_session() as cur:
                cur.execute("DELETE FROM cartoes WHERE id=%s AND usuario_id=%s", (cid, uid))
            carregar_listas()
        except:
            pass

    btn_salvar_banco = ft.ElevatedButton("SALVAR BANCO", bgcolor="#1565C0", color="white", on_click=salvar_banco)
    btn_salvar_cartao = ft.ElevatedButton("SALVAR CARTÃO", bgcolor="#E65100", color="white", on_click=salvar_cartao)

    carregar_listas()

    conteudo = ft.Column([
        ft.Row([ft.Icon(ft.icons.ACCOUNT_BALANCE, color="#1565C0", size=30),
                ft.Text("BANCOS E CARTÕES", size=22, weight="bold", color="#1565C0")], spacing=10),
        ft.Divider(),
        ft.Container(
            bgcolor="#E3F2FD", border_radius=10, padding=16,
            content=ft.Column([
                ft.Text("🏦 Cadastrar / Editar Banco", size=15, weight="bold", color="#1565C0"),
                ft.Row([nome_banco_f, saldo_inicial_f, data_inicial_f, btn_salvar_banco], wrap=True, spacing=10),
                msg_banco,
            ], spacing=10)
        ),
        ft.Text("Bancos Cadastrados", size=15, weight="bold", color="#1565C0"),
        lista_bancos_col,
        ft.Divider(),
        ft.Container(
            bgcolor="#FFF3E0", border_radius=10, padding=16,
            content=ft.Column([
                ft.Text("💳 Cadastrar / Editar Cartão", size=15, weight="bold", color="#E65100"),
                ft.Row([nome_cartao_f, tipo_cartao_f, limite_f, banco_dd, btn_salvar_cartao], wrap=True, spacing=10),
                msg_cartao,
            ], spacing=10)
        ),
        ft.Text("Cartões Cadastrados", size=15, weight="bold", color="#E65100"),
        lista_cartoes_col,
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.View(
        route="/bancos",
        controls=[get_menu(page), ft.Divider(),
                  ft.Container(padding=ft.padding.symmetric(horizontal=24, vertical=16), expand=True, content=conteudo)]
    )