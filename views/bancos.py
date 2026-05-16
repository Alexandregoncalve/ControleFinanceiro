import flet as ft
from menu import get_menu
from database import db_session
from utils import limpar_valor, formatar_moeda_input
from datetime import datetime

CORES_BANCO = ["#1565C0", "#2E7D32", "#6A1B9A", "#00838F", "#E65100", "#AD1457", "#4527A0", "#37474F"]


def bancos_view(page: ft.Page):
    uid = page.session.get("user_id")
    state = {"editing_banco_id": None, "editing_cartao_id": None}

    # ── CAMPOS BANCO ───────────────────────────────────────────────────────
    nome_banco_f = ft.TextField(label="Nome do Banco", width=220)
    codigo_banco_f = ft.TextField(label="Cód. Banco", width=100, hint_text="Ex: 237")
    agencia_f = ft.TextField(label="Agência", width=110)
    conta_f = ft.TextField(label="Nº Conta", width=140)
    saldo_inicial_f = ft.TextField(label="Saldo Inicial", width=160, on_blur=formatar_moeda_input)
    data_inicial_f = ft.TextField(
        label="Data Inicial", width=160,
        value=datetime.now().strftime("%d/%m/%Y")
    )
    msg_banco = ft.Text("", size=13)

    # ── CAMPOS CARTÃO ──────────────────────────────────────────────────────
    nome_cartao_f = ft.TextField(label="Nome do Cartão", width=200)
    tipo_cartao_f = ft.Dropdown(
        label="Tipo", width=150,
        options=[ft.dropdown.Option("Crédito"), ft.dropdown.Option("Débito"), ft.dropdown.Option("Ambos")]
    )
    limite_f = ft.TextField(label="Limite", width=180, on_blur=formatar_moeda_input)
    banco_dd = ft.Dropdown(label="Banco vinculado", width=220, options=[])
    msg_cartao = ft.Text("", size=13)

    lista_bancos_col = ft.Column([], spacing=12)
    lista_cartoes_col = ft.Column([], spacing=12)

    # ── CAMPOS TRANSFERÊNCIA ───────────────────────────────────────────────
    transf_orig_dd = ft.Dropdown(label="Origem", width=200)
    transf_dest_dd = ft.Dropdown(label="Destino", width=200)
    transf_valor_f = ft.TextField(label="Valor", width=140, on_blur=formatar_moeda_input)
    transf_desc_f = ft.TextField(label="Descrição", width=250, value="Transferência entre bancos")
    transf_data_f = ft.TextField(label="Data", width=120, value=datetime.now().strftime("%d/%m/%Y"), read_only=True)
    msg_transf = ft.Text("", size=13)
    lista_transf = ft.Column([], spacing=6, scroll=ft.ScrollMode.AUTO, height=180)

    # ── FUNÇÕES (PRESERVADAS) ──────────────────────────────────────────────
    def fmt(v):
        try:
            return f"R$ {float(v):_.2f}".replace(".", ",").replace("_", ".")
        except:
            return "R$ 0,00"

    def carregar_banco_dds():
        try:
            with db_session() as cur:
                cur.execute("SELECT id, nome_banco FROM bancos WHERE usuario_id=%s ORDER BY nome_banco", (uid,))
                bancos = cur.fetchall()
            opcoes = [ft.dropdown.Option(str(b['id']), b['nome_banco']) for b in bancos]
            banco_dd.options = opcoes
            transf_orig_dd.options = [ft.dropdown.Option("", "— Selecione —")] + opcoes
            transf_dest_dd.options = [ft.dropdown.Option("", "— Selecione —")] + opcoes
            page.update()
        except:
            pass

    def card_banco(b, cor):
        codigo = f" ({b['codigo_banco']})" if b['codigo_banco'] else ""
        return ft.Container(
            width=280, border_radius=14, bgcolor=cor, padding=ft.padding.all(15),
            shadow=ft.BoxShadow(blur_radius=10, color=ft.colors.with_opacity(0.2, "black"), offset=ft.Offset(2, 4)),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.ACCOUNT_BALANCE, color="white", size=24),
                    ft.Column([
                        ft.Text(b['nome_banco'], color="white", weight="bold", size=14, expand=True, no_wrap=True),
                        ft.Text(f"Banco{codigo}", color="white70", size=10),
                    ], expand=True, spacing=1),
                ], spacing=10),
                ft.Text(f"Ag: {b['agencia'] or '—'} | Cta: {b['numero_conta'] or '—'}", color="white", size=11),
                ft.Divider(color=ft.colors.with_opacity(0.3, "white"), height=10),
                ft.Row([
                    ft.Column([
                        ft.Text("Saldo Inicial", color=ft.colors.with_opacity(0.7, "white"), size=10),
                        ft.Text(fmt(b['saldo_inicial'] or 0), color="white", size=16, weight="bold"),
                    ]),
                ], alignment="spaceBetween"),
                ft.Row([
                    ft.TextButton("✏️", style=ft.ButtonStyle(color="white"),
                                  on_click=lambda _, b=b: preparar_edicao_banco(b)),
                    ft.TextButton("🗑️", style=ft.ButtonStyle(color=ft.colors.RED_200),
                                  on_click=lambda _, bid=b['id']: excluir_banco(bid)),
                ], alignment=ft.MainAxisAlignment.END, spacing=0),
            ], spacing=4),
        )

    def carregar_listas():
        try:
            with db_session() as cur:
                cur.execute(
                    "SELECT id, nome_banco, saldo_inicial, COALESCE(data_criacao, '') as data_criacao, agencia, numero_conta, codigo_banco FROM bancos WHERE usuario_id=%s ORDER BY nome_banco",
                    (uid,))
                bancos = cur.fetchall()
                cur.execute(
                    "SELECT id, nome_cartao, tipo, limite, banco_id FROM cartoes WHERE usuario_id=%s ORDER BY nome_cartao",
                    (uid,))
                cartoes = cur.fetchall()
            banco_map = {int(b['id']): b['nome_banco'] for b in bancos}
            lista_bancos_col.controls.clear()
            lista_bancos_col.controls.append(
                ft.Row([card_banco(b, CORES_BANCO[i % len(CORES_BANCO)]) for i, b in enumerate(bancos)], wrap=True,
                       spacing=10))
            lista_cartoes_col.controls.clear()
            lista_cartoes_col.controls.append(
                ft.Row([card_cartao(c, banco_map) for c in cartoes], wrap=True, spacing=10))
            carregar_banco_dds()
            page.update()
        except:
            pass

    # --- FUNÇÕES DE SALVAMENTO (REDUZIDAS PARA ESPAÇO) ---
    def salvar_banco(e):
        nome, codigo, ag, cta = nome_banco_f.value.strip(), codigo_banco_f.value.strip(), agencia_f.value.strip(), conta_f.value.strip()
        saldo, data = limpar_valor(saldo_inicial_f.value.strip() or "0"), data_inicial_f.value.strip()
        if not nome: return
        with db_session() as cur:
            if state["editing_banco_id"]:
                cur.execute(
                    "UPDATE bancos SET nome_banco=%s, saldo_inicial=%s, data_criacao=%s, agencia=%s, numero_conta=%s, codigo_banco=%s WHERE id=%s AND usuario_id=%s",
                    (nome, saldo, data, ag, cta, codigo or None, state["editing_banco_id"], uid))
            else:
                cur.execute(
                    "INSERT INTO bancos (nome_banco, saldo_inicial, data_criacao, agencia, numero_conta, codigo_banco, usuario_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (nome, saldo, data, ag, cta, codigo or None, uid))
        nome_banco_f.value = agencia_f.value = conta_f.value = saldo_inicial_f.value = codigo_banco_f.value = ""
        state["editing_banco_id"] = None;
        btn_salvar_banco.text = "SALVAR BANCO";
        carregar_listas()

    def preparar_edicao_banco(b):
        state["editing_banco_id"] = b['id']
        nome_banco_f.value, codigo_banco_f.value = b['nome_banco'], b['codigo_banco'] or ""
        agencia_f.value, conta_f.value = b['agencia'] or "", b['numero_conta'] or ""
        saldo_inicial_f.value = f"{b['saldo_inicial'] or 0:_.2f}".replace(".", ",").replace("_", ".")
        btn_salvar_banco.text = "ATUALIZAR BANCO";
        page.update()

    # (Mantenha aqui as funções excluir_banco, salvar_cartao, preparar_edicao_cartao, excluir_cartao e realizar_transferencia do seu código original)

    # ── DEFINIÇÃO DOS BOTÕES ──────────────────────────────────────────────
    btn_salvar_banco = ft.ElevatedButton("SALVAR BANCO", bgcolor="#1565C0", color="white", on_click=salvar_banco)
    btn_salvar_cartao = ft.ElevatedButton("SALVAR CARTÃO", bgcolor="#E65100", color="white")
    btn_transferir = ft.ElevatedButton("💸 TRANSFERIR", bgcolor="#2E7D32", color="white", height=45)

    carregar_listas()

    # ── LAYOUT PRINCIPAL ──────────────────────────────────────────────────

    # Bloco Superior: Cadastro + Listagem Lado a Lado
    secao_bancos = ft.ResponsiveRow([
        # Formulário (Esquerda)
        ft.Column([
            ft.Container(
                bgcolor="#E3F2FD", border_radius=10, padding=20,
                content=ft.Column([
                    ft.Text("🏦 Cadastrar / Editar Banco", size=16, weight="bold", color="#1565C0"),
                    ft.Row([nome_banco_f, codigo_banco_f, agencia_f], spacing=10, wrap=True),
                    ft.Row([conta_f, saldo_inicial_f, data_inicial_f], spacing=10, wrap=True),
                    btn_salvar_banco,
                    msg_banco,
                ], spacing=15)
            )
        ], col={"md": 4}),

        # Lista (Direita)
        ft.Column([
            ft.Text("Bancos Cadastrados", size=16, weight="bold", color="#1565C0"),
            lista_bancos_col
        ], col={"md": 8}),
    ], spacing=20)

    conteudo = ft.Column([
        ft.Row([ft.Icon(ft.icons.ACCOUNT_BALANCE, color="#1565C0", size=30),
                ft.Text("BANCOS E CARTÕES", size=22, weight="bold", color="#1565C0")], spacing=10),
        ft.Divider(),

        secao_bancos,

        ft.Divider(height=30),

        # ── TRANSFERÊNCIA ─────────────────────────────────────
        ft.Container(
            bgcolor="#E8F5E9", border_radius=10, padding=16,
            content=ft.Column([
                ft.Row([ft.Icon(ft.icons.SWAP_HORIZ, color="#2E7D32", size=24),
                        ft.Text("💸 Transferência entre Bancos", size=15, weight="bold", color="#2E7D32")]),
                ft.Row([transf_orig_dd, ft.Icon(ft.icons.ARROW_FORWARD, color="#2E7D32"), transf_dest_dd], spacing=12),
                ft.Row([transf_valor_f, transf_data_f, transf_desc_f, btn_transferir], wrap=True, spacing=10),
                lista_transf,
            ], spacing=10)
        ),

        ft.Divider(height=30),

        # ── CARTÕES ────────────────────────────────────────────────
        ft.Container(
            bgcolor="#FFF3E0", border_radius=10, padding=16,
            content=ft.Column([
                ft.Text("💳 Cadastrar / Editar Cartão", size=15, weight="bold", color="#E65100"),
                ft.Row([nome_cartao_f, tipo_cartao_f, limite_f, banco_dd, btn_salvar_cartao], wrap=True, spacing=10),
            ], spacing=10)
        ),
        lista_cartoes_col,
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.View(
        route="/bancos",
        controls=[
            get_menu(page), ft.Divider(),
            ft.Container(padding=ft.padding.symmetric(horizontal=24, vertical=16), expand=True, content=conteudo)
        ]
    )