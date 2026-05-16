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
    nome_banco_f   = ft.TextField(label="Nome do Banco", width=200)
    codigo_banco_f = ft.TextField(label="Código Banco", width=100, hint_text="Ex: 237")
    agencia_f      = ft.TextField(label="Agência", width=110)
    conta_f        = ft.TextField(label="Nº Conta", width=140)
    saldo_inicial_f = ft.TextField(label="Saldo Inicial", width=160, on_blur=formatar_moeda_input)
    data_inicial_f  = ft.TextField(
        label="Data Inicial (DD/MM/AAAA)", width=170,
        value=datetime.now().strftime("%d/%m/%Y")
    )
    msg_banco = ft.Text("", size=13)

    # ── CAMPOS CARTÃO ──────────────────────────────────────────────────────
    nome_cartao_f = ft.TextField(label="Nome do Cartão", width=200)
    tipo_cartao_f = ft.Dropdown(
        label="Tipo", width=150,
        options=[ft.dropdown.Option("Crédito"), ft.dropdown.Option("Débito"), ft.dropdown.Option("Ambos")]
    )
    limite_f  = ft.TextField(label="Limite (ex: 5.000,00)", width=180, on_blur=formatar_moeda_input)
    banco_dd  = ft.Dropdown(label="Banco vinculado", width=220, options=[])
    msg_cartao = ft.Text("", size=13)

    lista_bancos_col  = ft.Column([], spacing=12)
    lista_cartoes_col = ft.Column([], spacing=12)

    # ── CAMPOS TRANSFERÊNCIA ───────────────────────────────────────────────
    transf_orig_dd  = ft.Dropdown(label="Banco Origem", width=220, options=[])
    transf_dest_dd  = ft.Dropdown(label="Banco Destino", width=220, options=[])
    transf_valor_f  = ft.TextField(label="Valor", width=160, on_blur=formatar_moeda_input)
    transf_desc_f   = ft.TextField(label="Descrição", width=280, value="Transferência entre bancos")
    transf_data_f   = ft.TextField(label="Data", width=140, value=datetime.now().strftime("%d/%m/%Y"), read_only=True)
    msg_transf      = ft.Text("", size=13)
    lista_transf    = ft.Column([], spacing=6, scroll=ft.ScrollMode.AUTO, height=200)

    date_picker_transf = ft.DatePicker(
        first_date=datetime(2020, 1, 1), last_date=datetime(2030, 12, 31),
        on_change=lambda e: (
            setattr(transf_data_f, "value", e.control.value.strftime("%d/%m/%Y")),
            page.update()
        ) if e.control.value else None
    )
    page.overlay.append(date_picker_transf)
    btn_data_transf = ft.ElevatedButton(
        "📅 Data", bgcolor=ft.colors.BLUE_100, color=ft.colors.BLUE_900,
        on_click=lambda e: (setattr(date_picker_transf, "open", True), page.update())
    )

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
            banco_dd.options      = opcoes
            transf_orig_dd.options = [ft.dropdown.Option("", "— Selecione —")] + opcoes
            transf_dest_dd.options = [ft.dropdown.Option("", "— Selecione —")] + opcoes
            page.update()
        except:
            pass

    def card_banco(b, cor):
        codigo = f" ({b['codigo_banco']})" if b['codigo_banco'] else ""
        return ft.Container(
            width=300, border_radius=14, bgcolor=cor, padding=ft.padding.all(18),
            shadow=ft.BoxShadow(blur_radius=10, color=ft.colors.with_opacity(0.22, "black"), offset=ft.Offset(2, 4)),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.ACCOUNT_BALANCE, color="white", size=28),
                    ft.Column([
                        ft.Text(b['nome_banco'], color="white", weight="bold", size=15, expand=True),
                        ft.Text(f"Banco{codigo}", color="white70", size=15), ## alterei de 11 para 15
                    ], expand=True, spacing=2),
                ], spacing=10),
                ft.Text(f"Ag: {b['agencia'] or '—'} | Cta: {b['numero_conta'] or '—'}", color="white", size=12),
                ft.Divider(color=ft.colors.with_opacity(0.3, "white"), height=14),
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

    def card_cartao(c, banco_map):
        tipo_cor   = {"Crédito": "#E65100", "Débito": "#2E7D32", "Ambos": "#6A1B9A"}.get(c['tipo'], "#37474F")
        banco_nome = banco_map.get(int(c['banco_id']) if c['banco_id'] else 0, "—")
        return ft.Container(
            width=280, border_radius=14, bgcolor=tipo_cor, padding=ft.padding.all(18),
            content=ft.Column([
                ft.Row([ft.Icon(ft.icons.CREDIT_CARD, color="white", size=28),
                        ft.Text(c['nome_cartao'], color="white", weight="bold", size=16, expand=True)]),
                ft.Text(c['tipo'], color="white", size=11),
                ft.Divider(color=ft.colors.with_opacity(0.3, "white"), height=14),
                ft.Row([
                    ft.Column([ft.Text("Limite", color="white70", size=11),
                               ft.Text(fmt(c['limite'] or 0), color="white", size=16, weight="bold")]),
                    ft.Column([ft.Text("Banco", color="white70", size=11),
                               ft.Text(banco_nome, color="white", size=13)])
                ], spacing=30),
                ft.Row([
                    ft.TextButton("✏️", on_click=lambda _, c=c: preparar_edicao_cartao(c)),
                    ft.TextButton("🗑️", on_click=lambda _, cid=c['id']: excluir_cartao(cid))
                ], alignment=ft.MainAxisAlignment.END)
            ], spacing=4)
        )

    def carregar_transferencias():
        try:
            with db_session() as cur:
                cur.execute("""
                    SELECT t.data, t.valor, t.descricao,
                           bo.nome_banco as origem, bd.nome_banco as destino
                    FROM transferencias t
                    JOIN bancos bo ON t.banco_orig = bo.id
                    JOIN bancos bd ON t.banco_dest = bd.id
                    WHERE t.usuario_id=%s
                    ORDER BY t.data DESC, t.id DESC
                    LIMIT 20
                """, (uid,))
                rows = cur.fetchall()

            lista_transf.controls.clear()
            if not rows:
                lista_transf.controls.append(
                    ft.Text("Nenhuma transferência realizada.", color="grey", italic=True, size=12))
            else:
                for r in rows:
                    lista_transf.controls.append(
                        ft.Container(
                            border=ft.border.all(1, "#E0E0E0"), border_radius=8, padding=10,
                            content=ft.Row([
                                ft.Column([
                                    ft.Text(r['data'], size=11, color="grey"),
                                    ft.Text(r['descricao'] or "Transferência", size=12),
                                ], expand=True),
                                ft.Row([
                                    ft.Text(r['origem'], size=12, color="#C62828"),
                                    ft.Icon(ft.icons.ARROW_FORWARD, size=14, color="grey"),
                                    ft.Text(r['destino'], size=12, color="#2E7D32"),
                                ], spacing=6),
                                ft.Text(fmt(r['valor']), size=13, weight="bold", color="#1565C0"),
                            ], alignment="spaceBetween")
                        )
                    )
            page.update()
        except Exception as ex:
            print(f"[bancos] carregar_transferencias erro: {ex}")

    def carregar_listas():
        try:
            with db_session() as cur:
                cur.execute("""
                    SELECT id, nome_banco, saldo_inicial, COALESCE(data_criacao, '') as data_criacao,
                           agencia, numero_conta, codigo_banco
                    FROM bancos WHERE usuario_id=%s ORDER BY nome_banco
                """, (uid,))
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

            lista_cartoes_col.controls.clear()
            lista_cartoes_col.controls.append(ft.Row(
                [card_cartao(c, banco_map) for c in cartoes] if cartoes else [ft.Text("Nenhum cartão cadastrado.")],
                wrap=True, spacing=16))

            carregar_banco_dds()
            carregar_transferencias()
            page.update()
        except Exception as ex:
            print(f"[bancos] carregar_listas erro: {ex}")

    def salvar_banco(e):
        nome   = nome_banco_f.value.strip()
        codigo = codigo_banco_f.value.strip()
        ag     = agencia_f.value.strip()
        cta    = conta_f.value.strip()
        saldo  = limpar_valor(saldo_inicial_f.value.strip() or "0")
        data_str = data_inicial_f.value.strip()

        if not nome:
            msg_banco.value = "⚠️ Informe o nome do banco."
            msg_banco.color = ft.colors.ORANGE_700
            page.update()
            return
        try:
            with db_session() as cur:
                if state["editing_banco_id"]:
                    cur.execute(
                        "UPDATE bancos SET nome_banco=%s, saldo_inicial=%s, data_criacao=%s, agencia=%s, numero_conta=%s, codigo_banco=%s WHERE id=%s AND usuario_id=%s",
                        (nome, saldo, data_str, ag, cta, codigo or None, state["editing_banco_id"], uid))
                    state["editing_banco_id"] = None
                else:
                    cur.execute(
                        "INSERT INTO bancos (nome_banco, saldo_inicial, data_criacao, agencia, numero_conta, codigo_banco, usuario_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        (nome, saldo, data_str, ag, cta, codigo or None, uid))

            msg_banco.value = "✅ Banco salvo!"
            msg_banco.color = ft.colors.GREEN_700
            nome_banco_f.value = agencia_f.value = conta_f.value = saldo_inicial_f.value = codigo_banco_f.value = ""
            data_inicial_f.value = datetime.now().strftime("%d/%m/%Y")
            btn_salvar_banco.text = "SALVAR BANCO"
            carregar_listas()
        except Exception as ex:
            msg_banco.value = f"❌ Erro: {ex}"
            msg_banco.color = ft.colors.RED_700
            page.update()

    def preparar_edicao_banco(b):
        state["editing_banco_id"] = b['id']
        nome_banco_f.value    = b['nome_banco']
        codigo_banco_f.value  = b['codigo_banco'] or ""
        agencia_f.value       = b['agencia'] or ""
        conta_f.value         = b['numero_conta'] or ""
        saldo_inicial_f.value = f"{b['saldo_inicial'] or 0:_.2f}".replace(".", ",").replace("_", ".")
        data_inicial_f.value  = b['data_criacao'] if b['data_criacao'] else datetime.now().strftime("%d/%m/%Y")
        btn_salvar_banco.text = "ATUALIZAR BANCO"
        page.update()

    def excluir_banco(bid):
        try:
            with db_session() as cur:
                cur.execute("DELETE FROM bancos WHERE id=%s AND usuario_id=%s", (bid, uid))
            carregar_listas()
        except Exception as ex:
            print(f"[bancos] excluir_banco erro: {ex}")

    def salvar_cartao(e):
        nome, tipo, lim, bid = nome_cartao_f.value.strip(), tipo_cartao_f.value, limpar_valor(
            limite_f.value.strip() or "0"), banco_dd.value
        if not nome or not tipo or not bid:
            msg_cartao.value = "⚠️ Preencha todos os campos."
            msg_cartao.color = ft.colors.ORANGE_700
            page.update()
            return
        try:
            with db_session() as cur:
                if state["editing_cartao_id"]:
                    cur.execute(
                        "UPDATE cartoes SET nome_cartao=%s, tipo=%s, limite=%s, banco_id=%s WHERE id=%s AND usuario_id=%s",
                        (nome, tipo, lim, int(bid), state["editing_cartao_id"], uid))
                    state["editing_cartao_id"] = None
                else:
                    cur.execute(
                        "INSERT INTO cartoes (nome_cartao, tipo, limite, banco_id, usuario_id) VALUES (%s,%s,%s,%s,%s)",
                        (nome, tipo, lim, int(bid), uid))
            msg_cartao.value = "✅ Cartão salvo!"
            msg_cartao.color = ft.colors.GREEN_700
            nome_cartao_f.value = limite_f.value = ""
            tipo_cartao_f.value = banco_dd.value = None
            btn_salvar_cartao.text = "SALVAR CARTÃO"
            carregar_listas()
        except Exception as ex:
            msg_cartao.value = f"❌ Erro: {ex}"
            msg_cartao.color = ft.colors.RED_700
            page.update()

    def preparar_edicao_cartao(c):
        state["editing_cartao_id"] = c['id']
        nome_cartao_f.value = c['nome_cartao']
        tipo_cartao_f.value = c['tipo']
        limite_f.value      = f"{c['limite'] or 0:_.2f}".replace(".", ",").replace("_", ".")
        banco_dd.value      = str(c['banco_id'])
        btn_salvar_cartao.text = "ATUALIZAR CARTÃO"
        page.update()

    def excluir_cartao(cid):
        try:
            with db_session() as cur:
                cur.execute("DELETE FROM cartoes WHERE id=%s AND usuario_id=%s", (cid, uid))
            carregar_listas()
        except Exception as ex:
            print(f"[bancos] excluir_cartao erro: {ex}")

    def realizar_transferencia(e):
        msg_transf.value = ""
        orig = transf_orig_dd.value
        dest = transf_dest_dd.value
        valor = limpar_valor(transf_valor_f.value or "0")
        data  = transf_data_f.value.strip()

        if not orig or orig == "":
            msg_transf.value = "⚠️ Selecione o banco de origem."
            msg_transf.color = ft.colors.ORANGE_700
            page.update()
            return
        if not dest or dest == "":
            msg_transf.value = "⚠️ Selecione o banco de destino."
            msg_transf.color = ft.colors.ORANGE_700
            page.update()
            return
        if orig == dest:
            msg_transf.value = "⚠️ Origem e destino não podem ser iguais."
            msg_transf.color = ft.colors.ORANGE_700
            page.update()
            return
        if valor <= 0:
            msg_transf.value = "⚠️ Informe um valor válido."
            msg_transf.color = ft.colors.ORANGE_700
            page.update()
            return

        try:
            with db_session() as cur:
                # Busca nomes dos bancos
                cur.execute("SELECT nome_banco FROM bancos WHERE id=%s", (int(orig),))
                nome_orig = cur.fetchone()['nome_banco']
                cur.execute("SELECT nome_banco FROM bancos WHERE id=%s", (int(dest),))
                nome_dest = cur.fetchone()['nome_banco']

                desc = transf_desc_f.value.strip() or "Transferência entre bancos"

                # ✅ Registra na tabela transferencias
                cur.execute("""
                    INSERT INTO transferencias (usuario_id, data, valor, banco_orig, banco_dest, descricao)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, (uid, data, valor, int(orig), int(dest), desc))

                # ✅ Lança despesa no banco de origem
                cur.execute("""
                    SELECT s.id FROM subcontas s
                    JOIN categorias c ON s.categoria_id = c.id
                    WHERE s.usuario_id=%s AND UPPER(s.nome) LIKE '%%TRANSFER%%'
                    LIMIT 1
                """, (uid,))
                sub_transf = cur.fetchone()

                if sub_transf:
                    sub_id = sub_transf['id']
                    # Despesa na origem
                    cur.execute("""
                        INSERT INTO transacoes (usuario_id, data, valor, subconta_id, tipo, descricao, banco_id)
                        VALUES (%s,%s,%s,%s,'Despesa',%s,%s)
                    """, (uid, data, valor, sub_id, f"Transf. → {nome_dest} | {desc}", int(orig)))
                    # Receita no destino
                    cur.execute("""
                        INSERT INTO transacoes (usuario_id, data, valor, subconta_id, tipo, descricao, banco_id)
                        VALUES (%s,%s,%s,%s,'Receita',%s,%s)
                    """, (uid, data, valor, sub_id, f"Transf. ← {nome_orig} | {desc}", int(dest)))

            msg_transf.value = f"✅ Transferência de {fmt(valor)} realizada: {nome_orig} → {nome_dest}"
            msg_transf.color = ft.colors.GREEN_700
            transf_valor_f.value = ""
            transf_desc_f.value  = "Transferência entre bancos"
            carregar_transferencias()
            page.update()
        except Exception as ex:
            import traceback
            print(f"[bancos] transferencia erro: {ex}")
            traceback.print_exc()
            msg_transf.value = f"❌ Erro: {ex}"
            msg_transf.color = ft.colors.RED_700
            page.update()

    btn_salvar_banco   = ft.ElevatedButton("SALVAR BANCO",   bgcolor="#1565C0", color="white", on_click=salvar_banco)
    btn_salvar_cartao  = ft.ElevatedButton("SALVAR CARTÃO",  bgcolor="#E65100", color="white", on_click=salvar_cartao)
    btn_transferir     = ft.ElevatedButton("💸 TRANSFERIR",   bgcolor="#2E7D32", color="white", on_click=realizar_transferencia, height=45)

    carregar_listas()

    conteudo = ft.Column([
        ft.Row([ft.Icon(ft.icons.ACCOUNT_BALANCE, color="#1565C0", size=30),
                ft.Text("BANCOS E CARTÕES", size=22, weight="bold", color="#1565C0")], spacing=10),
        ft.Divider(),

        # ── CADASTRO BANCO ─────────────────────────────────────────────────
        ft.Container(
            bgcolor="#E3F2FD", border_radius=10, padding=16,
            content=ft.Column([
                ft.Text("🏦 Cadastrar / Editar Banco", size=15, weight="bold", color="#1565C0"),
                ft.Row([nome_banco_f, codigo_banco_f, agencia_f, conta_f], wrap=True, spacing=10),
                ft.Row([saldo_inicial_f, data_inicial_f, btn_salvar_banco], wrap=True, spacing=10),
                msg_banco,
            ], spacing=10)
        ),
        ft.Text("Bancos Cadastrados", size=15, weight="bold", color="#1565C0"),
        lista_bancos_col,
        ft.Divider(),

        # ── TRANSFERÊNCIA ENTRE BANCOS ─────────────────────────────────────
        ft.Container(
            bgcolor="#E8F5E9", border_radius=10, padding=16,
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.SWAP_HORIZ, color="#2E7D32", size=24),
                    ft.Text("💸 Transferência entre Bancos", size=15, weight="bold", color="#2E7D32"),
                ], spacing=8),
                ft.Row([
                    transf_orig_dd,
                    ft.Icon(ft.icons.ARROW_FORWARD, color="#2E7D32", size=24),
                    transf_dest_dd,
                ], spacing=12),
                ft.Row([transf_valor_f, transf_data_f, btn_data_transf, transf_desc_f], wrap=True, spacing=10),
                btn_transferir,
                msg_transf,
                ft.Divider(),
                ft.Text("Últimas transferências:", size=13, weight="bold", color="#2E7D32"),
                lista_transf,
            ], spacing=10)
        ),
        ft.Divider(),

        # ── CADASTRO CARTÃO ────────────────────────────────────────────────
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

    return ft.View(
        route="/bancos",
        controls=[
            get_menu(page), ft.Divider(),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=24, vertical=16),
                expand=True, content=conteudo)
        ]
    )