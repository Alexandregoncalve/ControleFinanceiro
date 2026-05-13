import flet as ft
from menu import get_menu
from database import db_session
from utils import limpar_valor, formatar_moeda_input
from datetime import datetime

# Cores sugeridas para os cartões
OPCOES_CORES = [
    ft.dropdown.Option("#37474F", "Cinza Escuro (Sicredi)"),
    ft.dropdown.Option("#004a44", "Verde Sicredi"),
    ft.dropdown.Option("#1565C0", "Azul (Itaú/Caixa)"),
    ft.dropdown.Option("#B71C1C", "Vermelho (Santander/Bradesco)"),
    ft.dropdown.Option("#6A1B9A", "Roxo (Nubank)"),
    ft.dropdown.Option("#E65100", "Laranja (Inter)"),
    ft.dropdown.Option("#000000", "Preto (Black)"),
]

def bancos_view(page: ft.Page):
    uid = page.session.get("user_id")
    state = {"editing_banco_id": None, "editing_cartao_id": None}

    # --- CAMPOS DE ENTRADA BANCO ---
    nome_banco_f = ft.TextField(label="Nome do Banco", width=200)
    agencia_f = ft.TextField(label="Agência", width=100)
    conta_f = ft.TextField(label="Nº Conta", width=140)
    logo_url_f = ft.TextField(label="URL do Logo", width=200, hint_text="Link da imagem .png")
    cor_banco_f = ft.Dropdown(label="Cor do Card", width=180, options=OPCOES_CORES, value="#37474F")
    saldo_inicial_f = ft.TextField(label="Saldo Inicial", width=150, on_blur=formatar_moeda_input)
    data_inicial_f = ft.TextField(label="Data Inicial", width=150, value=datetime.now().strftime("%d/%m/%Y"))
    msg_banco = ft.Text("", size=13)

    # --- CAMPOS DE ENTRADA CARTÃO ---
    nome_cartao_f = ft.TextField(label="Nome do Cartão", width=200)
    tipo_cartao_f = ft.Dropdown(label="Tipo", width=130, options=[ft.dropdown.Option("Crédito"), ft.dropdown.Option("Débito"), ft.dropdown.Option("Ambos")])
    limite_f = ft.TextField(label="Limite", width=150, on_blur=formatar_moeda_input)
    banco_dd = ft.Dropdown(label="Banco vinculado", width=200, options=[])
    msg_cartao = ft.Text("", size=13)

    lista_bancos_col = ft.Column([], spacing=12)
    lista_cartoes_col = ft.Column([], spacing=12)

    def fmt(v):
        try: return f"R$ {float(v):_.2f}".replace(".", ",").replace("_", ".")
        except: return "R$ 0,00"

    def carregar_banco_dd():
        try:
            with db_session() as cur:
                cur.execute("SELECT id, nome_banco FROM bancos WHERE usuario_id=%s ORDER BY nome_banco", (uid,))
                bancos = cur.fetchall()
            banco_dd.options = [ft.dropdown.Option(str(b['id']), b['nome_banco']) for b in bancos]
            page.update()
        except: pass

    def card_banco(b):
        cor_card = b['cor'] if b['cor'] else "#37474F"
        return ft.Container(
            width=320, border_radius=18, bgcolor=cor_card, padding=20,
            shadow=ft.BoxShadow(blur_radius=15, color=ft.colors.with_opacity(0.3, "black"), offset=ft.Offset(4, 6)),
            content=ft.Column([
                ft.Row([
                    ft.Image(src=b['logo_url'], width=35, height=35, fit="contain") if b['logo_url'] else ft.Icon(ft.icons.ACCOUNT_BALANCE, color="white", size=30),
                    ft.Column([
                        ft.Text(b['nome_banco'], color="white", weight="bold", size=16),
                        ft.Text(f"Ag: {b['agencia'] or '—'} | Cta: {b['numero_conta'] or '—'}", color="white70", size=11),
                    ], spacing=0, expand=True),
                ], alignment="spaceBetween"),
                ft.Divider(color="white24", height=15),
                ft.Text("Saldo Inicial", color="white70", size=10),
                ft.Text(fmt(b['saldo_inicial'] or 0), color="white", size=22, weight="bold"),
                ft.Row([
                    ft.Text(f"Início: {b['data_criacao']}", color="white54", size=10),
                    ft.Row([
                        ft.IconButton(ft.icons.EDIT_OUTLINED, icon_color="white", icon_size=18, on_click=lambda _, b=b: preparar_edicao_banco(b)),
                        ft.IconButton(ft.icons.DELETE_OUTLINE, icon_color="red_200", icon_size=18, on_click=lambda _, bid=b['id']: excluir_banco(bid)),
                    ], spacing=0)
                ], alignment="spaceBetween")
            ], spacing=5)
        )

    def card_cartao(c, banco_map):
        tipo_cor = {"Crédito": "#E65100", "Débito": "#2E7D32", "Ambos": "#6A1B9A"}.get(c['tipo'], "#37474F")
        return ft.Container(
            width=280, border_radius=14, bgcolor=tipo_cor, padding=18,
            content=ft.Column([
                ft.Row([ft.Icon(ft.icons.CREDIT_CARD, color="white", size=26), ft.Text(c['nome_cartao'], color="white", weight="bold", size=16, expand=True)]),
                ft.Text(c['tipo'], color="white", size=11),
                ft.Divider(color="white24"),
                ft.Row([ft.Column([ft.Text("Limite", color="white70", size=10), ft.Text(fmt(c['limite'] or 0), color="white", size=15, weight="bold")]),
                        ft.Column([ft.Text("Banco", color="white70", size=10), ft.Text(banco_map.get(int(c['banco_id']), "—"), color="white", size=12)])], spacing=20),
                ft.Row([ft.IconButton(ft.icons.EDIT, icon_color="white", on_click=lambda _, c=c: preparar_edicao_cartao(c)),
                        ft.IconButton(ft.icons.DELETE, icon_color="red_200", on_click=lambda _, cid=c['id']: excluir_cartao(cid))], alignment="end")
            ])
        )

    def carregar_listas():
        try:
            with db_session() as cur:
                cur.execute("SELECT id, nome_banco, saldo_inicial, COALESCE(data_criacao, '') as data_criacao, agencia, numero_conta, cor, logo_url FROM bancos WHERE usuario_id=%s ORDER BY nome_banco", (uid,))
                bancos = cur.fetchall()
                cur.execute("SELECT id, nome_cartao, tipo, limite, banco_id FROM cartoes WHERE usuario_id=%s ORDER BY nome_cartao", (uid,))
                cartoes = cur.fetchall()
            banco_map = {int(b['id']): b['nome_banco'] for b in bancos}
            lista_bancos_col.controls.clear()
            lista_bancos_col.controls.append(ft.Row([card_banco(b) for b in bancos], wrap=True, spacing=16))
            lista_cartoes_col.controls.clear()
            lista_cartoes_col.controls.append(ft.Row([card_cartao(c, banco_map) for c in cartoes], wrap=True, spacing=16))
            carregar_banco_dd(); page.update()
        except: pass

    def salvar_banco(e):
        nome, ag, cta, logo, cor = nome_banco_f.value.strip(), agencia_f.value.strip(), conta_f.value.strip(), logo_url_f.value.strip(), cor_banco_f.value
        saldo = limpar_valor(saldo_inicial_f.value.strip() or "0")
        data = data_inicial_f.value.strip() or datetime.now().strftime("%d/%m/%Y")
        if not nome: return
        with db_session() as cur:
            if state["editing_banco_id"]:
                cur.execute("UPDATE bancos SET nome_banco=%s, saldo_inicial=%s, data_criacao=%s, agencia=%s, numero_conta=%s, cor=%s, logo_url=%s WHERE id=%s AND usuario_id=%s", (nome, saldo, data, ag, cta, cor, logo, state["editing_banco_id"], uid))
            else:
                cur.execute("INSERT INTO bancos (nome_banco, saldo_inicial, data_criacao, agencia, numero_conta, cor, logo_url, usuario_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (nome, saldo, data, ag, cta, cor, logo, uid))
        nome_banco_f.value = agencia_f.value = conta_f.value = logo_url_f.value = saldo_inicial_f.value = ""; state["editing_banco_id"] = None
        btn_salvar_banco.text = "SALVAR BANCO"; carregar_listas()

    def preparar_edicao_banco(b):
        state["editing_banco_id"] = b['id']; nome_banco_f.value = b['nome_banco']; agencia_f.value = b['agencia'] or ""; conta_f.value = b['numero_conta'] or ""; logo_url_f.value = b['logo_url'] or ""; cor_banco_f.value = b['cor'] or "#37474F"
        saldo_inicial_f.value = f"{b['saldo_inicial'] or 0:_.2f}".replace(".", ",").replace("_", "."); data_inicial_f.value = b['data_criacao']; btn_salvar_banco.text = "ATUALIZAR BANCO"; page.update()

    def excluir_banco(bid):
        with db_session() as cur: cur.execute("DELETE FROM bancos WHERE id=%s AND usuario_id=%s", (bid, uid))
        carregar_listas()

    def salvar_cartao(e):
        nome, tipo, lim, bid = nome_cartao_f.value.strip(), tipo_cartao_f.value, limpar_valor(limite_f.value.strip() or "0"), banco_dd.value
        if not (nome and tipo and bid): return
        with db_session() as cur:
            if state["editing_cartao_id"]: cur.execute("UPDATE cartoes SET nome_cartao=%s, tipo=%s, limite=%s, banco_id=%s WHERE id=%s AND usuario_id=%s", (nome, tipo, lim, int(bid), state["editing_cartao_id"], uid))
            else: cur.execute("INSERT INTO cartoes (nome_cartao, tipo, limite, banco_id, usuario_id) VALUES (%s, %s, %s, %s, %s)", (nome, tipo, lim, int(bid), uid))
        nome_cartao_f.value = limite_f.value = ""; state["editing_cartao_id"] = None; carregar_listas()

    def preparar_edicao_cartao(c):
        state["editing_cartao_id"] = c['id']; nome_cartao_f.value = c['nome_cartao']; tipo_cartao_f.value = c['tipo']; limite_f.value = f"{c['limite'] or 0:_.2f}".replace(".", ",").replace("_", "."); banco_dd.value = str(c['banco_id']); btn_salvar_cartao.text = "ATUALIZAR"; page.update()

    def excluir_cartao(cid):
        with db_session() as cur: cur.execute("DELETE FROM cartoes WHERE id=%s AND usuario_id=%s", (cid, uid))
        carregar_listas()

    btn_salvar_banco = ft.ElevatedButton("SALVAR BANCO", bgcolor="#1565C0", color="white", on_click=salvar_banco)
    btn_salvar_cartao = ft.ElevatedButton("SALVAR CARTÃO", bgcolor="#E65100", color="white", on_click=salvar_cartao)

    carregar_listas()
    conteudo = ft.Column([
        ft.Row([ft.Icon(ft.icons.ACCOUNT_BALANCE, color="#1565C0", size=30), ft.Text("BANCOS E CARTÕES", size=22, weight="bold", color="#1565C0")]),
        ft.Divider(),
        ft.Container(bgcolor="#E3F2FD", border_radius=10, padding=16, content=ft.Column([
            ft.Text("🏦 Cadastrar / Editar Banco", size=15, weight="bold", color="#1565C0"),
            ft.Row([nome_banco_f, agencia_f, conta_f, logo_url_f, cor_banco_f, saldo_inicial_f, data_inicial_f, btn_salvar_banco], wrap=True, spacing=10),
            msg_banco
        ])),
        ft.Text("Bancos Cadastrados", size=15, weight="bold", color="#1565C0"),
        lista_bancos_col,
        ft.Divider(),
        ft.Container(bgcolor="#FFF3E0", border_radius=10, padding=16, content=ft.Column([
            ft.Text("💳 Cadastrar / Editar Cartão", size=15, weight="bold", color="#E65100"),
            ft.Row([nome_cartao_f, tipo_cartao_f, limite_f, banco_dd, btn_salvar_cartao], wrap=True, spacing=10),
            msg_cartao
        ])),
        lista_cartoes_col
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.View(route="/bancos", controls=[get_menu(page), ft.Divider(), ft.Container(padding=24, expand=True, content=conteudo)])