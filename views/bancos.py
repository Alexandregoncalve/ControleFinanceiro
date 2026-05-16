import flet as ft
from menu import get_menu
from database import db_session
from utils import limpar_valor, formatar_moeda_input
from datetime import datetime

CORES_BANCO = ["#1565C0", "#2E7D32", "#6A1B9A", "#00838F", "#E65100", "#AD1457", "#4527A0", "#37474F"]


def bancos_view(page: ft.Page):
    uid = page.session.get("user_id")
    state = {"editing_banco_id": None, "editing_cartao_id": None, "editing_transf_id": None}

    # ── CAMPOS BANCO ───────────────────────────────────────────────────────
    nome_banco_f    = ft.TextField(label="Nome do Banco",             width=250)
    codigo_banco_f  = ft.TextField(label="Cód. Banco",                width=130, hint_text="Ex: 237")
    agencia_f       = ft.TextField(label="Agência",                   width=185)
    conta_f         = ft.TextField(label="Nº Conta",                  width=185)
    saldo_inicial_f = ft.TextField(label="Saldo Inicial",             width=185, on_blur=formatar_moeda_input)
    data_inicial_f  = ft.TextField(label="Data Inicial (DD/MM/AAAA)", width=195,
                                   value=datetime.now().strftime("%d/%m/%Y"))
    msg_banco = ft.Text("", size=13)

    # ── CAMPOS CARTÃO ──────────────────────────────────────────────────────
    nome_cartao_f = ft.TextField(label="Nome do Cartão",              width=240)
    tipo_cartao_f = ft.Dropdown(label="Tipo", width=160,
        options=[ft.dropdown.Option("Crédito"), ft.dropdown.Option("Débito"), ft.dropdown.Option("Ambos")])
    limite_f   = ft.TextField(label="Limite (ex: 5.000,00)",          width=200, on_blur=formatar_moeda_input)
    banco_dd   = ft.Dropdown(label="Banco vinculado",                 width=220, options=[])
    msg_cartao = ft.Text("", size=13)

    lista_bancos_col  = ft.Column([], spacing=12)
    lista_cartoes_col = ft.Column([], spacing=12)

    # ── CAMPOS TRANSFERÊNCIA ───────────────────────────────────────────────
    transf_orig_dd  = ft.Dropdown(label="Banco Origem",  width=220, options=[])
    transf_dest_dd  = ft.Dropdown(label="Banco Destino", width=220, options=[])
    transf_valor_f  = ft.TextField(label="Valor", width=160, on_blur=formatar_moeda_input)
    transf_desc_f   = ft.TextField(label="Descrição", width=280, value="Transferência entre bancos")
    transf_data_f   = ft.TextField(label="Data", width=140, value=datetime.now().strftime("%d/%m/%Y"), read_only=True)
    msg_transf      = ft.Text("", size=13)
    lista_transf    = ft.Column([], spacing=6, scroll=ft.ScrollMode.AUTO, height=220)

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
            banco_dd.options       = opcoes
            transf_orig_dd.options = [ft.dropdown.Option("", "— Selecione —")] + opcoes
            transf_dest_dd.options = [ft.dropdown.Option("", "— Selecione —")] + opcoes
            page.update()
        except:
            pass

    # ── Calcula saldo real do banco (saldo_inicial + receitas - despesas) ──
    def saldo_real(banco_id, saldo_inicial):
        try:
            with db_session() as cur:
                cur.execute("""
                    SELECT
                        COALESCE(SUM(CASE WHEN tipo='Receita' THEN valor ELSE 0 END), 0) AS total_rec,
                        COALESCE(SUM(CASE WHEN tipo='Despesa' THEN valor ELSE 0 END), 0) AS total_desp
                    FROM transacoes
                    WHERE usuario_id=%s AND banco_id=%s
                """, (uid, banco_id))
                row = cur.fetchone()
            return float(saldo_inicial or 0) + float(row['total_rec']) - float(row['total_desp'])
        except:
            return float(saldo_inicial or 0)

    def card_banco(b, cor):
        codigo  = f" ({b['codigo_banco']})" if b['codigo_banco'] else ""
        s_real  = saldo_real(b['id'], b['saldo_inicial'])
        s_inic  = float(b['saldo_inicial'] or 0)
        diff    = s_real - s_inic
        diff_cor = ft.colors.GREEN_200 if diff >= 0 else ft.colors.RED_200
        diff_str = f"{'▲' if diff >= 0 else '▼'} {fmt(abs(diff))}"

        return ft.Container(
            width=300, border_radius=14, bgcolor=cor, padding=ft.padding.all(18),
            shadow=ft.BoxShadow(blur_radius=10, color=ft.colors.with_opacity(0.22, "black"), offset=ft.Offset(2, 4)),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.ACCOUNT_BALANCE, color="white", size=28),
                    ft.Column([
                        ft.Text(b['nome_banco'], color="white", weight="bold", size=15, expand=True),
                        ft.Text(f"Banco{codigo}", color="white70", size=11),
                    ], expand=True, spacing=2),
                ], spacing=10),
                ft.Text(f"Ag: {b['agencia'] or '—'} | Cta: {b['numero_conta'] or '—'}", color="white", size=12),
                ft.Divider(color=ft.colors.with_opacity(0.3, "white"), height=14),
                ft.Row([
                    ft.Column([
                        ft.Text("Saldo Atual", color=ft.colors.with_opacity(0.75, "white"), size=11),
                        ft.Text(fmt(s_real), color="white", size=20, weight="bold"),
                        ft.Text(f"Inicial: {fmt(s_inic)}  {diff_str}",
                                color=diff_cor, size=10),
                    ]),
                    ft.Column([
                        ft.Text("Início", color=ft.colors.with_opacity(0.75, "white"), size=11),
                        ft.Text(b['data_criacao'] if b['data_criacao'] else "—", color="white", size=11),
                    ], horizontal_alignment=ft.CrossAxisAlignment.END)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([
                    ft.TextButton("✏️ Editar",  style=ft.ButtonStyle(color="white"),
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
                    ft.Column([ft.Text("Limite",  color="white70", size=11),
                               ft.Text(fmt(c['limite'] or 0), color="white", size=16, weight="bold")]),
                    ft.Column([ft.Text("Banco",   color="white70", size=11),
                               ft.Text(banco_nome, color="white", size=13)])
                ], spacing=30),
                ft.Row([
                    ft.TextButton("✏️", on_click=lambda _, c=c: preparar_edicao_cartao(c)),
                    ft.TextButton("🗑️", on_click=lambda _, cid=c['id']: excluir_cartao(cid))
                ], alignment=ft.MainAxisAlignment.END)
            ], spacing=4)
        )

    # ── TRANSFERÊNCIAS ─────────────────────────────────────────────────────
    def carregar_transferencias():
        try:
            with db_session() as cur:
                cur.execute("""
                    SELECT t.id, t.data, t.valor, t.descricao,
                           bo.nome_banco AS origem, bd.nome_banco AS destino
                    FROM transferencias t
                    JOIN bancos bo ON t.banco_orig = bo.id
                    JOIN bancos bd ON t.banco_dest = bd.id
                    WHERE t.usuario_id=%s
                    ORDER BY t.data DESC, t.id DESC
                    LIMIT 30
                """, (uid,))
                rows = cur.fetchall()

            lista_transf.controls.clear()
            if not rows:
                lista_transf.controls.append(
                    ft.Text("Nenhuma transferência realizada.", color="grey", italic=True, size=12))
            else:
                for r in rows:
                    tid = r['id']
                    lista_transf.controls.append(
                        ft.Container(
                            border=ft.border.all(1, "#C8E6C9"), border_radius=8, padding=10,
                            bgcolor="white",
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
                                ft.Row([
                                    ft.IconButton(
                                        icon=ft.icons.EDIT, icon_color="#1565C0", tooltip="Editar",
                                        icon_size=18,
                                        on_click=lambda _, row=r: preparar_edicao_transf(row)
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.DELETE, icon_color=ft.colors.RED_400, tooltip="Excluir",
                                        icon_size=18,
                                        on_click=lambda _, tid=tid: excluir_transferencia(tid)
                                    ),
                                ], spacing=0),
                            ], alignment="spaceBetween", vertical_alignment=ft.CrossAxisAlignment.CENTER)
                        )
                    )
            page.update()
        except Exception as ex:
            print(f"[bancos] carregar_transferencias erro: {ex}")

    def preparar_edicao_transf(r):
        state["editing_transf_id"] = r['id']
        # Precisamos do banco_orig e banco_dest — buscar do banco
        try:
            with db_session() as cur:
                cur.execute("SELECT banco_orig, banco_dest, valor, descricao, data FROM transferencias WHERE id=%s AND usuario_id=%s",
                            (r['id'], uid))
                t = cur.fetchone()
            transf_orig_dd.value = str(t['banco_orig'])
            transf_dest_dd.value = str(t['banco_dest'])
            transf_valor_f.value = f"{float(t['valor']):_.2f}".replace(".", ",").replace("_", ".")
            transf_desc_f.value  = t['descricao'] or "Transferência entre bancos"
            transf_data_f.value  = t['data']
            btn_transferir.text  = "💾 SALVAR EDIÇÃO"
            btn_transferir.bgcolor = "#1565C0"
        except Exception as ex:
            print(f"[bancos] preparar_edicao_transf erro: {ex}")
        page.update()

    def excluir_transferencia(tid):
        try:
            with db_session() as cur:
                # Remove transações vinculadas (descrição contém o ID da transferência ou pela data/valor)
                cur.execute("SELECT banco_orig, banco_dest, valor, data, descricao FROM transferencias WHERE id=%s AND usuario_id=%s",
                            (tid, uid))
                t = cur.fetchone()
                if t:
                    # Remove transações de débito na origem e crédito no destino geradas por esta transferência
                    cur.execute("""
                        DELETE FROM transacoes
                        WHERE usuario_id=%s AND banco_id=%s AND tipo='Despesa'
                          AND data=%s AND valor=%s AND descricao LIKE %s
                    """, (uid, t['banco_orig'], t['data'], t['valor'], '%Transf.%'))
                    cur.execute("""
                        DELETE FROM transacoes
                        WHERE usuario_id=%s AND banco_id=%s AND tipo='Receita'
                          AND data=%s AND valor=%s AND descricao LIKE %s
                    """, (uid, t['banco_dest'], t['data'], t['valor'], '%Transf.%'))
                cur.execute("DELETE FROM transferencias WHERE id=%s AND usuario_id=%s", (tid, uid))
            carregar_listas()
        except Exception as ex:
            print(f"[bancos] excluir_transferencia erro: {ex}")

    def cancelar_edicao_transf():
        state["editing_transf_id"] = None
        transf_orig_dd.value = ""
        transf_dest_dd.value = ""
        transf_valor_f.value = ""
        transf_desc_f.value  = "Transferência entre bancos"
        transf_data_f.value  = datetime.now().strftime("%d/%m/%Y")
        btn_transferir.text   = "💸 TRANSFERIR"
        btn_transferir.bgcolor = "#2E7D32"
        page.update()

    def carregar_listas():
        try:
            with db_session() as cur:
                cur.execute("""
                    SELECT id, nome_banco, saldo_inicial,
                           COALESCE(data_criacao, '') AS data_criacao,
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

    # ── BANCO CRUD ─────────────────────────────────────────────────────────
    def salvar_banco(e):
        nome     = nome_banco_f.value.strip()
        codigo   = codigo_banco_f.value.strip()
        ag       = agencia_f.value.strip()
        cta      = conta_f.value.strip()
        saldo    = limpar_valor(saldo_inicial_f.value.strip() or "0")
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
            nome_banco_f.value = agencia_f.value = conta_f.value = ""
            saldo_inicial_f.value = codigo_banco_f.value = ""
            data_inicial_f.value  = datetime.now().strftime("%d/%m/%Y")
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

    # ── CARTÃO CRUD ────────────────────────────────────────────────────────
    def salvar_cartao(e):
        nome = nome_cartao_f.value.strip()
        tipo = tipo_cartao_f.value
        lim  = limpar_valor(limite_f.value.strip() or "0")
        bid  = banco_dd.value
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

    # ── TRANSFERÊNCIA ──────────────────────────────────────────────────────
    def realizar_transferencia(e):
        msg_transf.value = ""
        orig  = transf_orig_dd.value
        dest  = transf_dest_dd.value
        valor = limpar_valor(transf_valor_f.value or "0")
        data  = transf_data_f.value.strip()
        desc  = transf_desc_f.value.strip() or "Transferência entre bancos"

        if not orig or orig == "":
            msg_transf.value = "⚠️ Selecione o banco de origem."; msg_transf.color = ft.colors.ORANGE_700
            page.update(); return
        if not dest or dest == "":
            msg_transf.value = "⚠️ Selecione o banco de destino."; msg_transf.color = ft.colors.ORANGE_700
            page.update(); return
        if orig == dest:
            msg_transf.value = "⚠️ Origem e destino não podem ser iguais."; msg_transf.color = ft.colors.ORANGE_700
            page.update(); return
        if valor <= 0:
            msg_transf.value = "⚠️ Informe um valor válido."; msg_transf.color = ft.colors.ORANGE_700
            page.update(); return

        try:
            with db_session() as cur:
                cur.execute("SELECT nome_banco FROM bancos WHERE id=%s", (int(orig),))
                nome_orig = cur.fetchone()['nome_banco']
                cur.execute("SELECT nome_banco FROM bancos WHERE id=%s", (int(dest),))
                nome_dest = cur.fetchone()['nome_banco']

                if state["editing_transf_id"]:
                    # ── EDITAR: remove transações antigas e recria ──────────
                    cur.execute("SELECT banco_orig, banco_dest, valor, data FROM transferencias WHERE id=%s AND usuario_id=%s",
                                (state["editing_transf_id"], uid))
                    old = cur.fetchone()
                    if old:
                        cur.execute("""DELETE FROM transacoes
                            WHERE usuario_id=%s AND banco_id=%s AND tipo='Despesa'
                              AND data=%s AND valor=%s AND descricao LIKE %s""",
                            (uid, old['banco_orig'], old['data'], old['valor'], '%Transf.%'))
                        cur.execute("""DELETE FROM transacoes
                            WHERE usuario_id=%s AND banco_id=%s AND tipo='Receita'
                              AND data=%s AND valor=%s AND descricao LIKE %s""",
                            (uid, old['banco_dest'], old['data'], old['valor'], '%Transf.%'))
                    cur.execute("""UPDATE transferencias
                        SET banco_orig=%s, banco_dest=%s, valor=%s, data=%s, descricao=%s
                        WHERE id=%s AND usuario_id=%s""",
                        (int(orig), int(dest), valor, data, desc, state["editing_transf_id"], uid))
                    transf_id = state["editing_transf_id"]
                    state["editing_transf_id"] = None
                    btn_transferir.text   = "💸 TRANSFERIR"
                    btn_transferir.bgcolor = "#2E7D32"
                else:
                    # ── NOVA transferência ──────────────────────────────────
                    cur.execute("""
                        INSERT INTO transferencias (usuario_id, data, valor, banco_orig, banco_dest, descricao)
                        VALUES (%s,%s,%s,%s,%s,%s)
                    """, (uid, data, valor, int(orig), int(dest), desc))
                    transf_id = cur.lastrowid

                # ── Busca subconta de transferência (ou usa NULL) ──────────
                cur.execute("""
                    SELECT s.id FROM subcontas s
                    JOIN categorias c ON s.categoria_id = c.id
                    WHERE s.usuario_id=%s AND UPPER(s.nome) LIKE '%%TRANSFER%%'
                    LIMIT 1
                """, (uid,))
                sub_row   = cur.fetchone()
                sub_id    = sub_row['id'] if sub_row else None

                # ── Se não achou subconta, busca qualquer subconta do usuário ──
                if not sub_id:
                    cur.execute("SELECT id FROM subcontas WHERE usuario_id=%s LIMIT 1", (uid,))
                    fallback = cur.fetchone()
                    sub_id = fallback['id'] if fallback else None

                if sub_id:
                    # Despesa na origem (saída de dinheiro)
                    cur.execute("""
                        INSERT INTO transacoes
                            (usuario_id, data, valor, subconta_id, tipo, descricao, banco_id)
                        VALUES (%s,%s,%s,%s,'Despesa',%s,%s)
                    """, (uid, data, valor, sub_id,
                          f"Transf. → {nome_dest} | {desc}", int(orig)))

                    # Receita no destino (entrada de dinheiro)
                    cur.execute("""
                        INSERT INTO transacoes
                            (usuario_id, data, valor, subconta_id, tipo, descricao, banco_id)
                        VALUES (%s,%s,%s,%s,'Receita',%s,%s)
                    """, (uid, data, valor, sub_id,
                          f"Transf. ← {nome_orig} | {desc}", int(dest)))
                else:
                    msg_transf.value = "⚠️ Transferência salva, mas sem subconta de transferência cadastrada. Crie uma subconta com 'Transf' no nome."
                    msg_transf.color = ft.colors.ORANGE_700

            if not msg_transf.value:
                msg_transf.value = f"✅ Transferência de {fmt(valor)}: {nome_orig} → {nome_dest}"
                msg_transf.color = ft.colors.GREEN_700

            transf_valor_f.value = ""
            transf_desc_f.value  = "Transferência entre bancos"
            transf_orig_dd.value = ""
            transf_dest_dd.value = ""
            carregar_listas()
        except Exception as ex:
            import traceback; traceback.print_exc()
            msg_transf.value = f"❌ Erro: {ex}"
            msg_transf.color = ft.colors.RED_700
            page.update()

    # ── BOTÕES PRINCIPAIS ──────────────────────────────────────────────────
    btn_salvar_banco  = ft.ElevatedButton("SALVAR BANCO",  bgcolor="#1565C0", color="white", on_click=salvar_banco)
    btn_salvar_cartao = ft.ElevatedButton("SALVAR CARTÃO", bgcolor="#E65100", color="white", on_click=salvar_cartao)
    btn_transferir    = ft.ElevatedButton("💸 TRANSFERIR",  bgcolor="#2E7D32", color="white",
                                          on_click=realizar_transferencia, height=45)
    btn_cancelar_transf = ft.TextButton(
        "✖ Cancelar edição",
        style=ft.ButtonStyle(color=ft.colors.RED_400),
        on_click=lambda _: cancelar_edicao_transf()
    )

    carregar_listas()

    # ── LAYOUT ─────────────────────────────────────────────────────────────

    # Formulário Banco — azul claro com borda azul
    form_banco = ft.Container(
        bgcolor="#E3F2FD",
        border=ft.border.all(2, "#90CAF9"),
        border_radius=12, padding=20, expand=True,
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.icons.ACCOUNT_BALANCE, color="#1565C0", size=22),
                ft.Text("Cadastrar / Editar Banco", size=15, weight="bold", color="#1565C0"),
            ], spacing=8),
            ft.Divider(color="#90CAF9", height=14),
            # Linha 1: nome + código + agência + conta
            ft.Row([nome_banco_f, codigo_banco_f, agencia_f, conta_f], wrap=True, spacing=12),
            # Linha 2: saldo + data
            ft.Row([saldo_inicial_f, data_inicial_f], wrap=True, spacing=12),
            btn_salvar_banco,
            msg_banco,
        ], spacing=16)
    )

    # Formulário Cartão — laranja claro com borda laranja
    form_cartao = ft.Container(
        bgcolor="#FFF3E0",
        border=ft.border.all(2, "#FFCC80"),
        border_radius=12, padding=20, expand=True,
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.icons.CREDIT_CARD, color="#E65100", size=22),
                ft.Text("Cadastrar / Editar Cartão", size=15, weight="bold", color="#E65100"),
            ], spacing=8),
            ft.Divider(color="#FFCC80", height=14),
            ft.Row([nome_cartao_f, tipo_cartao_f], wrap=True, spacing=12),
            ft.Row([limite_f, banco_dd], wrap=True, spacing=12),
            btn_salvar_cartao,
            msg_cartao,
        ], spacing=16)
    )

    # Coluna de bancos cadastrados — fundo azul claro
    col_bancos = ft.Container(
        expand=True,
        bgcolor="#E3F2FD",
        border=ft.border.all(1.5, "#90CAF9"),
        border_radius=12,
        padding=ft.padding.all(14),
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.icons.ACCOUNT_BALANCE, color="#1565C0", size=18),
                ft.Text("Bancos Cadastrados", size=14, weight="bold", color="#1565C0"),
            ], spacing=6),
            ft.Divider(color="#90CAF9", height=10),
            lista_bancos_col,
        ], spacing=10)
    )

    # Coluna de cartões cadastrados — fundo laranja claro
    col_cartoes = ft.Container(
        expand=True,
        bgcolor="#FFF3E0",
        border=ft.border.all(1.5, "#FFCC80"),
        border_radius=12,
        padding=ft.padding.all(14),
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.icons.CREDIT_CARD, color="#E65100", size=18),
                ft.Text("Cartões Cadastrados", size=14, weight="bold", color="#E65100"),
            ], spacing=6),
            ft.Divider(color="#FFCC80", height=10),
            lista_cartoes_col,
        ], spacing=10)
    )

    conteudo = ft.Column([
        # ── Título ────────────────────────────────────────────────────────
        ft.Row([
            ft.Icon(ft.icons.ACCOUNT_BALANCE, color="#1565C0", size=30),
            ft.Text("BANCOS E CARTÕES", size=22, weight="bold", color="#1565C0")
        ], spacing=10),
        ft.Divider(),

        # ── LINHA 1: Formulários lado a lado ──────────────────────────────
        ft.Row([form_banco, form_cartao],
               spacing=16, vertical_alignment=ft.CrossAxisAlignment.START),
        ft.Divider(),

        # ── LINHA 2: Cards lado a lado ────────────────────────────────────
        ft.Row([col_bancos, col_cartoes],
               spacing=16, vertical_alignment=ft.CrossAxisAlignment.START),
        ft.Divider(),

        # ── LINHA 3: Transferência entre Bancos ───────────────────────────
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
                ], spacing=12, wrap=True),
                ft.Row([transf_valor_f, transf_data_f, btn_data_transf, transf_desc_f],
                       wrap=True, spacing=10),
                ft.Row([btn_transferir, btn_cancelar_transf], spacing=12),
                msg_transf,
                ft.Divider(),
                ft.Text("Últimas transferências:", size=13, weight="bold", color="#2E7D32"),
                lista_transf,
            ], spacing=10)
        ),
    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)

    # ── Recarrega ao entrar na view (garante dados atualizados) ──────────
    def on_view_appear(e=None):
        carregar_listas()

    page.on_view_pop = lambda e: None  # evita conflito
    # Usa on_resized como gatilho de "voltou para a view"
    # A forma mais confiável no Flet é registrar no route_change
    def _on_route(e):
        if page.route == "/bancos":
            carregar_listas()

    # Registra sem sobrescrever handler existente
    _prev_route_handler = getattr(page, "_bancos_route_handler", None)
    page._bancos_route_handler = _on_route
    page.on_route_change = _on_route

    return ft.View(
        route="/bancos",
        controls=[
            get_menu(page), ft.Divider(),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=24, vertical=16),
                expand=True, content=conteudo)
        ]
    )