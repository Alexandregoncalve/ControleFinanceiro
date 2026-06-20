import flet as ft
from datetime import datetime, date
from menu import get_menu
from database import get_connection, get_cursor
from utils import formatar_moeda_input, limpar_valor


def dividas_view(page):
    def fmt(v):
        return f"R$ {v:_.2f}".replace(".", ",").replace("_", ".")

    hoje = datetime.now().date()
    uid = page.session.get("user_id")

    if not uid:
        return ft.View(
            route="/dividas",
            controls=[ft.Text("Sessão expirada. Faça login novamente.", color="red", size=16)]
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  HELPERS
    # ──────────────────────────────────────────────────────────────────────────
    def parse_data(s):
        if not s:
            return None
        s = str(s).strip()
        for fmt_str in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt_str).date()
            except ValueError:
                pass
        return None

    def fmt_data(d):
        if not d:
            return "—"
        try:
            if isinstance(d, str):
                d = parse_data(d)
            return d.strftime("%d/%m/%Y")
        except Exception:
            return str(d)

    def get_conn():
        conn = get_connection()
        cur  = get_cursor(conn)
        return conn, cur

    def fechar_dlg(dlg):
        dlg.open = False
        page.update()

    def confirmar_acao(titulo, mensagem, on_confirmar):
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(titulo, color="#C62828", weight="bold"),
            content=ft.Text(mensagem, size=13),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: fechar_dlg(dlg)),
                ft.ElevatedButton(
                    "Confirmar", bgcolor="#C62828", color=ft.colors.WHITE,
                    on_click=lambda e: [fechar_dlg(dlg), on_confirmar()],
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def set_msg(campo, texto, ok=True):
        campo.value = f"{'✅' if ok else '❌'} {texto}"
        campo.color = ft.colors.GREEN_700 if ok else ft.colors.RED_700
        page.update()

    # ──────────────────────────────────────────────────────────────────────────
    #  ESTADO DO FORMULÁRIO (tipo de controle selecionado)
    # ──────────────────────────────────────────────────────────────────────────
    tipo_selecionado = {"value": "livre"}  # 'parcelada' ou 'livre'

    # ─── Campos comuns ────────────────────────────────────────────────────────
    tf_nome        = ft.TextField(label="Nome da Dívida", width=280, hint_text="Ex: Empréstimo Banco X")
    tf_valor_total = ft.TextField(label="Valor Total (R$)", width=160, on_blur=formatar_moeda_input)
    msg_form       = ft.Text("", size=12)

    # ─── Campos apenas para PARCELADA ─────────────────────────────────────────
    tf_valor_parc  = ft.TextField(label="Valor da Parcela (R$)", width=170, on_blur=formatar_moeda_input)
    tf_total_parc  = ft.TextField(label="Nº Parcelas", width=120, keyboard_type=ft.KeyboardType.NUMBER)
    tf_dia_venc    = ft.TextField(label="Dia Vencimento", width=130, keyboard_type=ft.KeyboardType.NUMBER)
    tf_data_inicio = ft.TextField(label="Data Início (DD/MM/AAAA)", width=200, hint_text="01/01/2025")
    tf_taxa        = ft.TextField(label="Juros % a.m.", width=130, on_blur=formatar_moeda_input)

    campos_parcelada = ft.Row(
        [tf_valor_parc, tf_total_parc, tf_dia_venc, tf_data_inicio, tf_taxa],
        spacing=10, wrap=True, visible=False,
    )

    aviso_parcelada = ft.Container(
        visible=False,
        bgcolor="#E3F2FD", border_radius=8, padding=10,
        content=ft.Row([
            ft.Icon(ft.icons.INFO_OUTLINE, color="#1565C0", size=16),
            ft.Text(
                "Uma conta fixa será criada automaticamente e aparecerá em Contas Fixas todo mês para você dar baixa.",
                size=12, color="#1565C0", italic=True,
            ),
        ], spacing=8),
    )

    aviso_livre = ft.Container(
        visible=True,
        bgcolor="#FFF3E0", border_radius=8, padding=10,
        content=ft.Row([
            ft.Icon(ft.icons.INFO_OUTLINE, color="#E65100", size=16),
            ft.Text(
                "Sem vencimento fixo. Você registra o pagamento quando e quanto quiser, abatendo do saldo devedor.",
                size=12, color="#E65100", italic=True,
            ),
        ], spacing=8),
    )

    # ─── Botões de seleção do tipo ─────────────────────────────────────────────
    def selecionar_tipo(tipo):
        tipo_selecionado["value"] = tipo
        btn_parcelada.bgcolor = "#1565C0" if tipo == "parcelada" else "#E0E0E0"
        btn_parcelada.color   = ft.colors.WHITE if tipo == "parcelada" else "#555"
        btn_livre.bgcolor     = "#E65100" if tipo == "livre" else "#E0E0E0"
        btn_livre.color       = ft.colors.WHITE if tipo == "livre" else "#555"
        campos_parcelada.visible = tipo == "parcelada"
        aviso_parcelada.visible  = tipo == "parcelada"
        aviso_livre.visible      = tipo == "livre"
        page.update()

    btn_parcelada = ft.ElevatedButton(
        "🔵 PARCELADA",
        bgcolor="#E0E0E0", color="#555",
        on_click=lambda e: selecionar_tipo("parcelada"),
        tooltip="Valor fixo por parcela, dia de vencimento definido → gera conta fixa automática",
    )
    btn_livre = ft.ElevatedButton(
        "🟠 PAGAMENTO LIVRE",
        bgcolor="#E65100", color=ft.colors.WHITE,
        on_click=lambda e: selecionar_tipo("livre"),
        tooltip="Paga quando e quanto quiser → registra pagamento avulso",
    )

    # ─── Campos do pagamento avulso ───────────────────────────────────────────
    dd_divida_pag  = ft.Dropdown(label="Dívida", width=280, disabled=True)
    tf_valor_pag   = ft.TextField(label="Valor Pago (R$)", width=160, on_blur=formatar_moeda_input)
    tf_data_pag    = ft.TextField(
        label="Data Pagamento (DD/MM/AAAA)", width=210,
        value=hoje.strftime("%d/%m/%Y"),
    )
    tf_obs_pag     = ft.TextField(label="Observação (opcional)", width=260)
    msg_pag        = ft.Text("", size=12)

    lista_dividas  = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    resumo_row     = ft.Row(spacing=12, wrap=True)

    # ──────────────────────────────────────────────────────────────────────────
    #  CARREGAR DROPDOWN DE DÍVIDAS ATIVAS (pagamento avulso)
    # ──────────────────────────────────────────────────────────────────────────
    def carregar_dropdown():
        try:
            conn, cur = get_conn()
            cur.execute("""
                SELECT id, nome, tipo_controle FROM dividas
                WHERE usuario_id=%s AND status='ativa'
                ORDER BY nome
            """, (uid,))
            rows = cur.fetchall()
            conn.close()
            if rows:
                dd_divida_pag.options = [
                    ft.dropdown.Option(str(r['id']), f"{r['nome']} ({'livre' if r['tipo_controle']=='livre' else 'parcelada'})")
                    for r in rows
                ]
                dd_divida_pag.disabled = False
                dd_divida_pag.hint_text = "Selecione a dívida"
            else:
                dd_divida_pag.options = []
                dd_divida_pag.disabled = True
                dd_divida_pag.hint_text = "Nenhuma dívida ativa"
            page.update()
        except Exception as ex:
            print(f"[dividas] carregar_dropdown: {ex}")

    # ──────────────────────────────────────────────────────────────────────────
    #  BUILD CARD DE DÍVIDA
    # ──────────────────────────────────────────────────────────────────────────
    def build_card(divida, pagamentos):
        did           = divida['id']
        nome          = divida['nome']
        val_total     = float(divida['valor_total'] or 0)
        tot_parc      = divida.get('total_parcelas')
        dia_venc      = divida.get('dia_vencimento')
        taxa          = float(divida.get('taxa_juros') or 0)
        status        = divida.get('status', 'ativa')
        tipo          = divida.get('tipo_controle', 'livre')
        data_ini      = fmt_data(divida.get('data_inicio'))
        val_parcela   = float(divida.get('valor_parcela') or 0)

        total_pago    = sum(float(p['valor']) for p in pagamentos)
        saldo         = max(val_total - total_pago, 0.0)
        parc_pagas    = len(pagamentos)
        tot_parc_n    = int(tot_parc) if tot_parc else None
        progresso     = min(parc_pagas / tot_parc_n, 1.0) if tot_parc_n else (1.0 if saldo <= 0 else 0.0)

        # Badge status
        if status == 'quitada' or saldo <= 0:
            badge_cor, badge_label, badge_icon = "#43A047", "Quitada", ft.icons.CHECK_CIRCLE
        else:
            datas_pag = [parse_data(p['data']) for p in pagamentos if p.get('data')]
            ultima    = max(datas_pag) if datas_pag else None
            if tipo == 'parcelada' and ultima and (hoje - ultima).days > 35:
                badge_cor, badge_label, badge_icon = "#C62828", "Atrasado", ft.icons.WARNING_AMBER_ROUNDED
            elif not datas_pag:
                badge_cor, badge_label, badge_icon = "#F57F17", "Sem pagto", ft.icons.SCHEDULE
            else:
                badge_cor, badge_label, badge_icon = "#1565C0", "Em dia", ft.icons.CHECK_CIRCLE_OUTLINE

        # Tag do tipo
        tipo_cor    = "#1565C0" if tipo == "parcelada" else "#E65100"
        tipo_label  = "Parcelada" if tipo == "parcelada" else "Pagto Livre"

        det_col = ft.Column(spacing=4, visible=False)

        def toggle(e):
            det_col.visible = not det_col.visible
            btn_exp.icon = ft.icons.EXPAND_LESS if det_col.visible else ft.icons.EXPAND_MORE
            page.update()

        btn_exp = ft.IconButton(
            icon=ft.icons.EXPAND_MORE, tooltip="Ver pagamentos",
            icon_color="#1565C0", icon_size=20, on_click=toggle,
        )

        def on_excluir():
            try:
                conn, cur = get_conn()
                # Remove subconta fixa vinculada se existir
                cur.execute("SELECT subconta_id FROM dividas WHERE id=%s", (did,))
                row = cur.fetchone()
                if row and row['subconta_id']:
                    cur.execute(
                        "UPDATE subcontas SET divida_id=NULL, fixa=0 WHERE id=%s AND divida_id=%s",
                        (row['subconta_id'], did)
                    )
                cur.execute("DELETE FROM dividas WHERE id=%s AND usuario_id=%s", (did, uid))
                conn.commit()
                conn.close()
                carregar_tudo()
                carregar_dropdown()
            except Exception as ex:
                print(f"[dividas] excluir divida: {ex}")

        def on_quitar():
            try:
                conn, cur = get_conn()
                cur.execute("""
                    UPDATE dividas SET status='quitada', data_quitacao=%s
                    WHERE id=%s AND usuario_id=%s
                """, (hoje, did, uid))
                # Desativa subconta fixa vinculada
                cur.execute("SELECT subconta_id FROM dividas WHERE id=%s", (did,))
                row = cur.fetchone()
                if row and row['subconta_id']:
                    cur.execute(
                        "UPDATE subcontas SET fixa=0 WHERE id=%s AND divida_id=%s",
                        (row['subconta_id'], did)
                    )
                conn.commit()
                conn.close()
                carregar_tudo()
                carregar_dropdown()
            except Exception as ex:
                print(f"[dividas] quitar: {ex}")

        btn_excluir = ft.IconButton(
            icon=ft.icons.DELETE_FOREVER, tooltip="Excluir dívida",
            icon_color="#C62828", icon_size=20,
            on_click=lambda e: confirmar_acao(
                "Excluir Dívida",
                f"Excluir '{nome}' e todos os seus pagamentos?",
                on_excluir,
            ),
        )
        btn_quitar = ft.IconButton(
            icon=ft.icons.DONE_ALL, tooltip="Marcar como quitada",
            icon_color="#43A047", icon_size=20,
            on_click=lambda e: confirmar_acao(
                "Quitar Dívida", f"Marcar '{nome}' como quitada?", on_quitar,
            ),
        ) if status == 'ativa' else ft.Container()

        # Linhas de pagamento
        if pagamentos:
            for p in sorted(pagamentos, key=lambda x: parse_data(x['data']) or date.min):
                pid   = p['id']
                val_p = float(p['valor'])
                dat_p = fmt_data(p.get('data'))
                obs_p = p.get('observacao') or ''

                def make_fn(pid_=pid, val_=val_p, dt_=dat_p):
                    def fn():
                        try:
                            conn, cur = get_conn()
                            cur.execute(
                                "SELECT transacao_id FROM divida_pagamentos WHERE id=%s", (pid_,)
                            )
                            row = cur.fetchone()
                            if row and row['transacao_id']:
                                cur.execute("DELETE FROM transacoes WHERE id=%s", (row['transacao_id'],))
                            cur.execute(
                                "DELETE FROM divida_pagamentos WHERE id=%s AND usuario_id=%s",
                                (pid_, uid)
                            )
                            conn.commit()
                            conn.close()
                            carregar_tudo()
                        except Exception as ex:
                            print(f"[dividas] excluir pagamento: {ex}")
                    return fn

                det_col.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.icons.RECEIPT_LONG, size=14, color="#1565C0"),
                            ft.Text(dat_p, size=11, width=90),
                            ft.Text(obs_p, size=11, color="grey", expand=True),
                            ft.Text(fmt(val_p), size=12, weight="bold", color="#C62828"),
                            ft.IconButton(
                                icon=ft.icons.DELETE_OUTLINE,
                                tooltip="Excluir pagamento",
                                icon_color="#C62828", icon_size=15,
                                on_click=lambda e, f=make_fn(), v=val_p, d=dat_p: confirmar_acao(
                                    "Excluir Pagamento",
                                    f"Excluir pagamento de {fmt(v)} em {d}?",
                                    f,
                                ),
                            ),
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.padding.symmetric(horizontal=12, vertical=4),
                        bgcolor="#F5F6FA", border_radius=6,
                    )
                )
        else:
            det_col.controls.append(
                ft.Text("Nenhum pagamento registrado ainda.", size=11, color="grey", italic=True)
            )

        # Info extras
        info_parts = []
        if tipo == 'parcelada':
            if val_parcela > 0:
                info_parts.append(f"Parcela: {fmt(val_parcela)}")
            if dia_venc:
                info_parts.append(f"Vence dia {dia_venc}")
            if data_ini and data_ini != "—":
                info_parts.append(f"Início: {data_ini}")
            if taxa > 0:
                info_parts.append(f"Juros: {taxa:.2f}% a.m.")
        info_str = "  •  ".join(info_parts)

        prog_texto = f"{parc_pagas}/{tot_parc_n} parcelas pagas" if tot_parc_n else f"{parc_pagas} pagamento(s)"

        return ft.Container(
            content=ft.Column([
                # Cabeçalho
                ft.Row([
                    ft.Column([
                        ft.Row([
                            ft.Text(nome, size=14, weight="bold"),
                            ft.Container(
                                content=ft.Text(tipo_label, size=10, color=tipo_cor, weight="bold"),
                                padding=ft.padding.symmetric(horizontal=7, vertical=2),
                                border=ft.border.all(1, tipo_cor),
                                border_radius=12,
                            ),
                        ], spacing=8),
                        ft.Text(info_str, size=10, color="grey") if info_str else ft.Container(height=0),
                    ], expand=True),
                    # Badge status
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(badge_icon, size=13, color=badge_cor),
                            ft.Text(badge_label, size=11, color=badge_cor, weight="bold"),
                        ], spacing=3),
                        padding=ft.padding.symmetric(horizontal=8, vertical=3),
                        border=ft.border.all(1, badge_cor), border_radius=20,
                    ),
                    ft.Column([
                        ft.Text("Total pago", size=10, color="grey"),
                        ft.Text(fmt(total_pago), size=13, weight="bold", color="#C62828"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.END),
                    ft.Column([
                        ft.Text("Saldo devedor", size=10, color="grey"),
                        ft.Text(
                            fmt(saldo) if saldo > 0 else "Quitado",
                            size=13, weight="bold",
                            color="#E65100" if saldo > 0 else "#43A047",
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.END),
                    ft.Column([
                        ft.Text("Valor total", size=10, color="grey"),
                        ft.Text(fmt(val_total), size=12, color="grey"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.END),
                    btn_exp, btn_quitar, btn_excluir,
                ], alignment="spaceBetween", vertical_alignment=ft.CrossAxisAlignment.CENTER),

                # Barra de progresso
                ft.Column([
                    ft.Row([
                        ft.Text(prog_texto, size=10, color="grey", expand=True),
                        ft.Text(f"{int(progresso * 100)}%", size=10, color="#1565C0", weight="bold"),
                    ]),
                    ft.ProgressBar(
                        value=progresso, bgcolor="#E0E0E0",
                        color="#43A047" if progresso >= 1.0 else tipo_cor,
                        height=6, border_radius=4,
                    ),
                ], spacing=2),

                det_col,
            ], spacing=8),
            padding=ft.padding.symmetric(vertical=12, horizontal=14),
            border=ft.border.all(1, "#E0E0E0"),
            border_radius=10, bgcolor=ft.colors.WHITE,
            shadow=ft.BoxShadow(blur_radius=3, color=ft.colors.BLACK12),
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  CARREGAR TUDO
    # ──────────────────────────────────────────────────────────────────────────
    def carregar_tudo():
        try:
            conn, cur = get_conn()
            cur.execute("SELECT * FROM dividas WHERE usuario_id=%s ORDER BY status, nome", (uid,))
            dividas = cur.fetchall()
            cur.execute("SELECT * FROM divida_pagamentos WHERE usuario_id=%s ORDER BY data", (uid,))
            todos_pag = cur.fetchall()
            conn.close()

            lista_dividas.controls = []
            if not dividas:
                lista_dividas.controls = [
                    ft.Text("Nenhuma dívida cadastrada.", color="grey", italic=True, size=13)
                ]
                resumo_row.controls = []
                page.update()
                return

            mapa_pag = {}
            for p in todos_pag:
                mapa_pag.setdefault(p['divida_id'], []).append(p)

            total_pago_geral  = 0.0
            saldo_total_geral = 0.0
            qtd_ativas        = 0
            qtd_quitadas      = 0

            for d in dividas:
                pags  = mapa_pag.get(d['id'], [])
                pago  = sum(float(p['valor']) for p in pags)
                saldo = max(float(d['valor_total'] or 0) - pago, 0.0)
                total_pago_geral  += pago
                saldo_total_geral += saldo
                if d['status'] == 'ativa':
                    qtd_ativas += 1
                else:
                    qtd_quitadas += 1
                lista_dividas.controls.append(build_card(d, pags))

            def _card(titulo, valor, sub, cor, icon):
                return ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(titulo, size=11, weight="bold", color=ft.colors.WHITE),
                            ft.Icon(icon, size=16, color=ft.colors.WHITE),
                        ], alignment="spaceBetween"),
                        ft.Text(valor, size=20, weight="bold", color=ft.colors.WHITE),
                        ft.Text(sub, size=10, color=ft.colors.WHITE70),
                    ], spacing=6),
                    padding=16, bgcolor=cor, border_radius=12, width=240,
                    shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26),
                )

            resumo_row.controls = [
                _card("💸 TOTAL PAGO",    fmt(total_pago_geral),  "soma de todos os pagamentos", "#C62828", ft.icons.PAYMENTS),
                _card("📋 DÍVIDAS ATIVAS", str(qtd_ativas),        "dívidas em aberto",           "#1565C0", ft.icons.LIST_ALT),
                _card("⏳ SALDO DEVEDOR",  fmt(saldo_total_geral), "total ainda a pagar",         "#E65100", ft.icons.ACCOUNT_BALANCE_WALLET),
                _card("✅ QUITADAS",        str(qtd_quitadas),      "dívidas encerradas",          "#43A047", ft.icons.DONE_ALL),
            ]
            page.update()
        except Exception as ex:
            import traceback; traceback.print_exc()
            print(f"[dividas] carregar_tudo: {ex}")

    # ──────────────────────────────────────────────────────────────────────────
    #  REGISTRAR NOVA DÍVIDA
    # ──────────────────────────────────────────────────────────────────────────
    def registrar_divida(e):
        nome_v = tf_nome.value.strip()
        if not nome_v:
            return set_msg(msg_form, "Informe o nome da dívida.", False)
        valor_v = limpar_valor(tf_valor_total.value)
        if valor_v <= 0:
            return set_msg(msg_form, "Informe o valor total da dívida.", False)

        tipo_v = tipo_selecionado["value"]

        # Validações para parcelada
        val_parc_v = 0.0
        parc_v     = None
        dia_v      = None
        dt_ini_v   = None
        taxa_v     = 0.0

        if tipo_v == "parcelada":
            val_parc_v = limpar_valor(tf_valor_parc.value)
            if val_parc_v <= 0:
                return set_msg(msg_form, "Informe o valor da parcela.", False)
            if not tf_total_parc.value.strip():
                return set_msg(msg_form, "Informe o número de parcelas.", False)
            if not tf_dia_venc.value.strip():
                return set_msg(msg_form, "Informe o dia de vencimento.", False)
            try:
                parc_v = int(tf_total_parc.value.strip())
                dia_v  = int(tf_dia_venc.value.strip())
                taxa_v = limpar_valor(tf_taxa.value) if tf_taxa.value.strip() else 0.0
                dt_ini_v = parse_data(tf_data_inicio.value) if tf_data_inicio.value.strip() else None
            except ValueError as ex:
                return set_msg(msg_form, f"Valor inválido: {ex}", False)

        try:
            conn, cur = get_conn()

            cur.execute("""
                INSERT INTO dividas
                    (usuario_id, nome, tipo_controle, valor_total, valor_parcela,
                     total_parcelas, dia_vencimento, data_inicio, taxa_juros, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'ativa')
                RETURNING id
            """, (uid, nome_v, tipo_v, valor_v, val_parc_v or None,
                  parc_v, dia_v, dt_ini_v, taxa_v))
            divida_id = cur.fetchone()['id']

            # Se parcelada → cria subconta fixa automaticamente
            if tipo_v == "parcelada":
                # Busca ou cria categoria "DÍVIDAS"
                cur.execute("""
                    SELECT id FROM categorias
                    WHERE usuario_id=%s AND UPPER(unaccent(nome)) LIKE '%%DIVIDA%%'
                    LIMIT 1
                """, (uid,))
                cat = cur.fetchone()
                if not cat:
                    cur.execute("""
                        INSERT INTO categorias (usuario_id, nome, tipo)
                        VALUES (%s, 'DÍVIDAS', 'Despesa') RETURNING id
                    """, (uid,))
                    cat_id = cur.fetchone()['id']
                else:
                    cat_id = cat['id']

                cur.execute("""
                    INSERT INTO subcontas
                        (usuario_id, categoria_id, nome, fixa, dia_vencimento, divida_id)
                    VALUES (%s, %s, %s, 1, %s, %s)
                """, (uid, cat_id, nome_v, dia_v, divida_id))

                # Atualiza divida com subconta_id gerada
                cur.execute("SELECT id FROM subcontas WHERE divida_id=%s", (divida_id,))
                sub_row = cur.fetchone()
                if sub_row:
                    cur.execute("UPDATE dividas SET subconta_id=%s WHERE id=%s",
                                (sub_row['id'], divida_id))

            conn.commit()
            conn.close()

            set_msg(msg_form, f"Dívida '{nome_v}' cadastrada!" + (
                " Conta fixa criada automaticamente." if tipo_v == "parcelada" else ""
            ))
            tf_nome.value = tf_valor_total.value = tf_valor_parc.value = ""
            tf_total_parc.value = tf_dia_venc.value = tf_taxa.value = tf_data_inicio.value = ""
            carregar_tudo()
            carregar_dropdown()
        except Exception as ex:
            import traceback; traceback.print_exc()
            set_msg(msg_form, f"Erro: {ex}", False)

    # ──────────────────────────────────────────────────────────────────────────
    #  REGISTRAR PAGAMENTO AVULSO
    # ──────────────────────────────────────────────────────────────────────────
    def registrar_pagamento(e):
        if not dd_divida_pag.value:
            return set_msg(msg_pag, "Selecione a dívida.", False)
        valor_v = limpar_valor(tf_valor_pag.value)
        if valor_v <= 0:
            return set_msg(msg_pag, "Informe o valor pago.", False)
        data_v = parse_data(tf_data_pag.value)
        if not data_v:
            return set_msg(msg_pag, "Data inválida. Use DD/MM/AAAA.", False)

        obs_v  = tf_obs_pag.value.strip() or None
        div_id = int(dd_divida_pag.value)

        try:
            conn, cur = get_conn()
            cur.execute("SELECT subconta_id, nome FROM dividas WHERE id=%s", (div_id,))
            div_row = cur.fetchone()
            transacao_id = None

            # Gera transação no extrato se tiver subconta vinculada
            if div_row and div_row['subconta_id']:
                cur.execute("""
                    INSERT INTO transacoes
                        (usuario_id, subconta_id, tipo, valor, data, descricao)
                    VALUES (%s, %s, 'Despesa', %s, %s, %s)
                    RETURNING id
                """, (uid, div_row['subconta_id'], valor_v,
                      data_v.strftime("%d/%m/%Y"), obs_v or div_row['nome']))
                transacao_id = cur.fetchone()['id']

            cur.execute("""
                INSERT INTO divida_pagamentos
                    (divida_id, usuario_id, valor, data, observacao, transacao_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (div_id, uid, valor_v, data_v, obs_v, transacao_id))

            conn.commit()
            conn.close()

            set_msg(msg_pag, f"Pagamento de {fmt(valor_v)} registrado!")
            tf_valor_pag.value = tf_obs_pag.value = ""
            tf_data_pag.value  = hoje.strftime("%d/%m/%Y")
            dd_divida_pag.value = None
            carregar_tudo()
        except Exception as ex:
            import traceback; traceback.print_exc()
            set_msg(msg_pag, f"Erro: {ex}", False)

    # ──────────────────────────────────────────────────────────────────────────
    #  SEÇÃO VISUAL
    # ──────────────────────────────────────────────────────────────────────────
    def secao(titulo, subtitulo, conteudo):
        return ft.Container(
            content=ft.Column([
                ft.Text(titulo, weight="bold", size=14, color="#C62828"),
                ft.Text(subtitulo, size=11, color="grey") if subtitulo else ft.Container(height=0),
                ft.Divider(height=6),
                conteudo,
            ], spacing=6),
            padding=16,
            border=ft.border.all(1, "#E0E0E0"),
            border_radius=12, bgcolor=ft.colors.WHITE,
            shadow=ft.BoxShadow(blur_radius=4, color=ft.colors.BLACK12),
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  INIT
    # ──────────────────────────────────────────────────────────────────────────
    carregar_dropdown()
    carregar_tudo()

    return ft.View(
        route="/dividas",
        bgcolor="#F5F6FA",
        controls=[
            get_menu(page),
            ft.Divider(height=4, color="transparent"),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=20, vertical=8),
                expand=True,
                content=ft.Column([
                    ft.Text("💳 CONTROLE DE DÍVIDAS", size=22, weight="bold", color="#C62828"),
                    ft.Divider(height=8, color="transparent"),
                    resumo_row,
                    ft.Divider(height=8, color="transparent"),

                    # ── Cadastrar nova dívida ─────────────────────────────────
                    secao(
                        "➕ CADASTRAR NOVA DÍVIDA",
                        "Escolha como quer controlar essa dívida",
                        ft.Column([
                            # Seletor de tipo
                            ft.Row([
                                ft.Text("Tipo de controle:", size=12, color="grey"),
                                btn_parcelada,
                                btn_livre,
                            ], spacing=10),
                            aviso_parcelada,
                            aviso_livre,
                            ft.Row([tf_nome, tf_valor_total], spacing=10, wrap=True),
                            campos_parcelada,
                            ft.ElevatedButton(
                                "CADASTRAR DÍVIDA", icon=ft.icons.ADD_CIRCLE,
                                bgcolor="#1565C0", color=ft.colors.WHITE,
                                on_click=registrar_divida,
                            ),
                            msg_form,
                        ], spacing=10),
                    ),

                    ft.Divider(height=8, color="transparent"),

                    # ── Registrar pagamento avulso ────────────────────────────
                    secao(
                        "💰 REGISTRAR PAGAMENTO",
                        "Para dívidas parceladas, dê baixa diretamente em Contas Fixas. Aqui registre pagamentos avulsos.",
                        ft.Column([
                            ft.Row([dd_divida_pag, tf_valor_pag, tf_data_pag, tf_obs_pag,
                                    ft.ElevatedButton(
                                        "REGISTRAR PAGAMENTO", icon=ft.icons.SAVE,
                                        bgcolor="#C62828", color=ft.colors.WHITE,
                                        on_click=registrar_pagamento,
                                    )], spacing=10, wrap=True),
                            msg_pag,
                        ], spacing=10),
                    ),

                    ft.Divider(height=8, color="transparent"),

                    # ── Lista ─────────────────────────────────────────────────
                    secao(
                        "📋 DÍVIDAS REGISTRADAS",
                        "Clique em ▼ para ver os pagamentos detalhados",
                        lista_dividas,
                    ),
                    ft.Divider(height=16, color="transparent"),
                ], scroll=ft.ScrollMode.ALWAYS, expand=True),
            ),
        ],
    )