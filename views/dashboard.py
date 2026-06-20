import flet as ft
from datetime import datetime
from calendar import monthrange
from collections import defaultdict

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

    # ── Containers ──────────────────────────────────────────────────────────
    alertas_row       = ft.Row(spacing=8, wrap=True, run_spacing=8)
    resumo_row        = ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.START)
    bancos_container  = ft.Row(spacing=10, wrap=True, run_spacing=10)
    mes_atual_col     = ft.Column(spacing=8)
    top_gastos_col    = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)
    orcamento_col     = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
    comparativo_col   = ft.Column(spacing=6)
    metas_container   = ft.Column(spacing=6)
    fixas_container   = ft.Column(spacing=6)

    meta_rec_field = ft.TextField(label="Meta Receita",   width=160, on_blur=formatar_moeda_input, dense=True)
    meta_des_field = ft.TextField(label="Meta Despesa",   width=160, on_blur=formatar_moeda_input, dense=True)
    meta_res_field = ft.TextField(label="Meta Resultado", width=160, on_blur=formatar_moeda_input, dense=True)
    msg_meta = ft.Text("", size=12, color=ft.colors.GREEN_700)

    # ── COMPARATIVO ─────────────────────────────────────────────────────────
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

    comp_ini_dd = ft.Dropdown(label="De", width=130, value=f"{m_ini:02d}/{a_ini}", options=get_meses_comp(), dense=True)
    comp_fim_dd = ft.Dropdown(label="Até", width=130, value=get_mes_str(), options=get_meses_comp(), dense=True)
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
                return ft.DataCell(ft.Text(fmt(val), color="#1565C0", size=11))

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
                ft.Row([
                    ft.DataTable(
                        columns=cols_c, rows=rows_c,
                        border=ft.border.all(1, "#E0E0E0"),
                        border_radius=8,
                        horizontal_lines=ft.border.BorderSide(1, "#F0F0F0"),
                    ),
                ], scroll=ft.ScrollMode.AUTO),
            ]
            msg_comp.value = f"Exibindo {len(meses_ord)} mês(es) com dados."
        except Exception as ex:
            import traceback
            print(f"[dashboard] comparativo erro: {ex}")
            traceback.print_exc()
            comparativo_col.controls = [ft.Text("Erro ao carregar comparativo.", color="red", size=12)]
        page.update()

    def filtrar_comparativo(e):
        if comp_ini_dd.value and comp_fim_dd.value:
            carregar_comparativo(comp_ini_dd.value, comp_fim_dd.value)

    comp_ini_dd.on_change = filtrar_comparativo
    comp_fim_dd.on_change = filtrar_comparativo

    # ── METAS ───────────────────────────────────────────────────────────────
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

    # ── CARREGAR PRINCIPAL ──────────────────────────────────────────────────
    def carregar(mes_str):
        try:
            with db_session() as cur:
                cur.execute("SELECT COALESCE(SUM(valor),0) as total FROM transacoes WHERE usuario_id=%s AND tipo='Receita' AND data LIKE %s", (uid, f"%%/{mes_str}"))
                ent = float(cur.fetchone()['total'] or 0)
                cur.execute("SELECT COALESCE(SUM(valor),0) as total FROM transacoes WHERE usuario_id=%s AND tipo='Despesa' AND data LIKE %s", (uid, f"%%/{mes_str}"))
                sai = float(cur.fetchone()['total'] or 0)
                saldo_mes       = ent - sai
                saldo_acumulado = calcular_saldo_acumulado(mes_str)

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

                cur.execute("""
                    SELECT COALESCE(SUM(t.valor),0) as total FROM transacoes t
                    JOIN subcontas s ON t.subconta_id=s.id
                    WHERE t.usuario_id=%s AND t.tipo='Despesa' AND t.data LIKE %s
                    AND (s.nome ILIKE '%%CARTAO%%' OR s.nome ILIKE '%%CARTÃO%%')
                """, (uid, f"%%/{mes_str}"))
                total_cartao = float(cur.fetchone()['total'] or 0)

                cur.execute("SELECT COUNT(*) as total FROM subcontas s WHERE s.fixa=1 AND s.usuario_id=%s AND s.id NOT IN (SELECT subconta_id FROM transacoes WHERE data LIKE %s AND usuario_id=%s)", (uid, f"%%/{mes_str}", uid))
                fixas_pendentes = int(cur.fetchone()['total'] or 0)

                cur.execute("SELECT COUNT(*) as total FROM subcontas s WHERE s.fixa=1 AND s.usuario_id=%s", (uid,))
                total_fixas = int(cur.fetchone()['total'] or 0)

                # Valor das despesas fixas no mês
                cur.execute("""
                    SELECT COALESCE(SUM(t.valor),0) as total FROM transacoes t
                    JOIN subcontas s ON t.subconta_id=s.id
                    WHERE t.usuario_id=%s AND t.tipo='Despesa' AND s.fixa=1 AND t.data LIKE %s
                """, (uid, f"%%/{mes_str}"))
                fixas_valor = float(cur.fetchone()['total'] or 0)

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

                # Mês anterior — tendências
                mes_ant = mes_anterior_str(mes_str)
                cur.execute("SELECT COALESCE(SUM(valor),0) as total FROM transacoes WHERE usuario_id=%s AND tipo='Receita' AND data LIKE %s", (uid, f"%%/{mes_ant}"))
                ent_ant = float(cur.fetchone()['total'] or 0)
                cur.execute("SELECT COALESCE(SUM(valor),0) as total FROM transacoes WHERE usuario_id=%s AND tipo='Despesa' AND data LIKE %s", (uid, f"%%/{mes_ant}"))
                sai_ant = float(cur.fetchone()['total'] or 0)
                saldo_ant = ent_ant - sai_ant

                cur.execute("""
                    SELECT COALESCE(SUM(t.valor),0) as total FROM transacoes t
                    JOIN subcontas s ON t.subconta_id=s.id
                    WHERE t.usuario_id=%s AND t.tipo='Despesa' AND s.fixa=1 AND t.data LIKE %s
                """, (uid, f"%%/{mes_ant}"))
                fixas_valor_ant = float(cur.fetchone()['total'] or 0)

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
        pct_fixas_desp = (fixas_valor / sai * 100) if sai > 0 else 0

        # ── SCORE DE SAÚDE ───────────────────────────────────────────────────
        _sp = max(0, min(100, int(saldo_mes / ent * 100))) if ent > 0 else 0
        _so = int(sum(1 for o in orcamentos if float(o['total']) <= float(o['orcamento'])) / max(len(orcamentos), 1) * 100) if orcamentos else 100
        _sf = max(0, int((total_fixas - fixas_pendentes) / total_fixas * 100)) if total_fixas > 0 else 100
        _sc = max(0, 100 - int(sai / ent * 100)) if ent > 0 else 0
        score_final = int(_sp * 0.35 + _so * 0.25 + _sf * 0.25 + _sc * 0.15)
        if score_final >= 70:
            cor_sc, lbl_sc, bg_sc = "#2E7D32", "BOA", "#E8F5E9"
        elif score_final >= 40:
            cor_sc, lbl_sc, bg_sc = "#F57F17", "REGULAR", "#FFF8E1"
        else:
            cor_sc, lbl_sc, bg_sc = "#C62828", "ATENÇÃO", "#FFEBEE"

        def tend_txt(atual, anterior):
            if anterior == 0:
                return ""
            diff = ((atual - anterior) / anterior) * 100
            sinal = "▲" if diff > 0 else "▼"
            return f"{sinal} {abs(diff):.1f}% vs mês anterior"

        # ── LINHA 1: RESUMO (Receitas, Despesas, Resultado, Saúde) ───────────
        def big_card(titulo, valor, cor, tend, meta_txt, pct, has_meta):
            children = [
                ft.Text(titulo, size=11, color="#1565C0", weight="bold"),
                ft.Text(fmt(valor), size=24, weight="bold", color=cor),
            ]
            if tend:
                children.append(ft.Text(tend, size=10, color="#888888"))
            if has_meta:
                children.append(ft.Text(meta_txt, size=10, color="#888888"))
                children.append(ft.ProgressBar(value=min(pct / 100, 1.0), color=cor, bgcolor="#F0F0F0", height=4, border_radius=2))
            else:
                children.append(ft.Container(
                    content=ft.Text("Sem meta definida", size=9, color="#AAAAAA", italic=True),
                ))
            return ft.Container(
                expand=1, height=128, padding=14, bgcolor="white", border_radius=12,
                border=ft.border.only(left=ft.BorderSide(4, cor)),
                shadow=ft.BoxShadow(blur_radius=4, color="#00000010"),
                content=ft.Column(children, spacing=4),
            )

        if saldo_mes >= 0:
            res_msg = f"✅ Sobrou {fmt(saldo_mes)} este mês"
            res_cor = "#2E7D32"
        else:
            res_msg = f"❌ Gastou {fmt(abs(saldo_mes))} a mais do que recebeu"
            res_cor = "#C62828"

        # Valores para o card "Despesas fixas" do resumo
        pagas_pre = total_fixas - fixas_pendentes
        fixas_valor_pre = fixas_valor
        pct_fixas_desp_pre = pct_fixas_desp
        tend_txt_pre = tend_txt(fixas_valor, fixas_valor_ant)
        if fixas_pendentes > 0:
            status_fixas_txt_pre = f"⚠ {fixas_pendentes} pendente(s) — {pagas_pre} de {total_fixas} lançadas"
            status_fixas_cor_pre = "#C62828"
        else:
            status_fixas_txt_pre = f"✅ todas lançadas ({total_fixas}/{total_fixas})"
            status_fixas_cor_pre = "#2E7D32"

        # ── FAIXA DE ALERTAS / INSIGHTS ───────────────────────────────────────
        def chip(icone, texto, cor, bg):
            return ft.Container(
                bgcolor=bg, border_radius=20, padding=ft.padding.symmetric(horizontal=12, vertical=6),
                content=ft.Text(f"{icone} {texto}", size=11, weight="bold", color=cor),
            )

        orc_ultrapassados = sum(1 for o in orcamentos if float(o['total']) > float(o['orcamento'])) if orcamentos else 0
        orc_atencao = sum(
            1 for o in orcamentos
            if float(o['orcamento']) > 0 and 80 <= (float(o['total']) / float(o['orcamento']) * 100) < 100
        ) if orcamentos else 0

        chips = []

        # Orçamento
        if orc_ultrapassados > 0:
            chips.append(chip("🔴", f"{orc_ultrapassados} categoria(s) ultrapassaram o orçamento", "#C62828", "#FFEBEE"))
        elif orc_atencao > 0:
            chips.append(chip("🟡", f"{orc_atencao} categoria(s) próxima(s) do limite", "#F57F17", "#FFF8E1"))
        else:
            chips.append(chip("✅", "Orçamento sob controle", "#2E7D32", "#E8F5E9"))

        # Contas fixas
        if fixas_pendentes > 0:
            chips.append(chip("📌", f"{fixas_pendentes} conta(s) fixa(s) pendente(s)", "#C62828", "#FFEBEE"))
        else:
            chips.append(chip("📌", "Todas as contas fixas lançadas", "#2E7D32", "#E8F5E9"))

        # Dias restantes (apenas mês atual)
        if m == hoje.month and a == hoje.year:
            chips.append(chip("📅", f"{dias_restantes} dia(s) restante(s) no mês", "#1565C0", "#E3F2FD"))

        # Cartão de crédito
        if total_cartao > 0:
            chips.append(chip("💳", f"Cartão: {fmt(total_cartao)} ({pct_cartao:.0f}% das despesas)", "#1565C0", "#E3F2FD"))

        # Saldo acumulado total
        cor_acum = "#2E7D32" if saldo_acumulado >= 0 else "#C62828"
        bg_acum  = "#E8F5E9" if saldo_acumulado >= 0 else "#FFEBEE"
        chips.append(chip("🏦", f"Saldo total em contas: {fmt(saldo_acumulado)}", cor_acum, bg_acum))

        # Projeção de fechamento do mês (apenas mês atual)
        if m == hoje.month and a == hoje.year and hoje.day > 0:
            dias_no_mes = monthrange(a, m)[1]
            ritmo = sai / hoje.day
            projecao = ritmo * dias_no_mes
            if meta_des > 0:
                if projecao > meta_des:
                    chips.append(chip("📈", f"Projeção: {fmt(projecao)} — acima da meta ({fmt(meta_des)})", "#C62828", "#FFEBEE"))
                else:
                    chips.append(chip("📈", f"Projeção: {fmt(projecao)} — dentro da meta", "#2E7D32", "#E8F5E9"))
            else:
                chips.append(chip("📈", f"Projeção de gastos até o fim do mês: {fmt(projecao)}", "#1565C0", "#E3F2FD"))

        alertas_row.controls = chips

        resumo_row.controls = [
            big_card("RECEITAS DO MÊS", ent, "#2E7D32",
                     tend_txt(ent, ent_ant),
                     f"Meta: {fmt(meta_rec)} ({fmt_pct(pct_rec)})", pct_rec, meta_rec > 0),
            big_card("DESPESAS DO MÊS", sai, "#C62828",
                     tend_txt(sai, sai_ant),
                     f"Meta: {fmt(meta_des)} ({fmt_pct(pct_des)})", pct_des, meta_des > 0),
            ft.Container(
                expand=1, height=128, padding=14, bgcolor="white", border_radius=12,
                border=ft.border.only(left=ft.BorderSide(4, res_cor)),
                shadow=ft.BoxShadow(blur_radius=4, color="#00000010"),
                content=ft.Column([
                    ft.Text("RESULTADO", size=11, color="#1565C0", weight="bold"),
                    ft.Text(fmt(saldo_mes), size=24, weight="bold", color=res_cor),
                    ft.Container(
                        bgcolor="#FFEBEE" if saldo_mes < 0 else "#E8F5E9",
                        border_radius=5, padding=ft.padding.symmetric(horizontal=8, vertical=3),
                        content=ft.Text(res_msg, size=10, color=res_cor, weight="bold"),
                    ),
                    ft.Text(f"Meta: {fmt(meta_res)} ({fmt_pct(pct_res)})" if meta_res > 0 else "Sem meta definida",
                            size=10, color="#888888", italic=(meta_res == 0)),
                ], spacing=4),
            ),
            ft.Container(
                expand=1, height=128, padding=14, bgcolor="white", border_radius=12,
                border=ft.border.only(left=ft.BorderSide(4, "#1565C0")),
                shadow=ft.BoxShadow(blur_radius=4, color="#00000010"),
                content=ft.Column([
                    ft.Text("DESPESAS FIXAS", size=11, color="#1565C0", weight="bold"),
                    ft.Text(fmt(fixas_valor_pre), size=24, weight="bold", color="#1565C0"),
                    ft.Text(f"{fmt_pct(pct_fixas_desp_pre)} das despesas do mês", size=10, color="#888888"),
                    ft.Text(tend_txt_pre, size=10, color="#888888") if tend_txt_pre else ft.Container(height=0),
                    ft.Text(status_fixas_txt_pre, size=10, weight="bold", color=status_fixas_cor_pre),
                ], spacing=4),
            ),
            ft.Container(
                expand=1, height=128, padding=12, bgcolor=bg_sc, border_radius=12,
                border=ft.border.only(left=ft.BorderSide(4, cor_sc)),
                shadow=ft.BoxShadow(blur_radius=4, color="#00000010"),
                tooltip=(
                    f"Saúde Financeira: {score_final}/100\n"
                    f"💰 Poupança: {_sp}% (meta >20%)\n"
                    f"🎯 Orçamento: {_so}% (meta >70%)\n"
                    f"📌 Fixas pagas: {_sf}% (meta >80%)\n"
                    f"📊 Renda livre: {_sc}% (meta >30%)"
                ),
                content=ft.Column([
                    ft.Text("SAÚDE", size=10, color=cor_sc, weight="bold"),
                    ft.Text(str(score_final), size=36, weight="bold", color=cor_sc),
                    ft.Text(lbl_sc, size=11, weight="bold", color=cor_sc),
                    ft.Text("financeira", size=9, color="#888888"),
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   alignment=ft.MainAxisAlignment.CENTER),
            ),
        ]

        # ── BANCOS ────────────────────────────────────────────────────────────
        pw = (page.window_width or 1200) - 210
        banco_w = max(160, int((pw * 0.55) / 3) - 12)
        bancos_cards = []
        for b in bancos_rows:
            saldo_real = calcular_saldo_banco(b['id'], float(b['saldo_inicial'] or 0), mes_str)
            variacao   = saldo_real - float(b['saldo_inicial'] or 0)
            cor_var    = "#A5D6A7" if variacao >= 0 else "#EF9A9A"
            sinal      = "▲" if variacao >= 0 else "▼"
            bancos_cards.append(
                ft.Container(
                    width=banco_w, padding=12, bgcolor="#37474F", border_radius=12,
                    shadow=ft.BoxShadow(blur_radius=6, color="#00000015"),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.icons.ACCOUNT_BALANCE, color="white", size=16),
                            ft.Text(b['nome_banco'], size=11, weight="bold", color="white", expand=True),
                        ], spacing=6),
                        ft.Text(fmt(saldo_real), size=18, weight="bold", color="white"),
                        ft.Row([
                            ft.Text("Inicial:", size=9, color="white70"),
                            ft.Text(fmt(b['saldo_inicial'] or 0), size=9, color="white70"),
                            ft.Text(f"{sinal} {fmt(abs(variacao))}", size=9, color=cor_var, weight="bold"),
                        ], spacing=4),
                        ft.Text(f"Ag: {b['agencia'] or '—'} | Cta: {b['numero_conta'] or '—'}", size=9, color="white70"),
                    ], spacing=3),
                )
            )
        bancos_container.controls = bancos_cards if bancos_cards else [
            ft.Text("Nenhum banco cadastrado.", color="grey", italic=True, size=12)
        ]

        # ── METAS ─────────────────────────────────────────────────────────────
        metas_container.controls = [
            ft.Row([meta_rec_field, meta_des_field, meta_res_field,
                    ft.ElevatedButton("SALVAR", bgcolor="#1565C0", color="white", on_click=salvar_meta)],
                   spacing=8, wrap=True),
            msg_meta,
            ft.Text("💡 Copiada automaticamente do mês anterior", size=9, color="#2E7D32", italic=True),
        ]

        # ── MÊS ATUAL + HISTÓRICO ────────────────────────────────────────────
        hist = defaultdict(lambda: {"Receita": 0.0, "Despesa": 0.0})
        for r in hist_rows:
            hist[r['m']][r['tipo']] = float(r['total'] or 0)

        max_re_de = max(ent, sai, 1)

        def chave_mes(mm):
            mes_n, ano_n = mm.split("/")
            return (int(ano_n), int(mes_n))

        meses_hist = sorted(hist.keys(), key=chave_mes)
        # Últimos 4 meses ANTES do mês atual (sem repetir o atual), em ordem cronológica
        meses_anteriores = [mm for mm in meses_hist if chave_mes(mm) < chave_mes(mes_str)][-4:]
        max_hist = max(
            [max(hist[mm]['Receita'], hist[mm]['Despesa']) for mm in (meses_anteriores + [mes_str])],
            default=1
        )
        HIST_BAR_MAX = 260

        mes_atual_col.controls = [
            ft.Container(
                bgcolor="#FFEBEE" if saldo_mes < 0 else "#E8F5E9",
                border_radius=6, padding=8,
                content=ft.Text(res_msg, size=12, weight="bold", color=res_cor),
            ),
            ft.Row([
                ft.Text("Receita", size=11, color="#2E7D32", weight="bold", width=60),
                ft.Container(
                    expand=True,
                    content=ft.ProgressBar(value=ent / max_re_de, color="#2E7D32", bgcolor="#F0F4FA", height=26, border_radius=4),
                ),
                ft.Text(fmt(ent), size=11, weight="bold", color="#2E7D32", width=90, text_align=ft.TextAlign.RIGHT),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([
                ft.Text("Despesa", size=11, color="#C62828", weight="bold", width=60),
                ft.Container(
                    expand=True,
                    content=ft.ProgressBar(value=sai / max_re_de, color="#C62828", bgcolor="#F0F4FA", height=26, border_radius=4),
                ),
                ft.Text(fmt(sai), size=11, weight="bold", color="#C62828", width=90, text_align=ft.TextAlign.RIGHT),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(height=8, color="#E8EEF7"),
            ft.Text("Histórico dos últimos meses", size=10, color="#888888"),
        ]

        for mm in meses_anteriores:
            saldo_mm = hist[mm]['Receita'] - hist[mm]['Despesa']
            cor_mm = "#2E7D32" if saldo_mm >= 0 else "#C62828"
            sinal_mm = "+" if saldo_mm >= 0 else "-"
            mes_atual_col.controls.append(
                ft.Row([
                    ft.Text(mm, size=10, color="#1565C0", weight="bold", width=48),
                    ft.Column([
                        ft.Container(height=11, width=max(4, int(hist[mm]['Receita'] / max_hist * HIST_BAR_MAX)), bgcolor="#2E7D32", border_radius=2),
                        ft.Container(height=11, width=max(4, int(hist[mm]['Despesa'] / max_hist * HIST_BAR_MAX)), bgcolor="#C62828", border_radius=2),
                    ], spacing=2, expand=True),
                    ft.Text(f"{sinal_mm}{fmt(abs(saldo_mm))}", size=10, weight="bold", color=cor_mm, width=72, text_align=ft.TextAlign.RIGHT),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            )

        # Mês atual destacado no histórico
        mes_atual_col.controls.append(
            ft.Container(
                bgcolor="#EEF4FF", border_radius=5, padding=ft.padding.symmetric(horizontal=4, vertical=3),
                content=ft.Row([
                    ft.Text(f"{mes_str} ◀", size=10, color="#1565C0", weight="bold", width=48),
                    ft.Column([
                        ft.Container(height=11, width=max(4, int(ent / max_hist * HIST_BAR_MAX)), bgcolor="#2E7D32", border_radius=2),
                        ft.Container(height=11, width=max(4, int(sai / max_hist * HIST_BAR_MAX)), bgcolor="#C62828", border_radius=2),
                    ], spacing=2, expand=True),
                    ft.Text(f"{'+' if saldo_mes>=0 else '-'}{fmt(abs(saldo_mes))}", size=10, weight="bold", color=res_cor, width=72, text_align=ft.TextAlign.RIGHT),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            )
        )

        # ── TOP GASTOS ────────────────────────────────────────────────────────
        max_gasto = float(gastos[0]['total']) if gastos else 1
        top_gastos_col.controls = [
            ft.Container(
                padding=ft.padding.symmetric(vertical=4),
                border=ft.border.only(bottom=ft.BorderSide(0.5, "#F0F4FA")),
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            width=20, height=20, border_radius=10, bgcolor="#E3F2FD",
                            alignment=ft.alignment.center,
                            content=ft.Text(str(i + 1), size=10, weight="bold", color="#1565C0"),
                        ),
                        ft.Container(
                            width=240,
                            content=ft.Text(g['nome'], size=11, color="#333333",
                                             overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                        ),
                        ft.Text(fmt(g['total']), size=11, weight="bold", color="#C62828", width=80, text_align=ft.TextAlign.RIGHT),
                        ft.Text(f"{g['total']/sai*100:.1f}%" if sai > 0 else "0%", size=10, color="#888888", width=36, text_align=ft.TextAlign.RIGHT),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(
                        padding=ft.padding.only(left=28),
                        content=ft.ProgressBar(
                            value=float(g['total']) / max_gasto if max_gasto > 0 else 0,
                            color="#C62828", bgcolor="#F0F4FA", height=5, border_radius=3,
                        ),
                    ),
                ], spacing=3),
            )
            for i, g in enumerate(gastos[:10])
        ] if gastos else [ft.Text("Sem despesas no período.", color="grey", italic=True)]

        # ── ORÇAMENTO — ALERTAS EM GRID ───────────────────────────────────────
        def badge_orc(pct):
            if pct >= 100:  return ("🔴", "#FFEBEE", "#C62828", "#FFCDD2")
            elif pct >= 80: return ("🟡", "#FFF8E1", "#F57F17", "#FFE082")
            else:           return ("✅", "#E8F5E9", "#2E7D32", "#C8E6C9")

        if orcamentos:
            orc_ordenados = sorted(
                orcamentos,
                key=lambda o: (float(o['total']) / float(o['orcamento'])) if float(o['orcamento']) > 0 else 0,
                reverse=True,
            )

            def orc_card(o):
                pct = (float(o['total']) / float(o['orcamento']) * 100) if float(o['orcamento']) > 0 else 0
                icone, bg, cor, bg_bar = badge_orc(pct)
                if o['total'] > o['orcamento']:
                    sub = f"Ultrapass. {fmt(abs(o['orcamento'] - o['total']))}"
                else:
                    sub = f"Restam {fmt(abs(o['orcamento'] - o['total']))}"
                return ft.Container(
                    expand=1, bgcolor=bg, border_radius=8, padding=8,
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"{icone} {o['nome']}", size=10, weight="bold", color=cor, expand=True,
                                    overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                            ft.Text(f"{pct:.0f}%", size=10, weight="bold", color=cor),
                        ]),
                        ft.Text(f"{fmt(o['total'])} / {fmt(o['orcamento'])}", size=8, color=cor,
                                overflow=ft.TextOverflow.ELLIPSIS, max_lines=1),
                        ft.ProgressBar(value=min(o['total']/o['orcamento'], 1.0) if o['orcamento'] > 0 else 0,
                                       color=cor, bgcolor=bg_bar, height=5, border_radius=3),
                        ft.Text(sub, size=8, color=cor),
                    ], spacing=2),
                )

            ORC_POR_LINHA = 6
            linhas = []
            for i in range(0, len(orc_ordenados), ORC_POR_LINHA):
                grupo = orc_ordenados[i:i + ORC_POR_LINHA]
                while len(grupo) < ORC_POR_LINHA:
                    grupo.append(None)
                linhas.append(
                    ft.Row([
                        orc_card(o) if o else ft.Container(expand=1)
                        for o in grupo
                    ], spacing=6)
                )
            orcamento_col.controls = linhas
        else:
            orcamento_col.controls = [ft.Text("Nenhum orçamento definido.", color="grey", italic=True, size=12)]

        carregar_comparativo(comp_ini_dd.value, comp_fim_dd.value)
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
                ft.Container(
                    content=ft.Column([
                        ft.Text(titulo, weight="bold", size=13, color=cor_titulo),
                        ft.Text(subtitulo, size=10, color="#999999") if subtitulo else ft.Container(height=0),
                    ], spacing=1),
                    border=ft.border.only(bottom=ft.BorderSide(2, "#E3F2FD")),
                    padding=ft.padding.only(bottom=8),
                ),
                conteudo,
            ], spacing=8),
            padding=14,
            border=ft.border.all(1, "#E8EEF7"),
            border_radius=12,
            bgcolor="white",
            shadow=ft.BoxShadow(blur_radius=4, color="#00000010"),
        )

    comparativo_conteudo = ft.Column([
        ft.Row([
            ft.Text("Período:", size=12, color="grey"),
            comp_ini_dd,
            ft.Text("até", size=12, color="grey"),
            comp_fim_dd,
            msg_comp,
        ], spacing=10, wrap=True),
        ft.Divider(height=4, color="transparent"),
        comparativo_col,
    ], spacing=6)

    return ft.View(route="/", bgcolor="#F0F4FA", controls=[
        ft.Container(
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            expand=True,
            content=ft.Column([
                # Cabeçalho
                ft.Row([
                    ft.Column([
                        ft.Text("Dashboard financeiro", size=20, weight="bold", color="#1565C0"),
                        ft.Container(width=180, height=3, bgcolor="#2E7D32", border_radius=2),
                    ], spacing=3),
                    ft.Row([ft.Text("Período:", size=11, color="#999999"), dd_mes], spacing=6),
                ], spacing=16),
                ft.Divider(height=4, color="transparent"),

                # FAIXA DE ALERTAS / INSIGHTS
                alertas_row,
                ft.Divider(height=4, color="transparent"),

                # LINHA 1: Resumo do mês (Receitas, Despesas, Resultado, Saúde)
                resumo_row,
                ft.Divider(height=4, color="transparent"),

                # LINHA 2: Bancos + Metas (ao lado do último banco)
                ft.Row([
                    ft.Container(content=bancos_container, expand=3),
                    ft.Container(
                        content=secao("🎯 Metas do mês", "Copiada automaticamente do mês anterior", metas_container),
                        expand=2,
                    ),
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Divider(height=4, color="transparent"),

                # LINHA 3: Mês atual + histórico | Top gastos
                ft.Row([
                    ft.Container(
                        content=secao("📊 Como está o mês", "Receita vs despesa e histórico", mes_atual_col),
                        expand=1,
                    ),
                    ft.Container(
                        content=secao("💸 Onde está indo o dinheiro", "Maiores gastos do mês",
                            ft.Container(content=top_gastos_col, height=320, clip_behavior=ft.ClipBehavior.HARD_EDGE)),
                        expand=1,
                    ),
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Divider(height=4, color="transparent"),

                # LINHA 4: Orçamento — alertas
                secao("🎯 Orçamento mensal", "Alertas e categorias monitoradas", orcamento_col),
                ft.Divider(height=4, color="transparent"),

                # Comparativo
                secao("📅 Comparativo mensal", None, comparativo_conteudo),
            ], scroll=ft.ScrollMode.ALWAYS, expand=True),
        )
    ])