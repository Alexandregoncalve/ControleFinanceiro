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
        "#1E88E5", "#E53935", "#43A047", "#FDD835", "#8E24AA",
        "#00ACC1", "#6D4C41", "#546E7A", "#D81B60", "#7CB342",
        "#FB8C00", "#039BE5", "#3949AB", "#00897B", "#5E35B1",
    ]

    # Containers principais usando ResponsiveRow para flexibilidade mobile
    cards_topo = ft.ResponsiveRow(spacing=12)
    bancos_container = ft.ResponsiveRow(spacing=12)
    grafico_container = ft.Container(padding=10)
    pizza_row = ft.ResponsiveRow(spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER)
    detalhes_col = ft.Column(scroll=ft.ScrollMode.AUTO, height=320, spacing=10)
    orcamento_col = ft.Column(spacing=10)
    comparativo_col = ft.Column(spacing=6)
    metas_container = ft.Column(spacing=6)

    meta_rec_field = ft.TextField(label="Meta Receita", expand=1, on_blur=formatar_moeda_input)
    meta_des_field = ft.TextField(label="Meta Despesa", expand=1, on_blur=formatar_moeda_input)
    meta_res_field = ft.TextField(label="Meta Resultado", expand=1, on_blur=formatar_moeda_input)
    msg_meta = ft.Text("", size=12, color=ft.colors.GREEN_700)

    def get_meses_comp():
        opcoes = []
        m, a = hoje.month, hoje.year
        for _ in range(24):
            opcoes.append(ft.dropdown.Option(f"{m:02d}/{a}"))
            m -= 1
            if m == 0:
                m = 12
                a -= 1
        return opcoes

    m_ini = hoje.month - 5
    a_ini = hoje.year
    if m_ini <= 0:
        m_ini += 12
        a_ini -= 1

    comp_ini_dd = ft.Dropdown(label="De", expand=1, value=f"{m_ini:02d}/{a_ini}", options=get_meses_comp())
    comp_fim_dd = ft.Dropdown(label="Até", expand=1, value=get_mes_str(), options=get_meses_comp())
    msg_comp = ft.Text("", size=11, color=ft.colors.GREY_600, italic=True)

    def carregar_comparativo(ini_str, fim_str):
        try:
            def meses_entre(ini, fim):
                resultado = []
                m, a = int(ini.split("/")[0]), int(ini.split("/")[1])
                mf, af = int(fim.split("/")[0]), int(fim.split("/")[1])
                while (a < af) or (a == af and m <= mf):
                    resultado.append(f"{m:02d}/{a}")
                    m += 1
                    if m > 12:
                        m = 1
                        a += 1
                return resultado

            meses = meses_entre(ini_str, fim_str)
            if not meses:
                comparativo_col.controls = [ft.Text("Período inválido.", color="red", size=12)]
                page.update()
                return

            with db_session() as cur:
                cur.execute("""
                    SELECT SPLIT_PART(t.data,'/',2)||'/'||SPLIT_PART(t.data,'/',3) as mes,
                           CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.nome ELSE s.nome END as nome,
                           SUM(t.valor) as total
                    FROM transacoes t JOIN subcontas s ON t.subconta_id=s.id
                    LEFT JOIN subcontas sr ON t.categoria_real_id=sr.id
                    WHERE t.usuario_id=%s AND t.tipo='Despesa'
                    GROUP BY 1,2 ORDER BY 1
                """, (uid,))
                comp_rows = cur.fetchall()

            comp_dados = defaultdict(dict)
            meses_c = set()
            for r in comp_rows:
                if r['mes'] in meses:
                    comp_dados[r['nome']][r['mes']] = float(r['total'] or 0)
                    meses_c.add(r['mes'])

            meses_ord = [m for m in meses if m in meses_c]

            if not meses_ord:
                comparativo_col.controls = [ft.Text("Sem dados no período selecionado.", color="grey", italic=True)]
                page.update()
                return

            def cell_comp(nome, m):
                val = comp_dados[nome].get(m, None)
                if val is None:
                    return ft.DataCell(ft.Text("—", color="grey", size=11))
                meses_list = sorted(comp_dados[nome].keys())
                idx = meses_list.index(m) if m in meses_list else -1
                if idx > 0:
                    prev = comp_dados[nome].get(meses_list[idx - 1], None)
                    if prev is not None and prev > 0:
                        cor = "#C62828" if val > prev else "#2E7D32"
                        return ft.DataCell(ft.Text(fmt(val), color=cor, size=11, weight="bold"))
                return ft.DataCell(ft.Text(fmt(val), color="#1E88E5", size=11))

            cols_c = [ft.DataColumn(ft.Text("Conta", weight="bold", size=12))] + [
                ft.DataColumn(ft.Text(m, weight="bold", size=12)) for m in meses_ord]
            rows_c = [
                ft.DataRow(cells=[ft.DataCell(ft.Text(n, size=11))] + [cell_comp(n, m) for m in meses_ord])
                for n in sorted(comp_dados.keys())
            ]

            # Envolvemos a tabela em um container de Rolagem para não estourar o Mobile
            comparativo_col.controls = [
                ft.Row([
                    ft.Container(width=10, height=10, bgcolor="#2E7D32", border_radius=5),
                    ft.Text("diminuiu", size=10, color="#2E7D32"),
                    ft.Container(width=10, height=10, bgcolor="#C62828", border_radius=5),
                    ft.Text("aumentou em relação ao mês anterior", size=10, color="#C62828"),
                ], spacing=6),
                ft.Container(
                    content=ft.DataTable(
                        columns=cols_c, rows=rows_c,
                        border=ft.border.all(1, "#EFEFEF"),
                        border_radius=8,
                        horizontal_lines=ft.border.BorderSide(1, "#F5F5F5"),
                    ),
                    scroll=ft.ScrollMode.HORIZONTAL
                ),
            ]
            msg_comp.value = f"Exibindo {len(meses_ord)} mês(es) com dados."
        except Exception as ex:
            print(f"[dashboard] comparativo erro: {ex}")
            comparativo_col.controls = [ft.Text("Erro ao carregar comparativo.", color="red", size=12)]
        page.update()

    def filtrar_comparativo(e):
        if comp_ini_dd.value and comp_fim_dd.value:
            carregar_comparativo(comp_ini_dd.value, comp_fim_dd.value)

    comp_ini_dd.on_change = filtrar_comparativo
    comp_fim_dd.on_change = filtrar_comparativo

    def salvar_meta(e):
        try:
            mes_str = get_mes_str()
            mr = limpar_valor(meta_rec_field.value)
            md = limpar_valor(meta_des_field.value)
            mres = limpar_valor(meta_res_field.value)
            with db_session() as cur:
                cur.execute("SELECT id FROM metas WHERE mes=%s AND usuario_id=%s", (mes_str, uid))
                if cur.fetchone():
                    cur.execute(
                        "UPDATE metas SET meta_receita=%s, meta_despesa=%s, meta_resultado=%s WHERE mes=%s AND usuario_id=%s",
                        (mr, md, mres, mes_str, uid))
                else:
                    cur.execute(
                        "INSERT INTO metas (mes, meta_receita, meta_despesa, meta_resultado, usuario_id) VALUES (%s,%s,%s,%s,%s)",
                        (mes_str, mr, md, mres, uid))
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
        try:
            with db_session() as cur:
                cur.execute("SELECT COALESCE(SUM(saldo_inicial), 0) as total FROM bancos WHERE usuario_id=%s", (uid,))
                saldo_inicial = float(cur.fetchone()['total'] or 0)
                m_sel, a_sel = int(mes_str.split("/")[0]), int(mes_str.split("/")[1])
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
        try:
            m_sel, a_sel = int(mes_str.split("/")[0]), int(mes_str.split("/")[1])
            with db_session() as cur:
                cur.execute("""
                    SELECT COALESCE(SUM(valor), 0) as total FROM transacoes
                    WHERE usuario_id=%s AND banco_id=%s AND tipo='Receita'
                    AND (
                        CAST(SPLIT_PART(data,'/',3) AS INTEGER) < %s OR
                        (CAST(SPLIT_PART(data,'/',3) AS INTEGER) = %s AND CAST(SPLIT_PART(data,'/',2) AS INTEGER) <= %s)
                    )
                """, (uid, banco_id, a_sel, a_sel, m_sel))
                receitas = float(cur.fetchone()['total'] or 0)
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
                cur.execute(
                    "SELECT COALESCE(SUM(valor),0) as total FROM transacoes WHERE usuario_id=%s AND tipo='Receita' AND data LIKE %s",
                    (uid, f"%%/{mes_str}"))
                ent = float(cur.fetchone()['total'] or 0)
                cur.execute(
                    "SELECT COALESCE(SUM(valor),0) as total FROM transacoes WHERE usuario_id=%s AND tipo='Despesa' AND data LIKE %s",
                    (uid, f"%%/{mes_str}"))
                sai = float(cur.fetchone()['total'] or 0)
                saldo_mes = ent - sai
                saldo_acumulado = calcular_saldo_acumulado(mes_str)

                cur.execute(
                    "SELECT id, nome_banco, saldo_inicial, agencia, numero_conta FROM bancos WHERE usuario_id=%s ORDER BY nome_banco",
                    (uid,))
                bancos_rows = cur.fetchall()

                cur.execute("SELECT * FROM metas WHERE mes=%s AND usuario_id=%s", (mes_str, uid))
                meta_row = cur.fetchone()
                if not meta_row:
                    meta_row = buscar_meta_mes_anterior(mes_str)
                    msg_meta.value = "💡 Meta copiada do mês anterior." if meta_row else ""
                else:
                    msg_meta.value = ""

                meta_rec = float(meta_row['meta_receita'] or 0) if meta_row else 0.0
                meta_des = float(meta_row['meta_despesa'] or 0) if meta_row else 0.0
                meta_res = float(meta_row['meta_resultado'] or 0) if meta_row else 0.0
                meta_rec_field.value = f"{meta_rec:_.2f}".replace(".", ",").replace("_", ".") if meta_rec else ""
                meta_des_field.value = f"{meta_des:_.2f}".replace(".", ",").replace("_", ".") if meta_des else ""
                meta_res_field.value = f"{meta_res:_.2f}".replace(".", ",").replace("_", ".") if meta_res else ""

                cur.execute("""
                    SELECT CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.nome ELSE s.nome END as nome,
                           SUM(t.valor) as total
                    FROM transacoes t JOIN subcontas s ON t.subconta_id=s.id
                    LEFT JOIN subcontas sr ON t.categoria_real_id=sr.id
                    WHERE t.usuario_id=%s AND t.tipo='Despesa' AND t.data LIKE %s
                    GROUP BY 1 ORDER BY 2 DESC
                """, (uid, f"%%/{mes_str}"))
                gastos = cur.fetchall()

                cur.execute(
                    "SELECT COALESCE(SUM(t.valor),0) as total FROM transacoes t JOIN subcontas s ON t.subconta_id=s.id WHERE t.usuario_id=%s AND t.tipo='Despesa' AND t.data LIKE %s AND (s.nome ILIKE '%%CARTAO%%' OR s.nome ILIKE '%%CARTÃO%%')",
                    (uid, f"%%/{mes_str}"))
                total_cartao = float(cur.fetchone()['total'] or 0)

                cur.execute(
                    "SELECT COUNT(*) as total FROM subcontas s WHERE s.fixa=1 AND s.usuario_id=%s AND s.id NOT IN (SELECT subconta_id FROM transacoes WHERE data LIKE %s AND usuario_id=%s)",
                    (uid, f"%%/{mes_str}", uid))
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

                cur.execute(
                    "SELECT SPLIT_PART(data,'/',2)||'/'||SPLIT_PART(data,'/',3) as m, tipo, SUM(valor) as total FROM transacoes WHERE usuario_id=%s GROUP BY 1,2 ORDER BY 1",
                    (uid,))
                hist_rows = cur.fetchall()

        except Exception as ex:
            print(f"[dashboard] carregar erro: {ex}")
            return

        pct_rec = (ent / meta_rec * 100) if meta_rec > 0 else 0
        pct_des = (sai / meta_des * 100) if meta_des > 0 else 0
        pct_res = (saldo_mes / meta_res * 100) if meta_res > 0 else 0
        m, a = state["mes"], state["ano"]
        dias_restantes = max(0, monthrange(a, m)[1] - hoje.day) if (m == hoje.month and a == hoje.year) else 0
        pct_cartao = (total_cartao / sai * 100) if sai > 0 else 0

        # ── NOVO DESIGN: CARDS CLEAN (ESTILO BANKING PREMIUM) ──
        def card_meta_clean(titulo, valor, meta, pct, cor_destaque, icone, col_size):
            cor_progresso = ft.colors.GREEN_600 if pct <= 100 and titulo == "DESPESAS" or (
                        pct >= 100 and titulo == "RECEITAS") else ft.colors.RED_600
            return ft.Container(
                col={"sm": 12, "md": 6, "lg": 2},  # Responsivo total para mobile
                padding=16, bgcolor="white", border_radius=12,
                border=ft.border.all(1, "#E8EBF0"),
                content=ft.Column([
                    ft.Row([
                        ft.Text(titulo, size=11, weight="bold", color="#758A9F"),
                        ft.Icon(icone, size=16, color=cor_destaque)
                    ], alignment="spaceBetween"),
                    ft.Text(fmt(valor), size=18, weight="bold", color="#1C2D42"),
                    ft.Row([
                        ft.Text("Meta:", size=10, color="#758A9F"),
                        ft.Text(fmt(meta) if meta > 0 else "—", size=10, color="#1C2D42", weight="bold"),
                    ], spacing=4),
                    ft.Row([
                        ft.ProgressBar(value=min(pct / 100, 1.0) if meta > 0 else 0, color=cor_destaque,
                                       bgcolor="#F0F2F5", height=4, expand=True),
                        ft.Text(fmt_pct(pct) if meta > 0 else "—", size=10, weight="bold", color=cor_progresso)
                    ], spacing=8)
                ], spacing=6)
            )

        cards_topo.controls = [
            card_meta_clean("RECEITAS", ent, meta_rec, pct_rec, "#2E7D32", ft.icons.ARROW_UPWARD, 2),
            card_meta_clean("DESPESAS", sai, meta_des, pct_des, "#C62828", ft.icons.ARROW_DOWNWARD, 2),
            ft.Container(
                col={"sm": 12, "md": 6, "lg": 2},
                padding=16, bgcolor="white", border_radius=12, border=ft.border.all(1, "#E8EBF0"),
                content=ft.Column([
                    ft.Row([ft.Text("RESULTADO", size=11, weight="bold", color="#758A9F"),
                            ft.Icon(ft.icons.ACCOUNT_BALANCE_WALLET, size=16, color="#1565C0")],
                           alignment="spaceBetween"),
                    ft.Text(fmt(saldo_mes), size=18, weight="bold", color="#1565C0" if saldo_mes >= 0 else "#C62828"),
                    ft.Row([ft.Text("Meta:", size=10, color="#758A9F"),
                            ft.Text(fmt(meta_res) if meta_res > 0 else "—", size=10, color="#1C2D42", weight="bold")],
                           spacing=4),
                    ft.Row([
                        ft.ProgressBar(value=min(pct_res / 100, 1.0) if meta_res > 0 else 0, color="#1565C0",
                                       bgcolor="#F0F2F5", height=4, expand=True),
                        ft.Text(fmt_pct(pct_res) if meta_res > 0 else "—", size=10, weight="bold", color="#1565C0")
                    ], spacing=8)
                ], spacing=6)
            ),
            ft.Container(
                col={"sm": 12, "md": 6, "lg": 2},
                padding=16, bgcolor="white", border_radius=12, border=ft.border.all(1, "#E8EBF0"),
                content=ft.Column([
                    ft.Row([ft.Text("ACUMULADO", size=11, weight="bold", color="#758A9F"),
                            ft.Icon(ft.icons.SAVINGS, size=16, color="#4527A0")], alignment="spaceBetween"),
                    ft.Text(fmt(saldo_acumulado), size=18, weight="bold", color="#4527A0"),
                    ft.Text("Saldo total geral", size=10, color="#758A9F"),
                ], spacing=8)
            ),
            ft.Container(
                col={"sm": 12, "md": 6, "lg": 2},
                padding=16, bgcolor="white", border_radius=12, border=ft.border.all(1, "#E8EBF0"),
                content=ft.Column([
                    ft.Row([ft.Text("CARTÃO", size=11, weight="bold", color="#758A9F"),
                            ft.Icon(ft.icons.CREDIT_CARD, size=16, color="#F57F17")], alignment="spaceBetween"),
                    ft.Text(fmt(total_cartao), size=18, weight="bold", color="#1C2D42"),
                    ft.Row([
                        ft.ProgressBar(value=min(pct_cartao / 100, 1.0), color="#F57F17", bgcolor="#F0F2F5", height=4,
                                       expand=True),
                        ft.Text(f"{pct_cartao:.1f}%", size=10, color="#758A9F", weight="bold")
                    ], spacing=8)
                ], spacing=6)
            ),
            ft.Container(
                col={"sm": 12, "md": 6, "lg": 2},
                padding=16, bgcolor="white", border_radius=12, border=ft.border.all(1, "#E8EBF0"),
                content=ft.Column([
                    ft.Row([ft.Text("DIAS REST.", size=11, weight="bold", color="#758A9F"),
                            ft.Icon(ft.icons.CALENDAR_TODAY, size=16, color="#00838F")], alignment="spaceBetween"),
                    ft.Text(str(dias_restantes), size=22, weight="bold", color="#1C2D42"),
                    ft.Text(f"⚠ {fixas_pendentes} pendentes" if fixas_pendentes > 0 else "Tudo em dia 🎉", size=10,
                            color="#F57F17" if fixas_pendentes > 0 else "#2E7D32", weight="bold"),
                ], spacing=6)
            ),
        ]

        # ── BANCOS (VISUAL LIMPO E FLUIDO) ──
        bancos_cards = []
        for b in bancos_rows:
            saldo_real = calcular_saldo_banco(b['id'], float(b['saldo_inicial'] or 0), mes_str)
            variacao = saldo_real - float(b['saldo_inicial'] or 0)
            cor_var = "#2E7D32" if variacao >= 0 else "#C62828"
            sinal = "▲" if variacao >= 0 else "▼"
            bancos_cards.append(
                ft.Container(
                    col={"sm": 12, "md": 4, "lg": 3},
                    padding=16, bgcolor="white", border_radius=12, border=ft.border.all(1, "#E8EBF0"),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.icons.ACCOUNT_BALANCE, color="#758A9F", size=16),
                            ft.Text(b['nome_banco'], size=13, weight="bold", color="#1C2D42", expand=True),
                            ft.Text(f"{sinal} {fmt(abs(variacao))}", size=10, color=cor_var, weight="bold")
                        ], spacing=6),
                        ft.Text(fmt(saldo_real), size=18, weight="bold", color="#1C2D42"),
                        ft.Text(f"Ag: {b['agencia'] or '—'} | Cta: {b['numero_conta'] or '—'}", size=10,
                                color="#758A9F"),
                    ], spacing=4)
                )
            )
        bancos_container.controls = bancos_cards

        # ── NOVO GRÁFICO PROFISSIONAL (NATIVO DO FLET) ──
        hist = defaultdict(lambda: {"Receita": 0.0, "Despesa": 0.0})
        for r in hist_rows:
            hist[r['m']][r['tipo']] = float(r['total'] or 0)
        meses_hist = sorted(hist.keys())[-6:]

        chart_groups = []
        for idx, m in enumerate(meses_hist):
            chart_groups.append(
                ft.BarChartGroup(
                    x=idx,
                    bar_rods=[
                        ft.BarChartRod(from_y=0, to_y=hist[m]['Receita'], color="#2E7D32", width=12, border_radius=3),
                        ft.BarChartRod(from_y=0, to_y=hist[m]['Despesa'], color="#C62828", width=12, border_radius=3),
                    ],
                )
            )

        grafico_col.controls = [
            ft.Row([
                ft.Row([ft.Container(width=10, height=10, bgcolor="#2E7D32", border_radius=2),
                        ft.Text("Receita", size=11, color="#546E7A")]),
                ft.Row([ft.Container(width=10, height=10, bgcolor="#C62828", border_radius=2),
                        ft.Text("Despesa", size=11, color="#546E7A")]),
            ], alignment="end", spacing=12),
            ft.Container(
                content=ft.BarChart(
                    bar_groups=chart_groups,
                    border=ft.border.all(1, "#E8EBF0"),
                    bottom_axis=ft.ChartAxis(
                        labels=[ft.ChartAxisLabel(value=i, label=ft.Text(m, size=10, color="#758A9F", weight="bold"))
                                for i, m in enumerate(meses_hist)],
                        labels_size=20,
                    ),
                    horizontal_grid_lines=ft.ChartGridLines(color="#F0F2F5", width=1),
                    height=200,
                ),
                padding=ft.padding.only(top=10)
            )
        ]

        # ── GASTOS (MAIS ESPAÇAMENTO E LEITURA) ──
        detalhes_col.controls.clear()
        if gastos:
            for g in gastos:
                detalhes_col.controls.append(
                    ft.Column([
                        ft.Row([
                            ft.Text(g['nome'], expand=True, size=12, color="#1C2D42", weight="w500"),
                            ft.Text(fmt(g['total']), weight="bold", color="#C62828", size=12),
                            ft.Text(f"{g['total'] / sai * 100:.1f}%" if sai > 0 else "0%", size=10, color="#758A9F",
                                    width=42, text_align="end"),
                        ]),
                        ft.ProgressBar(value=g['total'] / sai if sai > 0 else 0, color="#C62828", bgcolor="#F5F5F5",
                                       height=4, border_radius=2),
                    ], spacing=4)
                )
        else:
            detalhes_col.controls.append(ft.Text("Sem despesas no período.", color="grey", italic=True))

        # ── PIZZA (RESPONSIVO PARA CELULAR) ──
        if gastos and sai > 0:
            sections = [
                ft.PieChartSection(
                    value=float(g['total']),
                    title="",  # Remove títulos embolados de dentro da pizza
                    color=CORES[i % len(CORES)], radius=50,
                ) for i, g in enumerate(gastos)
            ]
            legenda = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=180, controls=[
                ft.Row([
                    ft.Container(width=10, height=10, bgcolor=CORES[i % len(CORES)], border_radius=2),
                    ft.Text(g['nome'], size=11, expand=True, color="#1C2D42"),
                    ft.Text(fmt(g['total']), size=11, color="#C62828", weight="bold"),
                    ft.Text(f"{g['total'] / sai * 100:.1f}%", size=10, color="#758A9F", width=40, text_align="end"),
                ], spacing=6) for i, g in enumerate(gastos)
            ])

            # No Mobile (sm), o gráfico ocupa 12 colunas e a legenda 12 colunas (fica um embaixo do outro)
            pizza_row.controls = [
                ft.Container(content=ft.PieChart(sections=sections, height=140, center_space_radius=40),
                             col={"sm": 12, "lg": 5}),
                ft.Container(content=legenda, col={"sm": 12, "lg": 7}),
            ]
        else:
            pizza_row.controls = [ft.Text("Sem despesas no período.", color="grey", italic=True)]

        # ── ORÇAMENTO ──
        def badge_orc(pct):
            if pct >= 100:
                return ("🔴", "#FFEBEE", "#C62828")
            elif pct >= 80:
                return ("🟡", "#FFF8E1", "#FB8C00")
            else:
                return ("✅", "#E8F5E9", "#2E7D32")

        if orcamentos:
            orcamento_col.controls = [
                                         ft.Row([
                                             ft.Row(
                                                 [ft.Container(width=8, height=8, bgcolor="#2E7D32", border_radius=4),
                                                  ft.Text("Dentro do limite", size=10, color="#758A9F")]),
                                             ft.Row(
                                                 [ft.Container(width=8, height=8, bgcolor="#FB8C00", border_radius=4),
                                                  ft.Text("Atenção (+80%)", size=10, color="#758A9F")]),
                                             ft.Row(
                                                 [ft.Container(width=8, height=8, bgcolor="#C62828", border_radius=4),
                                                  ft.Text("Estourou", size=10, color="#758A9F")]),
                                         ], spacing=12),
                                     ] + [
                                         ft.Container(
                                             border_radius=10, padding=12,
                                             bgcolor=
                                             badge_orc(o['total'] / o['orcamento'] * 100 if o['orcamento'] > 0 else 0)[
                                                 1],
                                             content=ft.Column([
                                                 ft.Row([
                                                     ft.Text(badge_orc(o['total'] / o['orcamento'] * 100 if o[
                                                                                                                'orcamento'] > 0 else 0)[
                                                                 0] + " " + o['nome'],
                                                             expand=True, size=12, weight="bold",
                                                             color=badge_orc(o['total'] / o['orcamento'] * 100 if o[
                                                                                                                      'orcamento'] > 0 else 0)[
                                                                 2]),
                                                     ft.Text(f"{fmt(o['total'])} / {fmt(o['orcamento'])}", size=11,
                                                             color=badge_orc(o['total'] / o['orcamento'] * 100 if o[
                                                                                                                      'orcamento'] > 0 else 0)[
                                                                 2]),
                                                 ]),
                                                 ft.ProgressBar(
                                                     value=min(o['total'] / o['orcamento'], 1.0) if o[
                                                                                                        'orcamento'] > 0 else 0,
                                                     color=badge_orc(o['total'] / o['orcamento'] * 100 if o[
                                                                                                              'orcamento'] > 0 else 0)[
                                                         2],
                                                     bgcolor="white", height=6, border_radius=3),
                                                 ft.Text(
                                                     ("Ultrapassado em " if o['total'] > o[
                                                         'orcamento'] else "Restam ") + fmt(
                                                         abs(o['orcamento'] - o['total'])),
                                                     size=10, weight="bold", color=badge_orc(
                                                         o['total'] / o['orcamento'] * 100 if o[
                                                                                                  'orcamento'] > 0 else 0)[
                                                         2]),
                                             ], spacing=4)) for o in orcamentos
                                     ]
        else:
            orcamento_col.controls = [ft.Text("Nenhum orçamento definido.", color="grey", italic=True, size=12)]

        metas_container.controls = [
            ft.ResponsiveRow([
                ft.Container(content=meta_rec_field, col={"sm": 12, "md": 3}),
                ft.Container(content=meta_des_field, col={"sm": 12, "md": 3}),
                ft.Container(content=meta_res_field, col={"sm": 12, "md": 3}),
                ft.Container(
                    content=ft.ElevatedButton("SALVAR METAS", bgcolor="#1565C0", color="white", on_click=salvar_meta,
                                              height=48), col={"sm": 12, "md": 3}),
            ], spacing=10),
            msg_meta,
        ]

        carregar_comparativo(comp_ini_dd.value, comp_fim_dd.value)
        page.update()

    dd_mes = ft.Dropdown(
        label="Mês Filtro", width=140, value=get_mes_str(), options=get_meses_opcoes(),
        on_change=lambda e: (
            state.update({"mes": int(e.control.value.split("/")[0]), "ano": int(e.control.value.split("/")[1])}),
            carregar(e.control.value)
        )
    )
    carregar(get_mes_str())

    def secao(titulo, subtitulo, conteudo, col_size):
        return ft.Container(
            col=col_size,
            content=ft.Column([
                ft.Text(titulo, weight="bold", size=14, color="#1C2D42"),
                ft.Text(subtitulo, size=11, color="#758A9F") if subtitulo else ft.Container(),
                ft.Divider(height=10, color="#F0F2F5"),
                conteudo,
            ], spacing=4),
            padding=16, border=ft.border.all(1, "#E8EBF0"), border_radius=12, bgcolor="white"
        )

    comparativo_conteudo = ft.Column([
        ft.ResponsiveRow([
            ft.Container(content=comp_ini_dd, col={"sm": 6, "md": 2}),
            ft.Container(content=comp_fim_dd, col={"sm": 6, "md": 2}),
            ft.Container(content=msg_comp, col={"sm": 12, "md": 8}, alignment=ft.alignment.center_left),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Divider(height=10, color="#F0F2F5"),
        comparativo_col,
    ], spacing=6)

    # Grid central totalmente responsiva usando ResponsiveRow
    grid_dashboard = ft.ResponsiveRow([
        secao("📊 RECEITAS VS DESPESAS", "Evolução dos últimos 6 meses", grafico_col, {"sm": 12, "lg": 6}),
        secao("💸 GASTOS POR CONTA", "Onde você mais gastou esse mês", pizza_row, {"sm": 12, "lg": 6}),
        secao("📋 DETALHAMENTO DE GASTOS", "Lista ordenada de saídas", detalhes_col, {"sm": 12, "lg": 4}),
        secao("🎯 EVOLUÇÃO DE ORÇAMENTOS", "Metas de teto por categoria", orcamento_col, {"sm": 12, "lg": 4}),
        secao("⚙ CONFIGURAR METAS DO MÊS", "Ajuste seus objetivos financeiros", metas_container, {"sm": 12, "lg": 4}),
        secao("🔄 COMPARATIVO EVOLUTIVO", "Histórico de despesas lado a lado", comparativo_conteudo,
              {"sm": 12, "lg": 12}),
    ], spacing=16)

    return ft.View(route="/", bgcolor="#F8F9FA", controls=[
        get_menu(page),
        ft.Container(
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            expand=True,
            content=ft.Column([
                ft.Row([
                    ft.Text("DASHBOARD", size=20, weight="bold", color="#1C2D42"),
                    dd_mes
                ], alignment="spaceBetween"),
                ft.Divider(height=10, color="transparent"),
                cards_topo,
                ft.Text("CONTA CORRENTE & BANCOS", size=12, weight="bold", color="#758A9F"),
                bancos_container,
                ft.Divider(height=5, color="transparent"),
                grid_dashboard
            ], spacing=12, scroll=ft.ScrollMode.AUTO)
        )
    ])