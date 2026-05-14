import flet as ft
from datetime import datetime
from calendar import monthrange
from collections import defaultdict
from menu import get_menu
from database import db_session
from utils import limpar_valor, formatar_moeda_input


def dashboard_view(page):
    hoje = datetime.now()
    state = {"mes": hoje.month, "ano": hoje.year}
    uid = page.session.get("user_id")

    def get_mes_str():
        return f"{state['mes']:02d}/{state['ano']}"

    def get_meses_opcoes():
        opcoes = []
        m, a = hoje.month, hoje.year
        for _ in range(12):
            opcoes.append(ft.dropdown.Option(f"{m:02d}/{a}"))
            m -= 1
            if m == 0:
                m = 12
                a -= 1
        return opcoes

    def fmt(v):
        return f"R$ {v:_.2f}".replace(".", ",").replace("_", ".")

    def fmt_pct(v):
        return f"{v:.1f}%"

    def mes_anterior_str(mes_str):
        m = int(mes_str.split("/")[0])
        a = int(mes_str.split("/")[1])
        m -= 1
        if m == 0:
            m = 12
            a -= 1
        return f"{m:02d}/{a}"

    CORES = [
        "#1565C0", "#C62828", "#2E7D32", "#F57F17", "#6A1B9A",
        "#00838F", "#4E342E", "#37474F", "#AD1457", "#558B2F",
        "#EF6C00", "#0277BD", "#283593", "#00695C", "#4527A0",
    ]

    cards_topo       = ft.Row(spacing=12, wrap=True)
    bancos_container = ft.Row(spacing=12, wrap=True)
    grafico_col      = ft.Column(spacing=10)
    pizza_row        = ft.Row(spacing=16, vertical_alignment=ft.CrossAxisAlignment.START)
    detalhes_col     = ft.Column(scroll=ft.ScrollMode.AUTO, height=320, spacing=6)
    orcamento_col    = ft.Column(spacing=8)
    comparativo_col  = ft.Column(spacing=6)
    metas_container  = ft.Column(spacing=6)

    meta_rec_field = ft.TextField(label="Meta Receita",   width=180, on_blur=formatar_moeda_input)
    meta_des_field = ft.TextField(label="Meta Despesa",   width=180, on_blur=formatar_moeda_input)
    meta_res_field = ft.TextField(label="Meta Resultado", width=180, on_blur=formatar_moeda_input)
    msg_meta = ft.Text("", size=12, color=ft.colors.GREEN_700)

    def salvar_meta(e):
        try:
            mes_str = get_mes_str()
            mr   = limpar_valor(meta_rec_field.value)
            md   = limpar_valor(meta_des_field.value)
            mres = limpar_valor(meta_res_field.value)
            with db_session() as cur:
                cur.execute("SELECT id FROM metas WHERE mes=%s AND usuario_id=%s", (mes_str, uid))
                if cur.fetchone():
                    cur.execute("UPDATE metas SET meta_receita=%s, meta_despesa=%s, meta_resultado=%s WHERE mes=%s AND usuario_id=%s", (mr, md, mres, mes_str, uid))
                else:
                    cur.execute("INSERT INTO metas (mes, meta_receita, meta_despesa, meta_resultado, usuario_id) VALUES (%s,%s,%s,%s,%s)", (mes_str, mr, md, mres, uid))
            msg_meta.value = "✅ Metas salvas!"
            carregar(mes_str)
            page.update()
        except Exception as ex:
            print(f"[dashboard] salvar_meta erro: {ex}")
            msg_meta.value = "❌ Erro ao salvar metas."
            page.update()

    def buscar_meta_mes_anterior(mes_str):
        try:
            with db_session() as cur:
                cur.execute("SELECT * FROM metas WHERE mes=%s AND usuario_id=%s", (mes_anterior_str(mes_str), uid))
                return cur.fetchone()
        except:
            return None

    def calcular_saldo_acumulado(mes_str):
        """Saldo acumulado geral até o fim do mês selecionado."""
        try:
            with db_session() as cur:
                cur.execute("SELECT COALESCE(SUM(saldo_inicial), 0) as total FROM bancos WHERE usuario_id=%s", (uid,))
                saldo_inicial = float(cur.fetchone()['total'] or 0)
                m_sel, a_sel = int(mes_str.split("/")[0]), int(mes_str.split("/")[1])
                # Todas transações até o fim do mês selecionado
                cur.execute("""
                    SELECT tipo, SUM(valor) as total FROM transacoes
                    WHERE usuario_id=%s AND (
                        CAST(SPLIT_PART(data,'/',3) AS INTEGER) < %s OR
                        (CAST(SPLIT_PART(data,'/',3) AS INTEGER) = %s AND CAST(SPLIT_PART(data,'/',2) AS INTEGER) <= %s)
                    ) GROUP BY tipo
                """, (uid, a_sel, a_sel, m_sel))
                saldo_mov = 0.0
                for r in cur.fetchall():
                    saldo_mov += float(r['total'] or 0) if r['tipo'] == "Receita" else -float(r['total'] or 0)
                return saldo_inicial + saldo_mov
        except Exception as ex:
            print(f"[dashboard] saldo_acumulado erro: {ex}")
            return 0.0

    def calcular_saldo_banco(banco_id, saldo_inicial, mes_str):
        """Saldo real de um banco específico até o fim do mês selecionado."""
        try:
            m_sel, a_sel = int(mes_str.split("/")[0]), int(mes_str.split("/")[1])
            with db_session() as cur:
                # Receitas vinculadas ao banco até o fim do mês
                cur.execute("""
                    SELECT COALESCE(SUM(valor), 0) as total FROM transacoes
                    WHERE usuario_id=%s AND banco_id=%s AND tipo='Receita'
                    AND (
                        CAST(SPLIT_PART(data,'/',3) AS INTEGER) < %s OR
                        (CAST(SPLIT_PART(data,'/',3) AS INTEGER) = %s AND CAST(SPLIT_PART(data,'/',2) AS INTEGER) <= %s)
                    )
                """, (uid, banco_id, a_sel, a_sel, m_sel))
                receitas = float(cur.fetchone()['total'] or 0)

                # Despesas vinculadas ao banco até o fim do mês
                cur.execute("""
                    SELECT COALESCE(SUM(valor), 0) as total FROM transacoes
                    WHERE usuario_id=%s AND banco_id=%s AND tipo='Despesa'
                    AND (
                        CAST(SPLIT_PART(data,'/',3) AS INTEGER) < %s OR
                        (CAST(SPLIT_PART(data,'/',3) AS INTEGER) = %s AND CAST(SPLIT_PART(data,'/',2) AS INTEGER) <= %s)
                    )
                """, (uid, banco_id, a_sel, a_sel, m_sel))
                despesas = float(cur.fetchone()['total'] or 0)

            return saldo_inicial + receitas - despesas
        except Exception as ex:
            print(f"[dashboard] calcular_saldo_banco erro: {ex}")
            return saldo_inicial

    def carregar(mes_str):
        try:
            with db_session() as cur:
                cur.execute("SELECT COALESCE(SUM(valor),0) as total FROM transacoes WHERE usuario_id=%s AND tipo='Receita' AND data LIKE %s", (uid, f"%%/{mes_str}"))
                ent = float(cur.fetchone()['total'] or 0)
                cur.execute("SELECT COALESCE(SUM(valor),0) as total FROM transacoes WHERE usuario_id=%s AND tipo='Despesa' AND data LIKE %s", (uid, f"%%/{mes_str}"))
                sai = float(cur.fetchone()['total'] or 0)
                saldo_mes       = ent - sai
                saldo_acumulado = calcular_saldo_acumulado(mes_str)

                # ✅ Busca bancos com id para calcular saldo real
                cur.execute("SELECT id, nome_banco, saldo_inicial, agencia, numero_conta FROM bancos WHERE usuario_id=%s ORDER BY nome_banco", (uid,))
                bancos_rows = cur.fetchall()

                cur.execute("SELECT * FROM metas WHERE mes=%s AND usuario_id=%s", (mes_str, uid))
                meta_row = cur.fetchone()
                if not meta_row:
                    meta_row = buscar_meta_mes_anterior(mes_str)
                    msg_meta.value = "💡 Meta copiada do mês anterior." if meta_row else ""
                else:
                    msg_meta.value = ""

                meta_rec = float(meta_row['meta_receita']  or 0) if meta_row else 0.0
                meta_des = float(meta_row['meta_despesa']  or 0) if meta_row else 0.0
                meta_res = float(meta_row['meta_resultado'] or 0) if meta_row else 0.0
                meta_rec_field.value = f"{meta_rec:_.2f}".replace(".",",").replace("_",".") if meta_rec else ""
                meta_des_field.value = f"{meta_des:_.2f}".replace(".",",").replace("_",".") if meta_des else ""
                meta_res_field.value = f"{meta_res:_.2f}".replace(".",",").replace("_",".") if meta_res else ""

                cur.execute("""
                    SELECT CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.nome ELSE s.nome END as nome,
                           SUM(t.valor) as total
                    FROM transacoes t JOIN subcontas s ON t.subconta_id=s.id
                    LEFT JOIN subcontas sr ON t.categoria_real_id=sr.id
                    WHERE t.usuario_id=%s AND t.tipo='Despesa' AND t.data LIKE %s
                    GROUP BY 1 ORDER BY 2 DESC
                """, (uid, f"%%/{mes_str}"))
                gastos = cur.fetchall()

                cur.execute("SELECT COALESCE(SUM(t.valor),0) as total FROM transacoes t JOIN subcontas s ON t.subconta_id=s.id WHERE t.usuario_id=%s AND t.tipo='Despesa' AND t.data LIKE %s AND (s.nome ILIKE '%%CARTAO%%' OR s.nome ILIKE '%%CARTÃO%%')", (uid, f"%%/{mes_str}"))
                total_cartao = float(cur.fetchone()['total'] or 0)

                cur.execute("SELECT COUNT(*) as total FROM subcontas s WHERE s.fixa=1 AND s.usuario_id=%s AND s.id NOT IN (SELECT subconta_id FROM transacoes WHERE data LIKE %s AND usuario_id=%s)", (uid, f"%%/{mes_str}", uid))
                fixas_pendentes = int(cur.fetchone()['total'] or 0)

                cur.execute("""
                    SELECT CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.nome ELSE s.nome END as nome,
                           MAX(CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.orcamento ELSE s.orcamento END) as orcamento,
                           SUM(t.valor) as total
                    FROM transacoes t JOIN subcontas s ON t.subconta_id=s.id
                    LEFT JOIN subcontas sr ON t.categoria_real_id=sr.id
                    WHERE t.usuario_id=%s AND t.tipo='Despesa' AND t.data LIKE %s GROUP BY 1
                    HAVING MAX(CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.orcamento ELSE s.orcamento END) > 0
                """, (uid, f"%%/{mes_str}"))
                orcamentos = cur.fetchall()

                cur.execute("SELECT SPLIT_PART(data,'/',2)||'/'||SPLIT_PART(data,'/',3) as m, tipo, SUM(valor) as total FROM transacoes WHERE usuario_id=%s GROUP BY 1,2 ORDER BY 1", (uid,))
                hist_rows = cur.fetchall()

                cur.execute("""
                    SELECT SPLIT_PART(t.data,'/',2)||'/'||SPLIT_PART(t.data,'/',3) as mes,
                           CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.nome ELSE s.nome END as nome,
                           SUM(t.valor) as total
                    FROM transacoes t JOIN subcontas s ON t.subconta_id=s.id
                    LEFT JOIN subcontas sr ON t.categoria_real_id=sr.id
                    WHERE t.usuario_id=%s AND t.tipo='Despesa' GROUP BY 1,2 ORDER BY 1
                """, (uid,))
                comp_rows = cur.fetchall()

        except Exception as ex:
            import traceback
            print(f"[dashboard] carregar erro: {ex}")
            traceback.print_exc()
            return

        pct_rec = (ent / meta_rec * 100) if meta_rec > 0 else 0
        pct_des = (sai / meta_des * 100) if meta_des > 0 else 0
        pct_res = (saldo_mes / meta_res * 100) if meta_res > 0 else 0
        m, a = state["mes"], state["ano"]
        dias_restantes = max(0, monthrange(a, m)[1] - hoje.day) if (m == hoje.month and a == hoje.year) else 0
        pct_cartao = (total_cartao / sai * 100) if sai > 0 else 0

        # ── CARDS ──────────────────────────────────────────────────────────
        def card_meta(titulo, valor, meta, pct, cor_bg, icone):
            return ft.Container(
                width=230, height=150, padding=14, bgcolor=cor_bg, border_radius=14,
                shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26),
                content=ft.Column([
                    ft.Row([ft.Text(titulo, size=11, weight="bold", color="white"),
                            ft.Icon(icone, size=16, color="white")], alignment="spaceBetween"),
                    ft.Text(fmt(valor), size=20, weight="bold", color="white"),
                    ft.Row([ft.Text("Meta:", size=10, color="white70"),
                            ft.Text(fmt(meta) if meta > 0 else "—", size=10, color="white")], spacing=4),
                    ft.Container(
                        content=ft.Text(fmt_pct(pct) if meta > 0 else "Sem meta", size=11, weight="bold",
                                        color="#1B5E20" if pct <= 100 else "#B71C1C"),
                        bgcolor="white", border_radius=6, padding=ft.padding.symmetric(horizontal=8, vertical=2)),
                    ft.ProgressBar(value=min(pct/100,1.0) if meta > 0 else 0, color="white", bgcolor="white24", height=5),
                ], spacing=5))

        cards_topo.controls = [
            card_meta("RECEITAS", ent, meta_rec, pct_rec, "#2E7D32", ft.icons.ARROW_UPWARD),
            card_meta("DESPESAS", sai, meta_des, pct_des, "#C62828", ft.icons.ARROW_DOWNWARD),
            ft.Container(
                width=230, height=150, padding=14,
                bgcolor="#1565C0" if saldo_mes >= 0 else "#B71C1C", border_radius=14,
                shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26),
                content=ft.Column([
                    ft.Row([ft.Text("RESULTADO", size=11, weight="bold", color="white"),
                            ft.Icon(ft.icons.ACCOUNT_BALANCE_WALLET, size=16, color="white")], alignment="spaceBetween"),
                    ft.Text(fmt(saldo_mes), size=20, weight="bold", color="white"),
                    ft.Row([ft.Text("Meta:", size=10, color="white70"),
                            ft.Text(fmt(meta_res) if meta_res > 0 else "—", size=10, color="white")], spacing=4),
                    ft.Container(
                        content=ft.Text(fmt_pct(pct_res) if meta_res > 0 else "Sem meta", size=11, weight="bold",
                                        color="#1B5E20" if pct_res >= 100 else "#B71C1C"),
                        bgcolor="white", border_radius=6, padding=ft.padding.symmetric(horizontal=8, vertical=2)),
                    ft.ProgressBar(value=min(pct_res/100,1.0) if meta_res > 0 else 0, color="white", bgcolor="white24", height=5),
                ], spacing=5)),
            ft.Container(
                width=230, height=150, padding=14, bgcolor="#4527A0", border_radius=14,
                shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26),
                content=ft.Column([
                    ft.Row([ft.Text("ACUMULADO", size=11, weight="bold", color="white"),
                            ft.Icon(ft.icons.SAVINGS, size=16, color="white")], alignment="spaceBetween"),
                    ft.Text(fmt(saldo_acumulado), size=20, weight="bold", color="white"),
                    ft.Text("saldo total acumulado", size=10, color="white70"),
                ], spacing=5)),
            ft.Container(
                width=230, height=150, padding=14, bgcolor="#F57F17", border_radius=14,
                shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26),
                content=ft.Column([
                    ft.Row([ft.Text("💳 CARTÃO", size=11, weight="bold", color="white"),
                            ft.Icon(ft.icons.CREDIT_CARD, size=16, color="white")], alignment="spaceBetween"),
                    ft.Text(fmt(total_cartao), size=20, weight="bold", color="white"),
                    ft.Text("total no mês", size=10, color="white70"),
                    ft.ProgressBar(value=min(pct_cartao/100,1.0), color="white", bgcolor="white24", height=5),
                    ft.Text(f"{pct_cartao:.1f}% das despesas", size=10, color="white70"),
                ], spacing=4)),
            ft.Container(
                width=230, height=150, padding=14, bgcolor="#00838F", border_radius=14,
                shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26),
                content=ft.Column([
                    ft.Row([ft.Text("📅 DIAS REST.", size=11, weight="bold", color="white"),
                            ft.Icon(ft.icons.CALENDAR_TODAY, size=16, color="white")], alignment="spaceBetween"),
                    ft.Text(str(dias_restantes), size=36, weight="bold", color="white"),
                    ft.Text("dias no mês", size=10, color="white70"),
                    ft.Text(f"⚠ {fixas_pendentes} fixas pendentes", size=10, color="#FFD54F") if fixas_pendentes > 0 else ft.Container(),
                ], spacing=4)),
        ]

        # ── BANCOS — saldo real até o mês selecionado ──────────────────────
        bancos_cards = []
        for b in bancos_rows:
            saldo_real = calcular_saldo_banco(b['id'], float(b['saldo_inicial'] or 0), mes_str)
            variacao   = saldo_real - float(b['saldo_inicial'] or 0)
            cor_var    = "#A5D6A7" if variacao >= 0 else "#EF9A9A"
            sinal      = "▲" if variacao >= 0 else "▼"
            bancos_cards.append(
                ft.Container(
                    width=240, padding=14, bgcolor="#37474F", border_radius=12,
                    shadow=ft.BoxShadow(blur_radius=6, color=ft.colors.BLACK26),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.icons.ACCOUNT_BALANCE, color="white", size=18),
                            ft.Text(b['nome_banco'], size=12, weight="bold", color="white", expand=True),
                        ], spacing=6),
                        ft.Text(fmt(saldo_real), size=20, weight="bold", color="white"),
                        ft.Row([
                            ft.Text("Inicial:", size=10, color="white70"),
                            ft.Text(fmt(b['saldo_inicial'] or 0), size=10, color="white70"),
                            ft.Text(f"{sinal} {fmt(abs(variacao))}", size=10, color=cor_var, weight="bold"),
                        ], spacing=6),
                        ft.Text(
                            f"Ag: {b['agencia'] or '—'} | Cta: {b['numero_conta'] or '—'}",
                            size=10, color="white70"),
                    ], spacing=4)
                )
            )
        bancos_container.controls = bancos_cards

        # ── GRÁFICO RECEITAS VS DESPESAS ───────────────────────────────────
        hist = defaultdict(lambda: {"Receita": 0.0, "Despesa": 0.0})
        for r in hist_rows:
            hist[r['m']][r['tipo']] = float(r['total'] or 0)
        meses_hist = sorted(hist.keys())[-6:]
        max_val = max([max(hist[m]['Receita'], hist[m]['Despesa']) for m in meses_hist], default=1)
        BAR_MAX = 500

        grafico_col.controls = [
            ft.Row([
                ft.Container(width=12, height=12, bgcolor="#2E7D32", border_radius=3),
                ft.Text("Receita", size=11, color="#2E7D32", weight="bold"),
                ft.Container(width=12, height=12, bgcolor="#C62828", border_radius=3),
                ft.Text("Despesa", size=11, color="#C62828", weight="bold"),
            ], spacing=8),
        ] + [
            ft.Column([
                ft.Text(m, size=11, weight="bold", color="#555"),
                ft.Row([
                    ft.Container(
                        height=22, width=max(8, int(hist[m]['Receita'] / max_val * BAR_MAX)),
                        bgcolor="#2E7D32", border_radius=4, padding=ft.padding.only(left=6),
                        content=ft.Text(fmt(hist[m]['Receita']) if hist[m]['Receita'] > 0 else "", size=10, color="white")),
                ]),
                ft.Row([
                    ft.Container(
                        height=22, width=max(8, int(hist[m]['Despesa'] / max_val * BAR_MAX)),
                        bgcolor="#C62828", border_radius=4, padding=ft.padding.only(left=6),
                        content=ft.Text(fmt(hist[m]['Despesa']) if hist[m]['Despesa'] > 0 else "", size=10, color="white")),
                ]),
            ], spacing=3) for m in meses_hist
        ]

        # ── GASTOS POR CONTA ───────────────────────────────────────────────
        detalhes_col.controls = [
            ft.Column([
                ft.Row([
                    ft.Text(g['nome'], expand=True, size=12),
                    ft.Text(fmt(g['total']), weight="bold", color="#C62828", size=12),
                    ft.Text(f"{g['total']/sai*100:.1f}%" if sai > 0 else "0%", size=10, color="grey", width=42),
                ]),
                ft.ProgressBar(value=g['total']/sai if sai > 0 else 0, color="#C62828", bgcolor="#FFEBEE", height=6, border_radius=3),
            ], spacing=3) for g in gastos
        ] if gastos else [ft.Text("Sem despesas no período.", color="grey", italic=True)]

        # ── PIZZA + LEGENDA ────────────────────────────────────────────────
        if gastos and sai > 0:
            sections = [
                ft.PieChartSection(
                    value=float(g['total']),
                    title=f"{g['total']/sai*100:.0f}%" if g['total']/sai > 0.05 else "",
                    title_style=ft.TextStyle(size=12, color="white", weight="bold"),
                    color=CORES[i % len(CORES)],
                    radius=110,
                ) for i, g in enumerate(gastos)
            ]
            legenda = ft.Column(
                spacing=6, scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Row([
                        ft.Container(width=14, height=14, bgcolor=CORES[i % len(CORES)], border_radius=3),
                        ft.Text(g['nome'], size=11, expand=True),
                        ft.Text(fmt(g['total']), size=11, color="#C62828", weight="bold"),
                        ft.Text(f"{g['total']/sai*100:.1f}%", size=10, color="grey", width=40),
                    ], spacing=6) for i, g in enumerate(gastos)
                ]
            )
            pizza_row.controls = [
                ft.PieChart(sections=sections, height=260, center_space_radius=0, expand=False),
                ft.VerticalDivider(width=1, color="#E0E0E0"),
                ft.Container(content=legenda, expand=True),
            ]
        else:
            pizza_row.controls = [ft.Text("Sem despesas no período.", color="grey", italic=True)]

        # ── ORÇAMENTO MENSAL ───────────────────────────────────────────────
        def badge_orc(pct):
            if pct >= 100:  return ("🔴", "#FFEBEE", "#C62828")
            elif pct >= 80: return ("🟡", "#FFF8E1", "#F57F17")
            else:           return ("✅", "#E8F5E9", "#2E7D32")

        if orcamentos:
            orcamento_col.controls = [
                ft.Row([
                    ft.Container(width=10, height=10, bgcolor="#2E7D32", border_radius=5),
                    ft.Text("ok", size=10, color="#2E7D32"),
                    ft.Container(width=10, height=10, bgcolor="#F57F17", border_radius=5),
                    ft.Text("acima de 80%", size=10, color="#F57F17"),
                    ft.Container(width=10, height=10, bgcolor="#C62828", border_radius=5),
                    ft.Text("ultrapassado", size=10, color="#C62828"),
                ], spacing=6),
            ] + [
                ft.Container(
                    border_radius=8, padding=10,
                    bgcolor=badge_orc(o['total']/o['orcamento']*100 if o['orcamento'] > 0 else 0)[1],
                    content=ft.Column([
                        ft.Row([
                            ft.Text(badge_orc(o['total']/o['orcamento']*100 if o['orcamento'] > 0 else 0)[0] + " " + o['nome'],
                                    expand=True, size=12, weight="bold",
                                    color=badge_orc(o['total']/o['orcamento']*100 if o['orcamento'] > 0 else 0)[2]),
                            ft.Text(f"{fmt(o['total'])}/{fmt(o['orcamento'])}", size=11,
                                    color=badge_orc(o['total']/o['orcamento']*100 if o['orcamento'] > 0 else 0)[2]),
                            ft.Text(f"{o['total']/o['orcamento']*100:.1f}%" if o['orcamento'] > 0 else "0%",
                                    size=11, weight="bold",
                                    color=badge_orc(o['total']/o['orcamento']*100 if o['orcamento'] > 0 else 0)[2]),
                        ]),
                        ft.ProgressBar(
                            value=min(o['total']/o['orcamento'],1.0) if o['orcamento'] > 0 else 0,
                            color=badge_orc(o['total']/o['orcamento']*100 if o['orcamento'] > 0 else 0)[2],
                            bgcolor="white", height=8, border_radius=4),
                        ft.Text(
                            ("Ultrapassado " if o['total'] > o['orcamento'] else "Restam ") + fmt(abs(o['orcamento'] - o['total'])),
                            size=10, color=badge_orc(o['total']/o['orcamento']*100 if o['orcamento'] > 0 else 0)[2]),
                    ], spacing=4)) for o in orcamentos
            ]
        else:
            orcamento_col.controls = [ft.Text("Nenhum orçamento definido.", color="grey", italic=True, size=12)]

        # ── COMPARATIVO MENSAL ─────────────────────────────────────────────
        comp_dados = defaultdict(dict)
        meses_c = set()
        for r in comp_rows:
            comp_dados[r['nome']][r['mes']] = float(r['total'] or 0)
            meses_c.add(r['mes'])
        meses_ord = sorted(list(meses_c))[-3:]

        def cell_comp(nome, m):
            val = comp_dados[nome].get(m, None)
            if val is None:
                return ft.DataCell(ft.Text("—", color="grey", size=11))
            meses_list = sorted(comp_dados[nome].keys())
            idx = meses_list.index(m) if m in meses_list else -1
            if idx > 0:
                prev = comp_dados[nome].get(meses_list[idx-1], None)
                if prev is not None and prev > 0:
                    cor = "#C62828" if val > prev else "#2E7D32"
                    return ft.DataCell(ft.Text(fmt(val), color=cor, size=11, weight="bold"))
            return ft.DataCell(ft.Text(fmt(val), color="#1565C0", size=11))

        if meses_ord:
            cols_c = [ft.DataColumn(ft.Text("Conta", weight="bold", size=12))] + [
                ft.DataColumn(ft.Text(m, weight="bold", size=12)) for m in meses_ord]
            rows_c = [
                ft.DataRow(cells=[ft.DataCell(ft.Text(n, size=11))] + [cell_comp(n, m) for m in meses_ord])
                for n in sorted(comp_dados.keys())
            ]
            comparativo_col.controls = [
                ft.Row([
                    ft.Container(width=10, height=10, bgcolor="#2E7D32", border_radius=5),
                    ft.Text("diminuiu", size=10, color="#2E7D32"),
                    ft.Container(width=10, height=10, bgcolor="#C62828", border_radius=5),
                    ft.Text("aumentou em relação ao mês anterior", size=10, color="#C62828"),
                ], spacing=6),
                ft.DataTable(
                    columns=cols_c, rows=rows_c,
                    border=ft.border.all(1, "#E0E0E0"),
                    border_radius=8,
                    horizontal_lines=ft.border.BorderSide(1, "#F0F0F0"),
                ),
            ]
        else:
            comparativo_col.controls = [ft.Text("Sem dados comparativos.", color="grey", italic=True)]

        # ── METAS ──────────────────────────────────────────────────────────
        metas_container.controls = [
            ft.Row([meta_rec_field, meta_des_field, meta_res_field,
                    ft.ElevatedButton("SALVAR METAS", bgcolor="#1565C0", color="white", on_click=salvar_meta)],
                   spacing=10, wrap=True),
            msg_meta,
        ]
        page.update()

    dd_mes = ft.Dropdown(
        label="Mês", width=160, value=get_mes_str(), options=get_meses_opcoes(),
        on_change=lambda e: (
            state.update({"mes": int(e.control.value.split("/")[0]), "ano": int(e.control.value.split("/")[1])}),
            carregar(e.control.value)
        )
    )
    carregar(get_mes_str())

    def secao(titulo, subtitulo, conteudo, cor_titulo="#1565C0"):
        return ft.Container(
            content=ft.Column([
                ft.Text(titulo, weight="bold", size=15, color=cor_titulo),
                ft.Text(subtitulo, size=11, color="grey") if subtitulo else ft.Container(),
                ft.Divider(height=6),
                conteudo,
            ], spacing=6),
            padding=16, border=ft.border.all(1, "#E0E0E0"), border_radius=12,
            bgcolor="white", shadow=ft.BoxShadow(blur_radius=4, color=ft.colors.BLACK12)
        )

    return ft.View(route="/", bgcolor="#F5F6FA", controls=[
        get_menu(page),
        ft.Container(padding=ft.padding.symmetric(horizontal=20, vertical=8), expand=True, content=ft.Column([
            ft.Row([
                ft.Text("DASHBOARD FINANCEIRO", size=22, weight="bold", color="#1565C0"),
                ft.Row([ft.Text("Período:", size=12, color="grey"), dd_mes], spacing=8),
            ]),
            ft.Divider(height=4, color="transparent"),
            cards_topo,
            ft.Divider(height=4, color="transparent"),
            bancos_container,
            ft.Divider(height=4, color="transparent"),
            ft.Row([
                ft.Container(content=secao("📊 RECEITAS VS DESPESAS", "Histórico dos últimos 6 meses", grafico_col), expand=3),
                ft.Container(content=secao("💸 GASTOS POR CONTA", "Distribuição do mês atual", detalhes_col), expand=2),
            ], spacing=12),
            ft.Divider(height=4, color="transparent"),
            ft.Row([
                ft.Container(content=secao("🍕 DESPESAS POR CATEGORIA", "Distribuição percentual", pizza_row), expand=1),
                ft.Container(content=secao("🎯 ORÇAMENTO MENSAL", None, orcamento_col), expand=1),
            ], spacing=12),
            ft.Divider(height=4, color="transparent"),
            secao("🎯 DEFINIR METAS DO MÊS", "Configure as metas de receita, despesa e resultado", metas_container),
            ft.Divider(height=4, color="transparent"),
            secao("📅 COMPARATIVO MENSAL", None, comparativo_col),
        ], scroll=ft.ScrollMode.ALWAYS, expand=True))
    ])