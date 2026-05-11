import flet as ft
from datetime import datetime
from calendar import monthrange
from collections import defaultdict
from menu import get_menu
from database import get_connection, get_cursor
from utils import limpar_valor, formatar_moeda_input


def dashboard_view(page):
    hoje  = datetime.now()
    state = {"mes": hoje.month, "ano": hoje.year}
    uid   = page.session.get("user_id")

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

    cards_topo            = ft.Row(spacing=12, wrap=True)
    bancos_container      = ft.Row(spacing=12, wrap=True)
    grafico_barras_col    = ft.Column(spacing=8)
    pizza_container       = ft.Column(spacing=6)
    detalhes_col          = ft.Column(scroll=ft.ScrollMode.AUTO, height=300, spacing=4)
    orcamento_container   = ft.Column(spacing=6)
    comparativo_container = ft.Column(spacing=6)
    metas_container       = ft.Column(spacing=6)

    meta_rec_field = ft.TextField(label="Meta Receita",   width=180, on_blur=formatar_moeda_input)
    meta_des_field = ft.TextField(label="Meta Despesa",   width=180, on_blur=formatar_moeda_input)
    meta_res_field = ft.TextField(label="Meta Resultado", width=180, on_blur=formatar_moeda_input)
    msg_meta       = ft.Text("", size=12, color=ft.colors.GREEN_700)

    def salvar_meta(e):
        try:
            mes_str = get_mes_str()
            conn    = get_connection()
            cur     = get_cursor(conn)
            cur.execute("SELECT id FROM metas WHERE mes=%s AND usuario_id=%s", (mes_str, uid))
            row  = cur.fetchone()
            mr   = limpar_valor(meta_rec_field.value)
            md   = limpar_valor(meta_des_field.value)
            mres = limpar_valor(meta_res_field.value)
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
            conn.commit()
            conn.close()
            msg_meta.value = "✅ Metas salvas!"
            carregar(mes_str)
            page.update()
        except Exception as ex:
            print(f"[dashboard] salvar_meta: {ex}")
            msg_meta.value = "❌ Erro ao salvar metas."
            page.update()

    def buscar_meta_mes_anterior(mes_str: str):
        try:
            mes_ant = mes_anterior_str(mes_str)
            conn    = get_connection()
            cur     = get_cursor(conn)
            cur.execute("SELECT * FROM metas WHERE mes=%s AND usuario_id=%s", (mes_ant, uid))
            row = cur.fetchone()
            conn.close()
            return row
        except Exception as ex:
            print(f"[dashboard] buscar_meta_mes_anterior: {ex}")
            return None

    def calcular_saldo_acumulado(mes_str: str) -> float:
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("SELECT COALESCE(SUM(saldo_inicial), 0) as total FROM bancos WHERE usuario_id=%s", (uid,))
            row = cur.fetchone()
            saldo_inicial = float(row["total"] if row and row["total"] else 0)
            m_sel = int(mes_str.split("/")[0])
            a_sel = int(mes_str.split("/")[1])
            cur.execute("""
                SELECT tipo, SUM(valor) as total FROM transacoes
                WHERE usuario_id=%s AND (
                    CAST(SPLIT_PART(data, '/', 3) AS INTEGER) < %s OR
                    (CAST(SPLIT_PART(data, '/', 3) AS INTEGER) = %s AND
                     CAST(SPLIT_PART(data, '/', 2) AS INTEGER) < %s)
                )
                GROUP BY tipo
            """, (uid, a_sel, a_sel, m_sel))
            rows = cur.fetchall()
            conn.close()
            saldo_anterior = 0.0
            for r in rows:
                if r["tipo"] == "Receita":
                    saldo_anterior += float(r["total"] or 0)
                else:
                    saldo_anterior -= float(r["total"] or 0)
            return saldo_inicial + saldo_anterior
        except Exception as ex:
            print(f"[dashboard] calcular_saldo_acumulado: {ex}")
            return 0.0

    def carregar(mes_str):
        try:
            conn = get_connection()
            cur  = get_cursor(conn)

            cur.execute("SELECT COALESCE(SUM(valor),0) as total FROM transacoes WHERE usuario_id=%s AND tipo='Receita' AND data LIKE %s", (uid, f"%{mes_str}",))
            row = cur.fetchone()
            ent = float(row["total"] if row and row["total"] else 0)

            cur.execute("SELECT COALESCE(SUM(valor),0) as total FROM transacoes WHERE usuario_id=%s AND tipo='Despesa' AND data LIKE %s", (uid, f"%{mes_str}",))
            row = cur.fetchone()
            sai = float(row["total"] if row and row["total"] else 0)

            saldo_anterior  = calcular_saldo_acumulado(mes_str)
            saldo_mes       = ent - sai
            saldo_acumulado = saldo_anterior + saldo_mes

            cur.execute("SELECT nome_banco, saldo_inicial FROM bancos WHERE usuario_id=%s ORDER BY nome_banco", (uid,))
            bancos_rows = cur.fetchall()

            cur.execute("SELECT * FROM metas WHERE mes=%s AND usuario_id=%s", (mes_str, uid))
            meta_row = cur.fetchone()

            if not meta_row:
                meta_row = buscar_meta_mes_anterior(mes_str)
                msg_meta.value = "💡 Meta copiada do mês anterior. Salve para confirmar." if meta_row else ""
            else:
                msg_meta.value = ""

            meta_rec = float(meta_row["meta_receita"]   or 0) if meta_row else 0.0
            meta_des = float(meta_row["meta_despesa"]   or 0) if meta_row else 0.0
            meta_res = float(meta_row["meta_resultado"] or 0) if meta_row else 0.0

            meta_rec_field.value = f"{meta_rec:_.2f}".replace(".", ",").replace("_", ".") if meta_rec else ""
            meta_des_field.value = f"{meta_des:_.2f}".replace(".", ",").replace("_", ".") if meta_des else ""
            meta_res_field.value = f"{meta_res:_.2f}".replace(".", ",").replace("_", ".") if meta_res else ""

            cur.execute("""
                SELECT
                    CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.nome ELSE s.nome END as nome_exib,
                    SUM(t.valor) as total
                FROM transacoes t
                JOIN subcontas s ON t.subconta_id = s.id
                LEFT JOIN subcontas sr ON t.categoria_real_id = sr.id
                WHERE t.usuario_id=%s AND t.tipo='Despesa' AND t.data LIKE %s
                GROUP BY nome_exib ORDER BY total DESC
            """, (uid, f"%{mes_str}",))
            gastos = cur.fetchall()

            cur.execute("""
                SELECT COALESCE(SUM(t.valor),0) as total FROM transacoes t
                JOIN subcontas s ON t.subconta_id = s.id
                WHERE t.usuario_id=%s AND t.tipo='Despesa' AND t.data LIKE %s
                AND (s.nome LIKE '%CARTAO%' OR s.nome LIKE '%CARTÃO%')
            """, (uid, f"%{mes_str}",))
            row = cur.fetchone()
            total_cartao = float(row["total"] if row and row["total"] else 0)

            cur.execute("""
                SELECT COUNT(*) as total FROM subcontas s WHERE s.fixa=1 AND s.usuario_id=%s
                AND s.id NOT IN (SELECT subconta_id FROM transacoes WHERE data LIKE %s AND usuario_id=%s)
            """, (uid, f"%{mes_str}", uid))
            row = cur.fetchone()
            fixas_pendentes = int(row["total"] if row and row["total"] else 0)

            cur.execute("""
                SELECT
                    CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.nome ELSE s.nome END as nome_exib,
                    CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.orcamento ELSE s.orcamento END as orc_val,
                    SUM(t.valor) as gasto
                FROM transacoes t
                JOIN subcontas s ON t.subconta_id = s.id
                LEFT JOIN subcontas sr ON t.categoria_real_id = sr.id
                WHERE t.usuario_id=%s AND t.tipo='Despesa' AND t.data LIKE %s
                GROUP BY nome_exib, orc_val HAVING MAX(CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.orcamento ELSE s.orcamento END) > 0
                ORDER BY (SUM(t.valor) / MAX(CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.orcamento ELSE s.orcamento END)) DESC
            """, (uid, f"%{mes_str}",))
            orcamentos = cur.fetchall()

            cur.execute("""
                SELECT SPLIT_PART(data, '/', 2) || '/' || SPLIT_PART(data, '/', 3) as mes,
                       tipo, SUM(valor) as total
                FROM transacoes WHERE usuario_id=%s
                GROUP BY mes, tipo ORDER BY mes DESC LIMIT 24
            """, (uid,))
            hist_rows = cur.fetchall()

            cur.execute("""
                SELECT
                    SPLIT_PART(t.data, '/', 2) || '/' || SPLIT_PART(t.data, '/', 3) as mes,
                    CASE WHEN t.categoria_real_id IS NOT NULL THEN sr.nome ELSE s.nome END as nome_exib,
                    SUM(t.valor) as total
                FROM transacoes t
                JOIN subcontas s ON t.subconta_id = s.id
                LEFT JOIN subcontas sr ON t.categoria_real_id = sr.id
                WHERE t.usuario_id=%s AND t.tipo='Despesa'
                GROUP BY mes, nome_exib ORDER BY mes DESC
            """, (uid,))
            comp_rows = cur.fetchall()
            conn.close()

        except Exception as ex:
            print(f"[dashboard] carregar: {ex}")
            return

        pct_rec = (ent / meta_rec * 100) if meta_rec > 0 else 0
        pct_des = (sai / meta_des * 100) if meta_des > 0 else 0
        pct_res = (saldo_mes / meta_res * 100) if meta_res > 0 else 0

        m, a = state["mes"], state["ano"]
        dias_restantes = max(0, monthrange(a, m)[1] - hoje.day) if (m == hoje.month and a == hoje.year) else 0

        def card_meta(titulo, valor, meta, pct, cor_bg, icone):
            pct_str  = fmt_pct(pct) if meta > 0 else "Sem meta"
            cor_pct  = ft.colors.GREEN_100 if pct <= 100 else ft.colors.RED_100
            cor_ptxt = ft.colors.GREEN_800 if pct <= 100 else ft.colors.RED_800
            return ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(titulo, size=11, weight="bold", color=ft.colors.WHITE),
                        ft.Icon(icone, size=16, color=ft.colors.WHITE),
                    ], alignment="spaceBetween"),
                    ft.Text(fmt(valor), size=20, weight="bold", color=ft.colors.WHITE),
                    ft.Row([
                        ft.Text("Meta:", size=10, color=ft.colors.WHITE70),
                        ft.Text(fmt(meta) if meta > 0 else "—", size=10, color=ft.colors.WHITE),
                    ], spacing=4),
                    ft.Container(
                        content=ft.Text(pct_str, size=12, weight="bold", color=cor_ptxt),
                        bgcolor=cor_pct, border_radius=6,
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                    ),
                    ft.ProgressBar(
                        value=min(pct / 100, 1.0) if meta > 0 else 0,
                        color=ft.colors.WHITE, bgcolor=ft.colors.WHITE24, height=6,
                    ),
                ], spacing=6),
                padding=16, bgcolor=cor_bg, border_radius=12, width=210,
                shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26),
            )

        cards_topo.controls = [
            card_meta("RECEITAS", ent, meta_rec, pct_rec, "#2E7D32", ft.icons.ARROW_UPWARD),
            card_meta("DESPESAS", sai, meta_des, pct_des, "#C62828", ft.icons.ARROW_DOWNWARD),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("RESULTADO MÊS", size=11, weight="bold", color=ft.colors.WHITE),
                        ft.Icon(ft.icons.ACCOUNT_BALANCE_WALLET, size=16, color=ft.colors.WHITE),
                    ], alignment="spaceBetween"),
                    ft.Text(fmt(saldo_mes), size=20, weight="bold", color=ft.colors.WHITE),
                    ft.Row([
                        ft.Text("Meta:", size=10, color=ft.colors.WHITE70),
                        ft.Text(fmt(meta_res) if meta_res > 0 else "—", size=10, color=ft.colors.WHITE),
                    ], spacing=4),
                    ft.Container(
                        content=ft.Text(
                            fmt_pct(pct_res) if meta_res > 0 else "Sem meta",
                            size=12, weight="bold",
                            color=ft.colors.GREEN_800 if pct_res >= 100 else ft.colors.ORANGE_800,
                        ),
                        bgcolor=ft.colors.GREEN_100 if pct_res >= 100 else ft.colors.ORANGE_100,
                        border_radius=6,
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                    ),
                    ft.ProgressBar(
                        value=min(pct_res / 100, 1.0) if meta_res > 0 else 0,
                        color=ft.colors.WHITE, bgcolor=ft.colors.WHITE24, height=6,
                    ),
                ], spacing=6),
                padding=16,
                bgcolor="#1565C0" if saldo_mes >= 0 else "#B71C1C",
                border_radius=12, width=210,
                shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26),
            ),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("SALDO ACUMULADO", size=11, weight="bold", color=ft.colors.WHITE),
                        ft.Icon(ft.icons.SAVINGS, size=16, color=ft.colors.WHITE),
                    ], alignment="spaceBetween"),
                    ft.Text(fmt(saldo_acumulado), size=20, weight="bold", color=ft.colors.WHITE),
                    ft.Text("saldo anterior + mês", size=10, color=ft.colors.WHITE70),
                    ft.Text(f"Anterior: {fmt(saldo_anterior)}", size=10, color=ft.colors.WHITE70),
                ], spacing=6),
                padding=16,
                bgcolor="#4527A0" if saldo_acumulado >= 0 else "#B71C1C",
                border_radius=12, width=210,
                shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26),
            ),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("💳 CARTÃO", size=11, weight="bold", color=ft.colors.WHITE),
                        ft.Icon(ft.icons.CREDIT_CARD, size=16, color=ft.colors.WHITE),
                    ], alignment="spaceBetween"),
                    ft.Text(fmt(total_cartao), size=20, weight="bold", color=ft.colors.WHITE),
                    ft.Text("total no mês", size=10, color=ft.colors.WHITE70),
                    ft.ProgressBar(
                        value=min(total_cartao / sai, 1.0) if sai > 0 else 0,
                        color=ft.colors.WHITE, bgcolor=ft.colors.WHITE24, height=6,
                    ),
                    ft.Text(
                        fmt_pct(total_cartao / sai * 100) + " das despesas" if sai > 0 else "—",
                        size=10, color=ft.colors.WHITE70,
                    ),
                ], spacing=6),
                padding=16, bgcolor="#F57F17", border_radius=12, width=210,
                shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26),
            ),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("📅 DIAS REST.", size=11, weight="bold", color=ft.colors.WHITE),
                        ft.Icon(ft.icons.CALENDAR_TODAY, size=16, color=ft.colors.WHITE),
                    ], alignment="spaceBetween"),
                    ft.Text(
                        str(dias_restantes) if (m == hoje.month and a == hoje.year) else "—",
                        size=28, weight="bold", color=ft.colors.WHITE,
                    ),
                    ft.Text("dias no mês", size=10, color=ft.colors.WHITE70),
                    ft.Text(
                        f"⚠️ {fixas_pendentes} fixas pendentes", size=11,
                        color=ft.colors.YELLOW if fixas_pendentes > 0 else ft.colors.WHITE70,
                        weight="bold" if fixas_pendentes > 0 else "normal",
                    ),
                ], spacing=6),
                padding=16, bgcolor="#00838F", border_radius=12, width=210,
                shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26),
            ),
        ]

        CORES_BANCO = ["#0277BD", "#00695C", "#4E342E", "#AD1457", "#EF6C00", "#37474F"]
        total_bancos = sum(float(b["saldo_inicial"] or 0) for b in bancos_rows) if bancos_rows else 0.0
        cards_banco_lista = []
        for i, b in enumerate(bancos_rows):
            saldo_b  = float(b["saldo_inicial"] or 0)
            cor_card = CORES_BANCO[i % len(CORES_BANCO)] if saldo_b >= 0 else "#B71C1C"
            cards_banco_lista.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("🏦 " + b["nome_banco"], size=11, weight="bold", color=ft.colors.WHITE),
                        ft.Icon(ft.icons.ACCOUNT_BALANCE, size=16, color=ft.colors.WHITE),
                    ], alignment="spaceBetween"),
                    ft.Text(fmt(saldo_b), size=20, weight="bold", color=ft.colors.WHITE),
                    ft.Text("saldo atual", size=10, color=ft.colors.WHITE70),
                ], spacing=6),
                padding=16, bgcolor=cor_card, border_radius=12, width=210,
                shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26),
            ))
        cards_banco_lista.append(ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("💰 TOTAL BANCOS", size=11, weight="bold", color=ft.colors.WHITE),
                    ft.Icon(ft.icons.SAVINGS, size=16, color=ft.colors.WHITE),
                ], alignment="spaceBetween"),
                ft.Text(fmt(total_bancos), size=20, weight="bold", color=ft.colors.WHITE),
                ft.Text("consolidado", size=10, color=ft.colors.WHITE70),
                ft.Text(f"{len(bancos_rows)} banco(s) cadastrado(s)", size=10, color=ft.colors.WHITE70),
            ], spacing=6),
            padding=16,
            bgcolor="#1B5E20" if total_bancos >= 0 else "#B71C1C",
            border_radius=12, width=210,
            shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26),
        ))
        bancos_container.controls = cards_banco_lista if bancos_rows else [
            ft.Text("Nenhum banco cadastrado.", color="grey", size=12, italic=True)
        ]

        hist = defaultdict(lambda: {"Receita": 0.0, "Despesa": 0.0})
        for r in hist_rows:
            hist[r["mes"]][r["tipo"]] = float(r["total"] or 0)
        meses_hist = sorted(hist.keys())[-6:]

        if meses_hist:
            max_val    = max(max(hist[m]["Receita"] for m in meses_hist), max(hist[m]["Despesa"] for m in meses_hist), 1)
            bar_height = 180
            bar_width  = 38
            barras = []
            for mes_h in meses_hist:
                rec_h = hist[mes_h]["Receita"]
                des_h = hist[mes_h]["Despesa"]
                h_rec = int(rec_h / max_val * bar_height)
                h_des = int(des_h / max_val * bar_height)
                barras.append(ft.Column([
                    ft.Row([
                        ft.Column([
                            ft.Text(f"R${rec_h/1000:.1f}k" if rec_h >= 1000 else fmt(rec_h), size=8, color="#2E7D32", text_align="center", width=bar_width),
                            ft.Container(width=bar_width, height=max(h_rec, 3), bgcolor="#2E7D32", border_radius=ft.border_radius.only(top_left=4, top_right=4), tooltip=f"Receita: {fmt(rec_h)}"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                        ft.Column([
                            ft.Text(f"R${des_h/1000:.1f}k" if des_h >= 1000 else fmt(des_h), size=8, color="#C62828", text_align="center", width=bar_width),
                            ft.Container(width=bar_width, height=max(h_des, 3), bgcolor="#C62828", border_radius=ft.border_radius.only(top_left=4, top_right=4), tooltip=f"Despesa: {fmt(des_h)}"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                    ], spacing=4, alignment=ft.MainAxisAlignment.END),
                    ft.Text(mes_h, size=10, color="grey", text_align="center", width=bar_width * 2 + 4),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4))

            grafico_barras_col.controls = [
                ft.Row([
                    ft.Container(width=14, height=14, bgcolor="#2E7D32", border_radius=4),
                    ft.Text("Receita", size=12),
                    ft.Container(width=14, height=14, bgcolor="#C62828", border_radius=4),
                    ft.Text("Despesa", size=12),
                ], spacing=8),
                ft.Divider(height=4, color="transparent"),
                ft.Row(controls=barras, alignment=ft.MainAxisAlignment.SPACE_EVENLY, vertical_alignment=ft.CrossAxisAlignment.END),
            ]
        else:
            grafico_barras_col.controls = [ft.Text("Sem dados históricos.", color="grey", size=12)]

        detalhes_col.controls = []
        for g in gastos:
            pct_g = (float(g["total"] or 0) / sai * 100) if sai > 0 else 0
            detalhes_col.controls.append(ft.Column([
                ft.Row([
                    ft.Text(g["nome_exib"], size=11, expand=True),
                    ft.Text(fmt(float(g["total"] or 0)), size=11, weight="bold", color="red"),
                    ft.Text(fmt_pct(pct_g), size=10, color="grey"),
                ], alignment="spaceBetween"),
                ft.ProgressBar(value=pct_g / 100, color="#C62828", bgcolor="#EEE", height=5),
            ], spacing=2))
        if not detalhes_col.controls:
            detalhes_col.controls = [ft.Text("Nenhum gasto neste mês.", color="grey")]

        if not gastos or sai == 0:
            pizza_container.controls = [ft.Text("Nenhuma despesa neste mês.", color="grey")]
        else:
            fatias  = []
            legenda = []
            for i, g in enumerate(gastos):
                val_g = float(g["total"] or 0)
                pct   = (val_g / sai * 100)
                cor   = CORES[i % len(CORES)]
                titulo = f"{pct:.0f}%" if pct >= 5 else ""
                fatias.append(ft.PieChartSection(
                    value=val_g, title=titulo,
                    title_style=ft.TextStyle(size=12, color=ft.colors.WHITE, weight=ft.FontWeight.BOLD),
                    color=cor, radius=80,
                ))
                legenda.append(ft.Row([
                    ft.Container(width=12, height=12, bgcolor=cor, border_radius=3),
                    ft.Text(g["nome_exib"], size=11, expand=True),
                    ft.Text(fmt(val_g), size=11, weight="bold"),
                    ft.Text(fmt_pct(pct), size=10, color="grey"),
                ], spacing=6))
            pizza_container.controls = [
                ft.Row([
                    ft.PieChart(sections=fatias, sections_space=2, center_space_radius=45, expand=False, width=220, height=220),
                    ft.Column(controls=legenda, scroll=ft.ScrollMode.AUTO, height=220, spacing=6, expand=True),
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            ]

        if not orcamentos:
            orcamento_container.controls = [ft.Text("Nenhum orçamento definido.", color="grey", size=12, italic=True)]
        else:
            itens = []
            for o in orcamentos:
                orc_val  = float(o["orc_val"] or 0)
                gasto_o  = float(o["gasto"]   or 0)
                pct_o    = (gasto_o / orc_val * 100) if orc_val > 0 else 0
                restante = orc_val - gasto_o
                if pct_o >= 100:
                    cor_b = "red";    ico = "🚨"; cor_m = ft.colors.RED_700
                    msg_o = f"Ultrapassado {fmt(abs(restante))}"
                elif pct_o >= 80:
                    cor_b = "orange"; ico = "⚠️"; cor_m = ft.colors.ORANGE_700
                    msg_o = f"Restam {fmt(restante)}"
                else:
                    cor_b = "green";  ico = "✅"; cor_m = ft.colors.GREEN_700
                    msg_o = f"Restam {fmt(restante)}"
                itens.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"{ico} {o['nome_exib']}", size=11, weight="bold", expand=True),
                            ft.Text(f"{fmt(gasto_o)}/{fmt(orc_val)}", size=10, color="grey"),
                            ft.Text(fmt_pct(pct_o), size=11, weight="bold", color=cor_m),
                        ], alignment="spaceBetween"),
                        ft.ProgressBar(value=min(pct_o / 100, 1.0), color=cor_b, height=8),
                        ft.Text(msg_o, size=10, color=cor_m),
                    ], spacing=3),
                    padding=ft.padding.symmetric(vertical=5, horizontal=10),
                    border=ft.border.all(1, "#EEE"), border_radius=8,
                ))
            orcamento_container.controls = itens

        dados = defaultdict(dict)
        meses_set = set()
        for row in comp_rows:
            dados[row["nome_exib"]][row["mes"]] = float(row["total"] or 0)
            meses_set.add(row["mes"])
        meses_exib = list(reversed(sorted(meses_set, reverse=True)[:6]))

        if not meses_exib or not dados:
            comparativo_container.controls = [ft.Text("Sem dados.", color="grey")]
        else:
            colunas = [ft.DataColumn(ft.Text("Conta", weight="bold", size=11))]
            for mc in meses_exib:
                colunas.append(ft.DataColumn(ft.Text(mc, weight="bold", size=11)))
            linhas = []
            for nome in sorted(dados.keys()):
                cells = [ft.DataCell(ft.Text(nome, size=11))]
                for idx, mc in enumerate(meses_exib):
                    valor = dados[nome].get(mc)
                    if valor:
                        mes_ant   = meses_exib[idx - 1] if idx > 0 else None
                        valor_ant = dados[nome].get(mes_ant, 0) if mes_ant else 0
                        cor = ft.colors.RED_700 if valor > valor_ant and mes_ant else ft.colors.GREEN_700
                        cells.append(ft.DataCell(ft.Text(fmt(valor), color=cor, weight="bold", size=11)))
                    else:
                        cells.append(ft.DataCell(ft.Text("-", color=ft.colors.GREY_400, size=11)))
                linhas.append(ft.DataRow(cells=cells))
            comparativo_container.controls = [
                ft.Row(controls=[ft.DataTable(columns=colunas, rows=linhas)], scroll=ft.ScrollMode.ALWAYS)
            ]

        metas_container.controls = [
            ft.Row([
                meta_rec_field, meta_des_field, meta_res_field,
                ft.ElevatedButton("SALVAR METAS", icon=ft.icons.SAVE, bgcolor="#1565C0", color=ft.colors.WHITE, on_click=salvar_meta),
            ], spacing=10, wrap=True),
            msg_meta,
        ]

        page.update()

    dd_mes = ft.Dropdown(
        label="Mês", width=160, value=get_mes_str(),
        options=get_meses_opcoes(),
        on_change=lambda e: (
            state.update({"mes": int(e.control.value.split("/")[0]), "ano": int(e.control.value.split("/")[1])}),
            carregar(e.control.value),
            page.update()
        )
    )

    carregar(get_mes_str())

    def secao(titulo, subtitulo, conteudo, cor_titulo="blue"):
        return ft.Container(
            content=ft.Column([
                ft.Text(titulo, weight="bold", size=14, color=cor_titulo),
                ft.Text(subtitulo, size=11, color="grey") if subtitulo else ft.Container(),
                ft.Divider(height=6),
                conteudo,
            ], spacing=6),
            padding=16,
            border=ft.border.all(1, "#E0E0E0"),
            border_radius=12,
            bgcolor=ft.colors.WHITE,
            shadow=ft.BoxShadow(blur_radius=4, color=ft.colors.BLACK12),
        )

    return ft.View(
        route="/",
        bgcolor="#F5F6FA",
        controls=[
            get_menu(page),
            ft.Divider(height=4, color="transparent"),
            ft.Container(
                padding=ft.padding.symmetric(horizontal=20, vertical=8),
                expand=True,
                content=ft.Column([
                    ft.Row([
                        ft.Text("DASHBOARD FINANCEIRO", size=22, weight="bold", color="#1565C0"),
                        ft.Row([ft.Text("Período:", size=12, color="grey"), dd_mes], spacing=8),
                    ], alignment="start", spacing=20),
                    ft.Divider(height=8, color="transparent"),
                    cards_topo,
                    ft.Divider(height=4, color="transparent"),
                    bancos_container,
                    ft.Divider(height=8, color="transparent"),
                    ft.Row([
                        ft.Container(content=secao("📊 RECEITAS VS DESPESAS", "Histórico dos últimos 6 meses", grafico_barras_col), expand=3),
                        ft.Container(content=secao("💸 GASTOS POR CONTA", "Distribuição do mês atual", detalhes_col), expand=2),
                    ], spacing=12),
                    ft.Divider(height=8, color="transparent"),
                    ft.Row([
                        ft.Container(content=secao("🍕 DESPESAS POR CATEGORIA", "Distribuição percentual", pizza_container), expand=1),
                        ft.Container(content=secao("🎯 ORÇAMENTO MENSAL", "✅ ok  ⚠️ acima de 80%  🚨 ultrapassado", orcamento_container), expand=1),
                    ], spacing=12),
                    ft.Divider(height=8, color="transparent"),
                    secao("🎯 DEFINIR METAS DO MÊS", "Configure as metas de receita, despesa e resultado", metas_container),
                    ft.Divider(height=8, color="transparent"),
                    secao("📅 COMPARATIVO MENSAL", "🟢 diminuiu  🔴 aumentou em relação ao mês anterior", comparativo_container),
                    ft.Divider(height=8, color="transparent"),
                ], scroll=ft.ScrollMode.ALWAYS, expand=True)
            )
        ]
    )