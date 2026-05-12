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
        except Exception as ex:
            msg_meta.value = "❌ Erro ao salvar metas."
            page.update()

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
                saldo_ant = 0.0
                for r in cur.fetchall():
                    saldo_ant += float(r[1] or 0) if r[0] == "Receita" else -float(r[1] or 0)
                return saldo_inicial + saldo_ant
        except:
            return 0.0

    def carregar(mes_str):
        try:
            with db_session() as cur:
                # 1. Totais
                cur.execute(
                    "SELECT COALESCE(SUM(valor),0) FROM transacoes WHERE usuario_id=%s AND tipo='Receita' AND data LIKE %s",
                    (uid, f"%{mes_str}"))
                ent = float(cur.fetchone()[0] or 0)
                cur.execute(
                    "SELECT COALESCE(SUM(valor),0) FROM transacoes WHERE usuario_id=%s AND tipo='Despesa' AND data LIKE %s",
                    (uid, f"%{mes_str}"))
                sai = float(cur.fetchone()[0] or 0)

                saldo_anterior = calcular_saldo_acumulado(mes_str)
                saldo_mes, saldo_acumulado = ent - sai, saldo_anterior + (ent - sai)

                # 2. Bancos e Metas
                cur.execute("SELECT nome_banco, saldo_inicial FROM bancos WHERE usuario_id=%s ORDER BY nome_banco",
                            (uid,))
                bancos_rows = cur.fetchall()
                cur.execute("SELECT * FROM metas WHERE mes=%s AND usuario_id=%s", (mes_str, uid))
                meta_row = cur.fetchone()
                meta_rec = float(meta_row[2] or 0) if meta_row else 0.0
                meta_des = float(meta_row[3] or 0) if meta_row else 0.0
                meta_res = float(meta_row[4] or 0) if meta_row else 0.0

                # 3. Gastos Detalhados e Cartão
                cur.execute("""
                    SELECT CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.nome ELSE s.nome END as nome_exib, SUM(t.valor) as total
                    FROM transacoes t JOIN subcontas s ON t.subconta_id = s.id LEFT JOIN subcontas sr ON t.categoria_real_id = sr.id
                    WHERE t.usuario_id=%s AND t.tipo='Despesa' AND t.data LIKE %s GROUP BY nome_exib ORDER BY total DESC
                """, (uid, f"%{mes_str}"))
                gastos = cur.fetchall()

                cur.execute(
                    "SELECT COALESCE(SUM(t.valor),0) FROM transacoes t JOIN subcontas s ON t.subconta_id = s.id WHERE t.usuario_id=%s AND t.tipo='Despesa' AND t.data LIKE %s AND (s.nome ILIKE '%CARTAO%' OR s.nome ILIKE '%CARTÃO%')",
                    (uid, f"%{mes_str}"))
                total_cartao = float(cur.fetchone()[0] or 0)

                # 4. Orçamentos e Histórico
                cur.execute("""
                    SELECT CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.nome ELSE s.nome END as nome_exib, 
                           MAX(CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.orcamento ELSE s.orcamento END) as orc_val, SUM(t.valor) as gasto
                    FROM transacoes t JOIN subcontas s ON t.subconta_id = s.id LEFT JOIN subcontas sr ON t.categoria_real_id = sr.id
                    WHERE t.usuario_id=%s AND t.tipo='Despesa' AND t.data LIKE %s GROUP BY nome_exib HAVING MAX(CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.orcamento ELSE s.orcamento END) > 0
                """, (uid, f"%{mes_str}"))
                orc_rows = cur.fetchall()

                cur.execute(
                    "SELECT SPLIT_PART(data, '/', 2) || '/' || SPLIT_PART(data, '/', 3) as mes, tipo, SUM(valor) FROM transacoes WHERE usuario_id=%s GROUP BY mes, tipo ORDER BY mes DESC LIMIT 24",
                    (uid,))
                hist_rows = cur.fetchall()

        except Exception as e:
            print(f"Erro Carregar: {e}"); return

        # --- CONSTRUÇÃO VISUAL (RESTAURADA) ---
        def card_meta(titulo, valor, meta, pct, cor_bg, icone):
            return ft.Container(
                content=ft.Column([
                    ft.Row([ft.Text(titulo, size=11, weight="bold", color="white"),
                            ft.Icon(icone, size=16, color="white")], alignment="spaceBetween"),
                    ft.Text(fmt(valor), size=20, weight="bold", color="white"),
                    ft.ProgressBar(value=min(pct / 100, 1.0) if meta > 0 else 0, color="white", bgcolor="white24",
                                   height=6),
                ], spacing=6), padding=16, bgcolor=cor_bg, border_radius=12, width=210
            )

        cards_topo.controls = [
            card_meta("RECEITAS", ent, meta_rec, (ent / meta_rec * 100 if meta_rec > 0 else 0), "#2E7D32",
                      ft.icons.ARROW_UPWARD),
            card_meta("DESPESAS", sai, meta_des, (sai / meta_des * 100 if meta_des > 0 else 0), "#C62828",
                      ft.icons.ARROW_DOWNWARD),
            card_meta("RESULTADO", saldo_mes, meta_res, (saldo_mes / meta_res * 100 if meta_res > 0 else 0), "#1565C0",
                      ft.icons.ACCOUNT_BALANCE_WALLET),
            card_meta("CARTÃO", total_cartao, 0, 0, "#F57F17", ft.icons.CREDIT_CARD),
        ]

        bancos_container.controls = [
            ft.Container(content=ft.Text(f"🏦 {b[0]}: {fmt(b[1])}", color="white"), padding=12, bgcolor="#37474F",
                         border_radius=8) for b in bancos_rows]

        detalhes_col.controls = [ft.Row([ft.Text(g[0], expand=True), ft.Text(fmt(g[1]), weight="bold", color="red")])
                                 for g in gastos]

        # Pizza e Gráficos
        sections = [
            ft.PieChartSection(g[1], title=f"{g[1] / sai * 100:.0f}%" if sai > 0 else "", color=CORES[i % len(CORES)],
                               radius=50) for i, g in enumerate(gastos[:5])]
        pizza_container.controls = [ft.PieChart(sections=sections, height=150)] if sections else [ft.Text("Sem dados")]

        # Orçamentos
        orcamento_container.controls = [
            ft.Column([ft.Text(o[0], size=12), ft.ProgressBar(value=(o[2] / o[1] if o[1] > 0 else 0), color="orange")])
            for o in orc_rows]

        # Metas
        metas_container.controls = [
            ft.Row([meta_rec_field, meta_des_field, meta_res_field, ft.ElevatedButton("SALVAR", on_click=salvar_meta)])]

        page.update()

    dd_mes = ft.Dropdown(label="Mês", width=160, value=get_mes_str(), options=get_meses_opcoes(), on_change=lambda e: (
    state.update({"mes": int(e.control.value.split("/")[0]), "ano": int(e.control.value.split("/")[1])}),
    carregar(e.control.value)))
    carregar(get_mes_str())

    def secao(titulo, subtitulo, conteudo):
        return ft.Container(content=ft.Column(
            [ft.Text(titulo, weight="bold", size=14, color="#1565C0"), ft.Text(subtitulo, size=11, color="grey"),
             ft.Divider(height=6), conteudo], spacing=6), padding=16, border=ft.border.all(1, "#E0E0E0"),
                            border_radius=12, bgcolor="white")

    return ft.View(route="/", bgcolor="#F5F6FA", controls=[
        get_menu(page),
        ft.Container(padding=20, content=ft.Column([
            ft.Row([ft.Text("DASHBOARD FINANCEIRO", size=22, weight="bold", color="#1565C0"), dd_mes],
                   alignment="spaceBetween"),
            cards_topo, bancos_container,
            ft.Row([ft.Container(secao("📊 GASTOS POR CONTA", "Mês atual", detalhes_col), expand=1),
                    ft.Container(secao("🍕 CATEGORIAS", "Pizza", pizza_container), expand=1)], spacing=12),
            ft.Row([ft.Container(secao("🎯 ORÇAMENTOS", "Limites", orcamento_container), expand=1),
                    ft.Container(secao("🎯 DEFINIR METAS", "Configurar", metas_container), expand=1)], spacing=12),
        ], scroll=ft.ScrollMode.ALWAYS, expand=True))
    ])