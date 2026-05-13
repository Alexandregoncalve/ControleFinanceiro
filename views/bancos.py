import flet as ft
from menu import get_menu
from database import db_session
from utils import limpar_valor, formatar_moeda_input
from datetime import datetime

CORES_BANCO = ["#1565C0", "#2E7D32", "#6A1B9A", "#00838F", "#E65100", "#AD1457", "#4527A0", "#37474F"]


def bancos_view(page: ft.Page):
    uid = page.session.get("user_id")
    state = {"editing_banco_id": None, "editing_cartao_id": None}

    # --- NOVOS CAMPOS ---
    nome_banco_f = ft.TextField(label="Nome do Banco", width=250)
    agencia_f = ft.TextField(label="Agência", width=120)  # Novo
    conta_f = ft.TextField(label="Nº Conta", width=150)  # Novo
    saldo_inicial_f = ft.TextField(label="Saldo Inicial", width=180, on_blur=formatar_moeda_input)
    data_inicial_f = ft.TextField(
        label="Data Inicial (DD/MM/AAAA)",
        width=180,
        value=datetime.now().strftime("%d/%m/%Y")
    )
    msg_banco = ft.Text("", size=13)

    nome_cartao_f = ft.TextField(label="Nome do Cartão", width=200)
    tipo_cartao_f = ft.Dropdown(
        label="Tipo", width=150,
        options=[ft.dropdown.Option("Crédito"), ft.dropdown.Option("Débito"), ft.dropdown.Option("Ambos")]
    )
    limite_f = ft.TextField(label="Limite (ex: 5.000,00)", width=180, on_blur=formatar_moeda_input)
    banco_dd = ft.Dropdown(label="Banco vinculado", width=220, options=[])
    msg_cartao = ft.Text("", size=13)

    lista_bancos_col = ft.Column([], spacing=12)
    lista_cartoes_col = ft.Column([], spacing=12)

    def fmt(v):
        try:
            return f"R$ {float(v):_.2f}".replace(".", ",").replace("_", ".")
        except:
            return "R$ 0,00"

    def carregar_banco_dd():
        try:
            with db_session() as cur:
                cur.execute("SELECT id, nome_banco FROM bancos WHERE usuario_id=%s ORDER BY nome_banco", (uid,))
                bancos = cur.fetchall()
            banco_dd.options = [ft.dropdown.Option(str(b['id']), b['nome_banco']) for b in bancos]
            page.update()
        except:
            pass

    def card_banco(b, cor):
        return ft.Container(
            width=300,
            border_radius=14,
            bgcolor=cor,
            padding=ft.padding.all(18),
            shadow=ft.BoxShadow(blur_radius=10, color=ft.colors.with_opacity(0.22, "black"), offset=ft.Offset(2, 4)),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.ACCOUNT_BALANCE, color="white", size=28),
                    ft.Text(b['nome_banco'], color="white", weight="bold", size=16, expand=True),
                ], spacing=10),
                # Exibição Agência e Conta
                ft.Text(f"Ag: {b['agencia'] or '—'} | Cta: {b['numero_conta'] or '—'}", color="white", size=12),
                ft.Divider(color=ft.colors.with_opacity(0.3, "white"), height=18),
                ft.Row([
                    ft.Column([
                        ft.Text("Saldo Inicial", color=ft.colors.with_opacity(0.75, "white"), size=11),
                        ft.Text(fmt(b['saldo_inicial'] or 0), color="white", size=20, weight="bold"),
                    ]),
                    ft.Column([
                        ft.Text("Início", color=ft.colors.with_opacity(0.75, "white"), size=11),
                        ft.Text(b['data_criacao'] if b['data_criacao'] else "—", color="white", size=11),
                    ], horizontal_alignment=ft.CrossAxisAlignment.END)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([
                    ft.TextButton("✏️ Editar", style=ft.ButtonStyle(color="white"),
                                  on_click=lambda _, b=b: preparar_edicao_banco(b)),
                    ft.TextButton("🗑️ Excluir", style=ft.ButtonStyle(color=ft.colors.RED_200),
                                  on_click=lambda _, bid=b['id']: excluir_banco(bid)),
                ], alignment=ft.MainAxisAlignment.END),
            ], spacing=4),
        )

    def carregar_listas():
        try:
            with db_session() as cur:
                # SELECT ATUALIZADO
                cur.execute(
                    "SELECT id, nome_banco, saldo_inicial, COALESCE(data_criacao, '') as data_criacao, agencia, numero_conta FROM bancos WHERE usuario_id=%s ORDER BY nome_banco",
                    (uid,))
                bancos = cur.fetchall()
                cur.execute(
                    "SELECT id, nome_cartao, tipo, limite, banco_id FROM cartoes WHERE usuario_id=%s ORDER BY nome_cartao",
                    (uid,))
                cartoes = cur.fetchall()

            banco_map = {int(b['id']): b['nome_banco'] for b in bancos}
            lista_bancos_col.controls.clear()
            lista_bancos_col.controls.append(ft.Row(
                [card_banco(b, CORES_BANCO[i % len(CORES_BANCO)]) for i, b in enumerate(bancos)] if bancos else [
                    ft.Text("Nenhum banco cadastrado.")], wrap=True, spacing=16))

            # (Lógica de cartões mantida igual ao seu original)
            lista_cartoes_col.controls.clear()
            lista_cartoes_col.controls.append(ft.Row(
                [card_cartao(c, banco_map) for c in cartoes] if cartoes else [ft.Text("Nenhum cartão cadastrado.")],
                wrap=True, spacing=16))
            carregar_banco_dd();
            page.update()
        except:
            pass

    def salvar_banco(e):
        nome = nome_banco_f.value.strip()
        ag = agencia_f.value.strip()
        cta = conta_f.value.strip()
        saldo = limpar_valor(saldo_inicial_f.value.strip() or "0")
        data_str = data_inicial_f.value.strip()

        if not nome:
            msg_banco.value = "⚠️ Informe o nome do banco.";
            page.update();
            return

        try:
            with db_session() as cur:
                if state["editing_banco_id"]:
                    cur.execute(
                        "UPDATE bancos SET nome_banco=%s, saldo_inicial=%s, data_criacao=%s, agencia=%s, numero_conta=%s WHERE id=%s AND usuario_id=%s",
                        (nome, saldo, data_str, ag, cta, state["editing_banco_id"], uid))
                    state["editing_banco_id"] = None
                else:
                    cur.execute(
                        "INSERT INTO bancos (nome_banco, saldo_inicial, data_criacao, agencia, numero_conta, usuario_id) VALUES (%s, %s, %s, %s, %s, %s)",
                        (nome, saldo, data_str, ag, cta, uid))

            nome_banco_f.value = agencia_f.value = conta_f.value = saldo_inicial_f.value = ""
            btn_salvar_banco.text = "SALVAR BANCO"
            carregar_listas()
        except Exception as ex:
            msg_banco.value = f"❌ Erro: {ex}";
            page.update()

    def preparar_edicao_banco(b):
        state["editing_banco_id"] = b['id']
        nome_banco_f.value = b['nome_banco']
        agencia_f.value = b['agencia'] or ""
        conta_f.value = b['numero_conta'] or ""
        saldo_inicial_f.value = f"{b['saldo_inicial'] or 0:_.2f}".replace(".", ",").replace("_", ".")
        data_inicial_f.value = b['data_criacao'] if b['data_criacao'] else datetime.now().strftime("%d/%m/%Y")
        btn_salvar_banco.text = "ATUALIZAR BANCO"
        page.update()

    # --- REPETIR AS FUNÇÕES DE CARTÃO QUE VOCÊ JÁ TINHA ---
    def card_cartao(c, banco_map):
        tipo_cor = {"Crédito": "#E65100", "Débito": "#2E7D32", "Ambos": "#6A1B9A"}.get(c['tipo'], "#37474F")
        banco_nome = banco_map.get(int(c['banco_id']) if c['banco_id'] else 0, "—")
        return ft.Container(
            width=280, border_radius=14, bgcolor=tipo_cor, padding=ft.padding.all(18),
            content=ft.Column([
                ft.Row([ft.Icon(ft.icons.CREDIT_CARD, color="white", size=28),
                        ft.Text(c['nome_cartao'], color="white", weight="bold", size=16, expand=True)]),
                ft.Text(c['tipo'], color="white", size=11),
                ft.Divider(color=ft.colors.with_opacity(0.3, "white"), height=18),
                ft.Row([ft.Column([ft.Text("Limite", color="white70", size=11),
                                   ft.Text(fmt(c['limite'] or 0), color="white", size=16, weight="bold")]),
                        ft.Column(
                            [ft.Text("Banco", color="white70", size=11), ft.Text(banco_nome, color="white", size=13)])],
                       spacing=30),
                ft.Row([ft.TextButton("✏️", on_click=lambda _, c=c: preparar_edicao_cartao(c)),
                        ft.TextButton("🗑️", on_click=lambda _, cid=c['id']: excluir_cartao(cid))],
                       alignment=ft.MainAxisAlignment.END)
            ], spacing=4)
        )

    def excluir_banco(bid):
        with db_session() as cur: cur.execute("DELETE FROM bancos WHERE id=%s AND usuario_id=%s", (bid, uid))
        carregar_listas()

    def salvar_cartao(e):
        nome, tipo, lim, bid = nome_cartao_f.value.strip(), tipo_cartao_f.value, limpar_valor(
            limite_f.value.strip() or "0"), banco_dd.value
        if not nome or not tipo or not bid: return
        with db_session() as cur:
            if state["editing_cartao_id"]:
                cur.execute(
                    "UPDATE cartoes SET nome_cartao=%s, tipo=%s, limite=%s, banco_id=%s WHERE id=%s AND usuario_id=%s",
                    (nome, tipo, lim, int(bid), state["editing_cartao_id"], uid))
            else:
                cur.execute(
                    "INSERT INTO cartoes (nome_cartao, tipo, limite, banco_id, usuario_id) VALUES (%s, %s, %s, %s, %s)",
                    (nome, tipo, lim, int(bid), uid))
        nome_cartao_f.value = limite_f.value = "";
        carregar_listas()

    def preparar_edicao_cartao(c):
        state["editing_cartao_id"] = c['id'];
        nome_cartao_f.value = c['nome_cartao'];
        tipo_cartao_f.value = c['tipo'];
        limite_f.value = f"{c['limite'] or 0:_.2f}".replace(".", ",").replace("_", ".");
        banco_dd.value = str(c['banco_id']);
        page.update()

    def excluir_cartao(cid):
        with db_session() as cur: cur.execute("DELETE FROM cartoes WHERE id=%s AND usuario_id=%s", (cid, uid))
        carregar_listas()

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
                ft.Row([nome_banco_f, agencia_f, conta_f, saldo_inicial_f, data_inicial_f, btn_salvar_banco], wrap=True,
                       spacing=10),
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
        lista_cartoes_col,
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.View(route="/bancos", controls=[get_menu(page), ft.Divider(),
                                              ft.Container(padding=ft.padding.symmetric(horizontal=24, vertical=16),
                                                           expand=True, content=conteudo)])