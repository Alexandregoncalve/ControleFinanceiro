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

    def mes_anterior_str(mes_str: str) -> str:
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

    # Recipientes da Interface
    cards_topo = ft.Row(spacing=12, wrap=True)
    bancos_container = ft.Row(spacing=12, wrap=True)
    grafico_barras_col = ft.Column(spacing=8)
    pizza_container = ft.Column(spacing=6)
    detalhes_col = ft.Column(scroll=ft.ScrollMode.AUTO, height=300, spacing=4)
    orcamento_container = ft.Column(spacing=6)
    comparativo_container = ft.Column(spacing=6)
    metas_container = ft.Column(spacing=6)

    meta_rec_field = ft.TextField(label="Meta Receita", width=180, on_blur=formatar_moeda_input)
    meta_des_field = ft.TextField(label="Meta Despesa", width=180, on_blur=formatar_moeda_input)
    meta_res_field = ft.TextField(label="Meta Resultado", width=180, on_blur=formatar_moeda_input)
    msg_meta = ft.Text("", size=12, color=ft.colors.GREEN_700)

    def salvar_meta(e):
        try:
            mes_str = get_mes_str()
            mr = limpar_valor(meta_rec_field.value)
            md = limpar_valor(meta_des_field.value)
            mres = limpar_valor(meta_res_field.value)
            with db_session() as cur:
                cur.execute("SELECT id FROM metas WHERE mes=%s AND usuario_id=%s", (mes_str, uid))
                row = cur.fetchone()
                if row:
                    cur.execute(
                        "UPDATE metas SET meta_receita=%s, meta_despesa=%s, meta_resultado=%s WHERE mes=%s AND usuario_id=%s",
                        (mr, md, mres, mes_str, uid)
                    )
                else:
                    cur.execute(
                        "INSERT INTO metas (mes, meta_receita, meta_despesa, meta_resultado, usuario_id) VALUES (%s,%s,%s,%s,%s)",
                        (mes_str, mr, md, mres, uid)
                    )
            msg_meta.value = "✅ Metas salvas!"
            carregar(mes_str)
            page.update()
        except:
            msg_meta.value = "❌ Erro ao salvar metas."
            page.update()

    def buscar_meta_mes_anterior(mes_str: str):
        try:
            mes_ant = mes_anterior_str(mes_str)
            with db_session() as cur:
                cur.execute("SELECT * FROM metas WHERE mes=%s AND usuario_id=%s", (mes_ant, uid))
                return cur.fetchone()
        except:
            return None

    def calcular_saldo_acumulado(mes_str: str) -> float:
        try:
            with db_session() as cur:
                cur.execute("SELECT COALESCE(SUM(saldo_inicial), 0) FROM bancos WHERE usuario_id=%s", (uid,))
                saldo_inicial = float(cur.fetchone()[0] or 0)
                m_sel, a_sel = int(mes_str.split("/")[0]), int(mes_str.split("/")[1])
                cur.execute("""
                    SELECT tipo, SUM(valor) FROM transacoes
                    WHERE usuario_id=%s AND (
                        CAST(SPLIT_PART(data, '/', 3) AS INTEGER) < %s OR
                        (CAST(SPLIT_PART(data, '/', 3) AS INTEGER) = %s AND CAST(SPLIT_PART(data, '/', 2) AS INTEGER) < %s)
                    ) GROUP BY tipo
                """, (uid, a_sel, a_sel, m_sel))
                rows = cur.fetchall()
                saldo_anterior = 0.0
                for r in rows:
                    if r[0] == "Receita":
                        saldo_anterior += float(r[1] or 0)
                    else:
                        saldo_anterior -= float(r[1] or 0)
                return saldo_inicial + saldo_anterior
        except:
            return 0.0

    def carregar(mes_str):
        try:
            with db_session() as cur:
                cur.execute(
                    "SELECT COALESCE(SUM(valor),0) FROM transacoes WHERE usuario_id=%s AND tipo='Receita' AND data LIKE %s",
                    (uid, f"%{mes_str}",))
                ent = float(cur.fetchone()[0] or 0)
                cur.execute(
                    "SELECT COALESCE(SUM(valor),0) FROM transacoes WHERE usuario_id=%s AND tipo='Despesa' AND data LIKE %s",
                    (uid, f"%{mes_str}",))
                sai = float(cur.fetchone()[0] or 0)

                saldo_anterior = calcular_saldo_acumulado(mes_str)
                saldo_mes = ent - sai
                saldo_acumulado = saldo_anterior + saldo_mes

                cur.execute("SELECT nome_banco, saldo_inicial FROM bancos WHERE usuario_id=%s ORDER BY nome_banco",
                            (uid,))
                bancos_rows = cur.fetchall()

                cur.execute("SELECT * FROM metas WHERE mes=%s AND usuario_id=%s", (mes_str, uid))
                meta_row = cur.fetchone()
                if not meta_row:
                    meta_row = buscar_meta_mes_anterior(mes_str)
                    msg_meta.value = "💡 Meta copiada." if meta_row else ""
                else:
                    msg_meta.value = ""

                meta_rec = float(meta_row[2] or 0) if meta_row else 0.0
                meta_des = float(meta_row[3] or 0) if meta_row else 0.0
                meta_res = float(meta_row[4] or 0) if meta_row else 0.0
                meta_rec_field.value = f"{meta_rec:_.2f}".replace(".", ",").replace("_", ".") if meta_rec else ""
                meta_des_field.value = f"{meta_des:_.2f}".replace(".", ",").replace("_", ".") if meta_des else ""
                meta_res_field.value = f"{meta_res:_.2f}".replace(".", ",").replace("_", ".") if meta_res else ""

                cur.execute("""
                    SELECT CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.nome ELSE s.nome END, SUM(t.valor)
                    FROM transacoes t JOIN subcontas s ON t.subconta_id = s.id LEFT JOIN subcontas sr ON t.categoria_real_id = sr.id
                    WHERE t.usuario_id=%s AND t.tipo='Despesa' AND t.data LIKE %s GROUP BY 1 ORDER BY 2 DESC
                """, (uid, f"%{mes_str}",))
                gastos = cur.fetchall()

                cur.execute(
                    "SELECT COALESCE(SUM(t.valor),0) FROM transacoes t JOIN subcontas s ON t.subconta_id = s.id WHERE t.usuario_id=%s AND t.tipo='Despesa' AND t.data LIKE %s AND (s.nome ILIKE '%%CARTAO%%' OR s.nome ILIKE '%%CARTÃO%%')",
                    (uid, f"%{mes_str}"))
                total_cartao = float(cur.fetchone()[0] or 0)

                cur.execute(
                    "SELECT COUNT(*) FROM subcontas s WHERE s.fixa=1 AND s.usuario_id=%s AND s.id NOT IN (SELECT subconta_id FROM transacoes WHERE data LIKE %s AND usuario_id=%s)",
                    (uid, f"%{mes_str}", uid))
                fixas_pendentes = int(cur.fetchone()[0] or 0)

                cur.execute("""
                    SELECT CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.nome ELSE s.nome END, 
                           MAX(CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.orcamento ELSE s.orcamento END), SUM(t.valor)
                    FROM transacoes t JOIN subcontas s ON t.subconta_id = s.id LEFT JOIN subcontas sr ON t.categoria_real_id = sr.id
                    WHERE t.usuario_id=%s AND t.tipo='Despesa' AND t.data LIKE %s GROUP BY 1 HAVING MAX(2) > 0
                """, (uid, f"%{mes_str}",))
                orcamentos = cur.fetchall()

                cur.execute(
                    "SELECT SPLIT_PART(data, '/', 2) || '/' || SPLIT_PART(data, '/', 3) as m, tipo, SUM(valor) FROM transacoes WHERE usuario_id=%s GROUP BY 1, 2 ORDER BY 1 DESC LIMIT 24",
                    (uid,))
                hist_rows = cur.fetchall()

                cur.execute("""
                    SELECT SPLIT_PART(t.data, '/', 2) || '/' || SPLIT_PART(t.data, '/', 3), 
                           CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.nome ELSE s.nome END, SUM(t.valor)
                    FROM transacoes t JOIN subcontas s ON t.subconta_id = s.id LEFT JOIN subcontas sr ON t.categoria_real_id = sr.id
                    WHERE t.usuario_id=%s AND t.tipo='Despesa' GROUP BY 1, 2 ORDER BY 1 DESC
                """, (uid,))
                comp_rows = cur.fetchall()

        except:
            return

        pct_rec = (ent / meta_rec * 100) if meta_rec > 0 else 0
        pct_des = (sai / meta_des * 100) if meta_des > 0 else 0
        pct_res = (saldo_mes / meta_res * 100) if meta_res > 0 else 0
        m, a = state["mes"], state["ano"]
        dias_restantes = max(0, monthrange(a, m)[1] - hoje.day) if (m == hoje.month and a == hoje.year) else 0

        def card_meta(titulo, valor, meta, pct, cor_bg, icone):
            return ft.Container(
                content=ft.Column([
                    ft.Row([ft.Text(titulo, size=11, weight="bold", color="white"),
                            ft.Icon(icone, size=16, color="white")], alignment="spaceBetween"),
                    ft.Text(fmt(valor), size=20, weight="bold", color="white"),
                    ft.Row([ft.Text("Meta:", size=10, color="white70"),
                            ft.Text(fmt(meta) if meta > 0 else "—", size=10, color="white")], spacing=4),
                    ft.Container(content=ft.Text(fmt_pct(pct) if meta > 0 else "Sem meta", size=12, weight="bold",
                                                 color="#1B5E20" if pct <= 100 else "#B71C1C"), bgcolor="white",
                                 border_radius=6, padding=ft.padding.symmetric(horizontal=8, vertical=2)),
                    ft.ProgressBar(value=min(pct / 100, 1.0) if meta > 0 else 0, color="white", bgcolor="white24",
                                   height=6),
                ], spacing=6), padding=16, bgcolor=cor_bg, border_radius=12, width=210,
                shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26)
            )

        cards_topo.controls = [
            card_meta("RECEITAS", ent, meta_rec, pct_rec, "#2E7D32", ft.icons.ARROW_UPWARD),
            card_meta("DESPESAS", sai, meta_des, pct_des, "#C62828", ft.icons.ARROW_DOWNWARD),
            ft.Container(content=ft.Column([ft.Row([ft.Text("RESULTADO", size=11, weight="bold", color="white"),
                                                    ft.Icon(ft.icons.ACCOUNT_BALANCE_WALLET, size=16, color="white")],
                                                   alignment="spaceBetween"),
                                            ft.Text(fmt(saldo_mes), size=20, weight="bold", color="white"),
                                            ft.ProgressBar(value=min(pct_res / 100, 1.0) if meta_res > 0 else 0,
                                                           color="white", height=6)], spacing=6), padding=16,
                         bgcolor="#1565C0" if saldo_mes >= 0 else "#B71C1C", border_radius=12, width=210),
            ft.Container(content=ft.Column([ft.Row([ft.Text("ACUMULADO", size=11, weight="bold", color="white"),
                                                    ft.Icon(ft.icons.SAVINGS, size=16, color="white")],
                                                   alignment="spaceBetween"),
                                            ft.Text(fmt(saldo_acumulado), size=20, weight="bold", color="white")],
                                           spacing=6), padding=16, bgcolor="#4527A0", border_radius=12, width=210),
            ft.Container(content=ft.Column([ft.Row([ft.Text("💳 CARTÃO", size=11, weight="bold", color="white"),
                                                    ft.Icon(ft.icons.CREDIT_CARD, size=16, color="white")],
                                                   alignment="spaceBetween"),
                                            ft.Text(fmt(total_cartao), size=20, weight="bold", color="white")],
                                           spacing=6), padding=16, bgcolor="#F57F17", border_radius=12, width=210),
            ft.Container(content=ft.Column([ft.Row([ft.Text("📅 DIAS REST.", size=11, weight="bold", color="white"),
                                                    ft.Icon(ft.icons.CALENDAR_TODAY, size=16, color="white")],
                                                   alignment="spaceBetween"),
                                            ft.Text(str(dias_restantes), size=28, weight="bold", color="white")],
                                           spacing=6), padding=16, bgcolor="#00838F", border_radius=12, width=210),
        ]

        bancos_container.controls = [ft.Container(content=ft.Column(
            [ft.Text(b[0], size=11, weight="bold", color="white"), ft.Text(fmt(b[1]), size=18, color="white")]),
                                                  padding=16, bgcolor="#37474F", border_radius=12, width=210) for b in
                                     bancos_rows]
        detalhes_col.controls = [ft.Column(
            [ft.Row([ft.Text(g[0], expand=True), ft.Text(fmt(g[1]), weight="bold", color="red")]),
             ft.ProgressBar(value=g[1] / sai if sai > 0 else 0, color="#C62828", height=5)], spacing=2) for g in gastos]
        sections = [ft.PieChartSection(g[1], title=f"{g[1] / sai * 100:.0f}%" if g[1] / sai > 0.05 else "",
                                       color=CORES[i % len(CORES)], radius=80) for i, g in enumerate(gastos)]
        pizza_container.controls = [ft.PieChart(sections=sections, height=220)] if sections else [
            ft.Text("Sem despesas")]
        orcamento_container.controls = [ft.Column(
            [ft.Row([ft.Text(o[0], expand=True), ft.Text(fmt(o[2]) + "/" + fmt(o[1]), size=10)]),
             ft.ProgressBar(value=min(o[2] / o[1], 1.0), color="orange" if o[2] > o[1] * 0.8 else "blue", height=8)])
                                        for o in orcamentos]

        hist = defaultdict(lambda: {"Receita": 0.0, "Despesa": 0.0})
        for r in hist_rows: hist[r[0]][r[1]] = float(r[2] or 0)
        grafico_barras_col.controls = [ft.Row(
            [ft.Text(m, width=60), ft.ProgressBar(value=hist[m]['Receita'] / max(ent, 1), color="green", expand=True),
             ft.ProgressBar(value=hist[m]['Despesa'] / max(sai, 1), color="red", expand=True)], spacing=10) for m in
                                       sorted(hist.keys())[-6:]]

        comp_dados = defaultdict(dict);
        meses_c = set()
        for r in comp_rows: comp_dados[r[1]][r[0]] = r[2]; meses_c.add(r[0])
        meses_ord = sorted(list(meses_c))[-3:]
        cols = [ft.DataColumn(ft.Text("Conta"))] + [ft.DataColumn(ft.Text(m)) for m in meses_ord]
        rows_c = [ft.DataRow(
            cells=[ft.DataCell(ft.Text(n))] + [ft.DataCell(ft.Text(fmt(comp_dados[n].get(m, 0)))) for m in meses_ord])
                  for n in comp_dados]
        comparativo_container.controls = [ft.DataTable(columns=cols, rows=rows_c)]

        metas_container.controls = [ft.Row(
            [meta_rec_field, meta_des_field, meta_res_field, ft.ElevatedButton("SALVAR METAS", on_click=salvar_meta)],
            spacing=10, wrap=True), msg_meta]
        page.update()

    dd_mes = ft.Dropdown(label="Mês", width=160, value=get_mes_str(), options=get_meses_opcoes(), on_change=lambda e: (
    state.update({"mes": int(e.control.value.split("/")[0]), "ano": int(e.control.value.split("/")[1])}),
    carregar(e.control.value)))
    carregar(get_mes_str())

    def secao(titulo, subtitulo, conteudo, cor_titulo="blue"):
        return ft.Container(content=ft.Column([ft.Text(titulo, weight="bold", size=14, color=cor_titulo),
                                               ft.Text(subtitulo, size=11,
                                                       color="grey") if subtitulo else ft.Container(),
                                               ft.Divider(height=6), conteudo], spacing=6), padding=16,
                            border=ft.border.all(1, "#E0E0E0"), border_radius=12, bgcolor="white",
                            shadow=ft.BoxShadow(blur_radius=4, color=ft.colors.BLACK12))

    return ft.View(route="/", bgcolor="#F5F6FA", controls=[
        get_menu(page),
        ft.Container(padding=ft.padding.symmetric(horizontal=20, vertical=8), expand=True, content=ft.Column([
            ft.Row([ft.Text("DASHBOARD FINANCEIRO", size=22, weight="bold", color="#1565C0"),
                    ft.Row([ft.Text("Período:", size=12, color="grey"), dd_mes], spacing=8)], alignment="spaceBetween"),
            cards_topo, ft.Divider(height=4, color="transparent"), bancos_container,
            ft.Row([ft.Container(content=secao("📊 RECEITAS VS DESPESAS", "Histórico", grafico_barras_col), expand=3),
                    ft.Container(content=secao("💸 GASTOS POR CONTA", "Mês atual", detalhes_col), expand=2)],
                   spacing=12),
            ft.Row([ft.Container(content=secao("🍕 DESPESAS POR CATEGORIA", "Distribuição", pizza_container), expand=1),
                    ft.Container(content=secao("🎯 ORÇAMENTO MENSAL", "Status", orcamento_container), expand=1)],
                   spacing=12),
            secao("🎯 DEFINIR METAS DO MÊS", "Configure", metas_container),
            secao("📅 COMPARATIVO MENSAL", "Evolução", comparativo_container),
        ], scroll=ft.ScrollMode.ALWAYS, expand=True))
    ])