import flet as ft
import os
import base64
import io
import tempfile
from datetime import datetime, date as ddate
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from menu import get_menu
from database import get_connection, get_cursor
from utils import verificar_admin, formatar_moeda_input, limpar_valor


def extrato_view(page: ft.Page):
    state  = {"editing_id": None, "trans": []}
    uid    = page.session.get("user_id")
    hoje   = datetime.now()

    # ── HELPERS ───────────────────────────────────────────────────────────
    def fmt(v):
        try:
            valor = float(v)
            neg   = valor < 0
            valor = abs(valor)
            inteiro  = int(valor)
            cents    = round((valor - inteiro) * 100)
            s = str(inteiro)
            com_ponto = ""
            for i, c in enumerate(reversed(s)):
                if i > 0 and i % 3 == 0:
                    com_ponto = "." + com_ponto
                com_ponto = c + com_ponto
            return f"R$ {'-' if neg else ''}{com_ponto},{cents:02d}"
        except Exception:
            return "R$ 0,00"

    def safe(texto):
        import unicodedata
        texto = str(texto or "")
        nfd = unicodedata.normalize("NFD", texto)
        return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

    def str_to_date(s):
        s = (s or "").strip()
        if not s:
            return None
        try:
            p = s.split("/")
            return ddate(int(p[2]), int(p[1]), int(p[0]))
        except Exception:
            return None

    def parse_data(data_val):
        if isinstance(data_val, (ddate, datetime)):
            return f"{data_val.day:02d}/{data_val.month:02d}/{data_val.year}"
        s = str(data_val)
        if "-" in s and len(s) == 10 and s[4] == "-":
            p = s.split("-")
            return f"{p[2]}/{p[1]}/{p[0]}"
        return s

    def chave_mes(data_str):
        try:
            p = data_str.split("/")
            return int(p[2]) * 100 + int(p[1])
        except Exception:
            return 0

    def mes_label(data_str):
        nomes = ["Janeiro","Fevereiro","Marco","Abril","Maio","Junho",
                 "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
        try:
            p = data_str.split("/")
            return f"{nomes[int(p[1])-1]} {p[2]}"
        except Exception:
            return data_str

    # ── FILTROS ───────────────────────────────────────────────────────────
    def get_contas_opcoes():
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("SELECT DISTINCT s.nome FROM subcontas s WHERE s.usuario_id=%s ORDER BY s.nome", (uid,))
            nomes = cur.fetchall()
            conn.close()
            ops = [ft.dropdown.Option("Todas")]
            for n in nomes:
                ops.append(ft.dropdown.Option(n["nome"]))
            return ops
        except Exception:
            return [ft.dropdown.Option("Todas")]

    def aplicar_mascara(e):
        """Formata ao sair do campo: aceita 8 dígitos e monta DD/MM/AAAA."""
        tf     = e.control
        digits = "".join(c for c in (tf.value or "") if c.isdigit())[:8]
        if len(digits) == 8:
            tf.value = f"{digits[0:2]}/{digits[2:4]}/{digits[4:8]}"
        elif len(digits) > 4:
            tf.value = f"{digits[0:2]}/{digits[2:4]}/{digits[4:]}"
        elif len(digits) > 2:
            tf.value = f"{digits[0:2]}/{digits[2:]}"
        else:
            tf.value = digits
        tf.update()
        carregar_tabela()

    f_ini  = ft.TextField(label="Data Inicial", width=150, hint_text="DDMMAAAA",
                          value=f"01/{hoje.month:02d}/{hoje.year}",
                          on_blur=aplicar_mascara, keyboard_type=ft.KeyboardType.NUMBER)
    f_fim  = ft.TextField(label="Data Final",   width=150, hint_text="DDMMAAAA",
                          value=f"{hoje.day:02d}/{hoje.month:02d}/{hoje.year}",
                          on_blur=aplicar_mascara, keyboard_type=ft.KeyboardType.NUMBER)
    f_tipo = ft.Dropdown(label="Tipo", width=130, value="Todos", options=[
        ft.dropdown.Option("Todos"),
        ft.dropdown.Option("Receita"),
        ft.dropdown.Option("Despesa"),
    ])
    f_conta = ft.Dropdown(label="Conta", width=250, value="Todas",
                          options=get_contas_opcoes())

    total_text = ft.Text("", size=13, weight="bold")
    msg_text   = ft.Text("", size=13)
    lista_col  = ft.Column([], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

    # ── EDIÇÃO ────────────────────────────────────────────────────────────
    data_f  = ft.TextField(label="Data",               width=120)
    valor_f = ft.TextField(label="Valor (ex: 462,00)", width=150, on_blur=formatar_moeda_input)
    desc_f  = ft.TextField(label="Descrição",           width=300)
    btn_salvar   = ft.ElevatedButton("SALVAR ALTERAÇÃO", bgcolor="blue", color="white",
                                     on_click=lambda e: salvar_edicao(e))
    btn_cancelar = ft.ElevatedButton("CANCELAR", bgcolor=ft.colors.GREY_400,
                                     on_click=lambda e: cancelar_edicao(e))
    edicao_row = ft.Row([data_f, valor_f, desc_f, btn_salvar, btn_cancelar], visible=False)

    # ── LINHA DE TRANSAÇÃO ────────────────────────────────────────────────
    def linha_transacao(t):
        cor = ft.colors.GREEN_700 if t["tipo"] == "Receita" else ft.colors.RED_700
        tid = t["id"]
        def fazer_deletar(tid=tid): deletar(tid)
        def ao_clicar_excluir(_, f=fazer_deletar): verificar_admin(page, f)
        data_fmt = parse_data(t["data"])
        return ft.Container(
            border=ft.border.only(bottom=ft.BorderSide(1, "#EEEEEE")),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            content=ft.Row([
                ft.Container(width=110, content=ft.Text(data_fmt, size=13, color="#555555")),
                ft.Container(width=200, content=ft.Text(t["nome"], size=13)),
                ft.Container(width=130, content=ft.Text(fmt(t["valor"]), size=14, weight="bold", color=cor)),
                ft.Container(width=90,  content=ft.Container(
                    bgcolor=ft.colors.GREEN_100 if t["tipo"] == "Receita" else ft.colors.RED_100,
                    border_radius=12, padding=ft.padding.symmetric(horizontal=8, vertical=2),
                    content=ft.Text(t["tipo"], size=12, color=cor, weight="bold")
                )),
                ft.Container(expand=True, content=ft.Text(t["descricao"] or "—", size=13, color="#666666")),
                ft.Row([
                    ft.IconButton(icon=ft.icons.EDIT, icon_color="#1565C0", tooltip="Alterar",
                                  icon_size=18, on_click=lambda _, d=t: preparar_edicao(d)),
                    ft.IconButton(icon=ft.icons.DELETE, icon_color=ft.colors.RED_700, tooltip="Excluir",
                                  icon_size=18, on_click=ao_clicar_excluir),
                ], spacing=0),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    def cabecalho_mes(label, rec, desp):
        saldo = rec - desp
        return ft.Container(
            bgcolor="#1565C0",
            border_radius=ft.border_radius.only(top_left=8, top_right=8),
            padding=ft.padding.symmetric(horizontal=16, vertical=14),
            margin=ft.margin.only(top=20),
            content=ft.Row([
                ft.Text(label, size=18, weight="bold", color="white", expand=True),
                ft.Row([
                    ft.Container(bgcolor=ft.colors.with_opacity(0.25,"white"), border_radius=6,
                        padding=ft.padding.symmetric(horizontal=12, vertical=4),
                        content=ft.Text(f"✅ {fmt(rec)}", size=14, color="white")),
                    ft.Container(bgcolor=ft.colors.with_opacity(0.25,"white"), border_radius=6,
                        padding=ft.padding.symmetric(horizontal=12, vertical=4),
                        content=ft.Text(f"❌ {fmt(desp)}", size=14, color="white")),
                    ft.Container(bgcolor=ft.colors.with_opacity(0.35,"white"), border_radius=6,
                        padding=ft.padding.symmetric(horizontal=12, vertical=4),
                        content=ft.Text(f"💰 {fmt(saldo)}", size=14, weight="bold",
                            color=ft.colors.GREEN_200 if saldo >= 0 else ft.colors.RED_200)),
                ], spacing=10),
            ]),
        )

    def cabecalho_colunas():
        return ft.Container(
            bgcolor="#E3F2FD",
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            content=ft.Row([
                ft.Container(width=110, content=ft.Text("Data",      size=13, weight="bold", color="#1565C0")),
                ft.Container(width=200, content=ft.Text("Conta",     size=13, weight="bold", color="#1565C0")),
                ft.Container(width=130, content=ft.Text("Valor",     size=13, weight="bold", color="#1565C0")),
                ft.Container(width=90,  content=ft.Text("Tipo",      size=13, weight="bold", color="#1565C0")),
                ft.Container(expand=True, content=ft.Text("Descrição", size=13, weight="bold", color="#1565C0")),
                ft.Container(width=80,  content=ft.Text("Ações",    size=13, weight="bold", color="#1565C0")),
            ]),
        )

    # ── CARREGAR TABELA ───────────────────────────────────────────────────
    def carregar_tabela():
        try:
            conn   = get_connection()
            cur    = get_cursor(conn)
            query  = """
                SELECT t.id, t.data, s.nome, t.valor, t.tipo, t.descricao
                FROM transacoes t
                JOIN subcontas s ON t.subconta_id = s.id
                WHERE t.usuario_id = %s
            """
            params = [uid]

            d_ini = str_to_date(f_ini.value)
            d_fim = str_to_date(f_fim.value)
            if d_ini:
                query += " AND TO_DATE(t.data, 'DD/MM/YYYY') >= %s"
                params.append(d_ini)
            if d_fim:
                query += " AND TO_DATE(t.data, 'DD/MM/YYYY') <= %s"
                params.append(d_fim)

            if f_tipo.value and f_tipo.value != "Todos":
                query += " AND t.tipo = %s"
                params.append(f_tipo.value)

            if f_conta.value and f_conta.value != "Todas":
                query += " AND s.nome = %s"
                params.append(f_conta.value)

            query += " ORDER BY TO_DATE(t.data, 'DD/MM/YYYY') DESC, t.id DESC"
            cur.execute(query, params)
            trans = cur.fetchall()
            conn.close()
            state["trans"] = trans

            # Agrupa por mês
            grupos = {}
            for t in trans:
                ds  = parse_data(t["data"])
                ck  = chave_mes(ds)
                lbl = mes_label(ds)
                if ck not in grupos:
                    grupos[ck] = {"label": lbl, "trans": [], "rec": 0.0, "desp": 0.0}
                grupos[ck]["trans"].append(t)
                if t["tipo"] == "Receita":
                    grupos[ck]["rec"]  += float(t["valor"])
                else:
                    grupos[ck]["desp"] += float(t["valor"])

            ordem = sorted(grupos.keys(), reverse=True)

            # Reconstrói lista
            novos = []
            total_rec = total_desp = 0.0
            for ck in ordem:
                g = grupos[ck]
                total_rec  += g["rec"]
                total_desp += g["desp"]
                novos.append(cabecalho_mes(g["label"], g["rec"], g["desp"]))
                novos.append(cabecalho_colunas())
                for t in g["trans"]:
                    novos.append(linha_transacao(t))
                novos.append(ft.Container(
                    bgcolor="#F5F5F5",
                    border_radius=ft.border_radius.only(bottom_left=8, bottom_right=8),
                    padding=ft.padding.symmetric(horizontal=16, vertical=6),
                    content=ft.Text(f"{len(g['trans'])} lancamento(s) em {g['label']}",
                                    size=12, color="#888888", italic=True),
                ))

            lista_col.controls = novos

            saldo = total_rec - total_desp
            total_text.value = (
                f"📋 {len(trans)} registros  |  "
                f"✅ Receitas: {fmt(total_rec)}  |  "
                f"❌ Despesas: {fmt(total_desp)}  |  "
                f"💰 Saldo: {fmt(saldo)}"
            )
            total_text.color = ft.colors.GREEN_700 if saldo >= 0 else ft.colors.RED_700
            page.update()

        except Exception as ex:
            import traceback; traceback.print_exc()
            print(f"[extrato] carregar_tabela: {ex}")

    f_tipo.on_change  = lambda e: carregar_tabela()
    f_conta.on_change = lambda e: carregar_tabela()

    def filtrar(e):
        carregar_tabela()

    def limpar_filtros(e):
        f_ini.value   = f"01/{hoje.month:02d}/{hoje.year}"
        f_fim.value   = f"{hoje.day:02d}/{hoje.month:02d}/{hoje.year}"
        f_ini.update()
        f_fim.update()
        f_tipo.value  = "Todos"
        f_conta.value = "Todas"
        msg_text.value = ""
        page.update()
        carregar_tabela()

    # ── CRUD ──────────────────────────────────────────────────────────────
    def deletar(tid):
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("SELECT tipo, valor, data, descricao FROM transacoes WHERE id=%s AND usuario_id=%s", (tid, uid))
            t = cur.fetchone()
            if t and t["descricao"] and "Transf. " in str(t["descricao"]):
                tipo_par = "Receita" if t["tipo"] == "Despesa" else "Despesa"
                cur.execute("DELETE FROM transacoes WHERE usuario_id=%s AND tipo=%s AND valor=%s AND data=%s AND descricao LIKE %s",
                            (uid, tipo_par, t["valor"], t["data"], "Transf.%"))
                cur.execute("DELETE FROM transacoes WHERE id=%s AND usuario_id=%s", (tid, uid))
                cur.execute("DELETE FROM transferencias WHERE usuario_id=%s AND valor=%s AND data=%s",
                            (uid, t["valor"], t["data"]))
                conn.commit()
                conn.close()
                msg_text.value = "🔗 Transferência excluída."
                msg_text.color = ft.colors.ORANGE_700
            else:
                cur.execute("DELETE FROM transacoes WHERE id=%s AND usuario_id=%s", (tid, uid))
                conn.commit()
                conn.close()
            carregar_tabela()
        except Exception as ex:
            print(f"[extrato] deletar: {ex}")

    def preparar_edicao(t):
        state["editing_id"] = t["id"]
        data_f.value  = parse_data(t["data"])
        valor_f.value = fmt(t["valor"]).replace("R$ ", "")
        desc_f.value  = t["descricao"] or ""
        edicao_row.visible = True
        page.update()

    def cancelar_edicao(e):
        state["editing_id"] = None
        data_f.value = valor_f.value = desc_f.value = ""
        edicao_row.visible = False
        page.update()

    def salvar_edicao(e):
        if not state["editing_id"]:
            return
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("UPDATE transacoes SET data=%s, valor=%s, descricao=%s WHERE id=%s AND usuario_id=%s",
                        (data_f.value, limpar_valor(valor_f.value), desc_f.value, state["editing_id"], uid))
            conn.commit()
            conn.close()
            cancelar_edicao(e)
            carregar_tabela()
        except Exception as ex:
            print(f"[extrato] salvar_edicao: {ex}")

    # ── EXPORTAR PDF ──────────────────────────────────────────────────────
    def exportar_pdf(e):
        try:
            trans = state["trans"]
            if not trans:
                msg_text.value = "⚠️ Nenhum dado para exportar."
                msg_text.color = ft.colors.ORANGE_700
                page.update()
                return

            msg_text.value = "⏳ Gerando PDF..."
            msg_text.color = ft.colors.BLUE_700
            page.update()

            buffer = io.BytesIO()
            doc    = SimpleDocTemplate(buffer, pagesize=A4,
                                       leftMargin=1.5*cm, rightMargin=1.5*cm,
                                       topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            elems  = []

            titulo_style = ParagraphStyle("titulo", parent=styles["Title"],
                fontSize=16, textColor=colors.HexColor("#1565C0"), spaceAfter=4)
            sub_style = ParagraphStyle("sub", parent=styles["Normal"],
                fontSize=10, textColor=colors.grey, spaceAfter=12)
            cell_style = ParagraphStyle("cell", fontSize=8, leading=10)

            filtros_str = []
            if f_ini.value: filtros_str.append(f"De: {f_ini.value}")
            if f_fim.value: filtros_str.append(f"Ate: {f_fim.value}")
            if f_tipo.value  != "Todos": filtros_str.append(f"Tipo: {safe(f_tipo.value)}")
            if f_conta.value != "Todas": filtros_str.append(f"Conta: {safe(f_conta.value)}")
            filtros_label = "  |  ".join(filtros_str) if filtros_str else "Todos os registros"

            elems += [
                Paragraph("FINANCA SIMPLES", titulo_style),
                Paragraph("EXTRATO DE TRANSACOES", titulo_style),
                Paragraph(f"Filtros: {filtros_label}", sub_style),
                Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style),
                Spacer(1, 0.5*cm),
            ]

            grupos = {}
            for t in trans:
                ds  = parse_data(t["data"])
                ck  = chave_mes(ds)
                lbl = mes_label(ds)
                if ck not in grupos:
                    grupos[ck] = {"label": lbl, "trans": [], "rec": 0.0, "desp": 0.0}
                grupos[ck]["trans"].append(t)
                if t["tipo"] == "Receita":
                    grupos[ck]["rec"]  += float(t["valor"])
                else:
                    grupos[ck]["desp"] += float(t["valor"])

            ordem = sorted(grupos.keys(), reverse=True)
            total_rec_g = total_des_g = 0.0
            col_widths  = [2.3*cm, 4.5*cm, 2.8*cm, 2.0*cm, 6.4*cm]

            for ck in ordem:
                g    = grupos[ck]
                rec  = g["rec"]
                desp = g["desp"]
                saldo_mes   = rec - desp
                total_rec_g += rec
                total_des_g += desp
                label_safe   = safe(g["label"])

                elems.append(Paragraph(
                    f"<b>{label_safe}</b>  -  Receitas: {fmt(rec)}  |  Despesas: {fmt(desp)}  |  Saldo: {fmt(saldo_mes)}",
                    ParagraphStyle("mes", parent=styles["Normal"], fontSize=10,
                        textColor=colors.HexColor("#1565C0"), backColor=colors.HexColor("#E3F2FD"),
                        spaceAfter=2, spaceBefore=10, borderPadding=4)
                ))

                dados_pdf = [["Data", "Conta", "Valor", "Tipo", "Descricao"]]
                for t in g["trans"]:
                    dados_pdf.append([
                        parse_data(t["data"]),
                        Paragraph(safe(t["nome"]), cell_style),
                        fmt(t["valor"]),
                        safe(t["tipo"]),
                        Paragraph(safe(t["descricao"]), cell_style),
                    ])
                n_dados = len(dados_pdf)
                cor_s = colors.HexColor("#1B5E20") if saldo_mes >= 0 else colors.HexColor("#B71C1C")
                dados_pdf.append(["", f"Subtotal {label_safe}",
                    Paragraph(f"Rec: {fmt(rec)}<br/>Des: {fmt(desp)}", cell_style),
                    Paragraph(f"Saldo:<br/>{fmt(saldo_mes)}", cell_style), ""])

                tbl = Table(dados_pdf, colWidths=col_widths, repeatRows=1)
                tbl.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0),(-1,0),  colors.HexColor("#1565C0")),
                    ("TEXTCOLOR",     (0,0),(-1,0),  colors.white),
                    ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
                    ("FONTSIZE",      (0,0),(-1,-1), 8),
                    ("ALIGN",         (0,0),(-1,0),  "CENTER"),
                    ("ROWBACKGROUNDS",(0,1),(-1,n_dados-1), [colors.white, colors.HexColor("#F5F5F5")]),
                    ("GRID",          (0,0),(-1,n_dados-1), 0.5, colors.HexColor("#DDDDDD")),
                    ("BACKGROUND",    (0,n_dados),(-1,-1), colors.HexColor("#E3F2FD")),
                    ("FONTNAME",      (0,n_dados),(-1,-1), "Helvetica-Bold"),
                    ("LINEABOVE",     (0,n_dados),(-1,n_dados), 1, colors.HexColor("#1565C0")),
                    ("TEXTCOLOR",     (2,n_dados),(3,n_dados), cor_s),
                    ("VALIGN",        (0,0),(-1,-1), "TOP"),
                    ("TOPPADDING",    (0,0),(-1,-1), 3),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 3),
                    ("LEFTPADDING",   (0,0),(-1,-1), 4),
                ]))
                elems.append(tbl)

            saldo_geral = total_rec_g - total_des_g
            elems += [
                Spacer(1, 0.5*cm),
                Paragraph(
                    f"<b>TOTAL GERAL  -  Receitas: {fmt(total_rec_g)}  |  "
                    f"Despesas: {fmt(total_des_g)}  |  Saldo: {fmt(saldo_geral)}</b>",
                    ParagraphStyle("total", parent=styles["Normal"], fontSize=11,
                        textColor=colors.HexColor("#1B5E20") if saldo_geral >= 0 else colors.HexColor("#B71C1C"),
                        backColor=colors.HexColor("#E8F5E9") if saldo_geral >= 0 else colors.HexColor("#FFEBEE"),
                        borderPadding=6)
                )
            ]

            doc.build(elems)

            pdf_bytes = buffer.getvalue()
            nome_arq  = f"extrato_{f_ini.value.replace('/','')}-{f_fim.value.replace('/','')}.pdf"

            dominio  = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
            base_url = f"https://{dominio}" if dominio else ""

            pasta_pdfs = os.path.join(tempfile.gettempdir(), "pdfs")
            os.makedirs(pasta_pdfs, exist_ok=True)
            caminho_pdf = os.path.join(pasta_pdfs, nome_arq)
            with open(caminho_pdf, "wb") as fp:
                fp.write(pdf_bytes)

            if base_url:
                url_pdf = f"{base_url}/pdf/{nome_arq}"
                msg_text.value = "✅ PDF pronto! Clique para baixar:"
                msg_text.color = ft.colors.GREEN_700
                page.update()
                page.launch_url(url_pdf, web_window_name="_blank")
            else:
                msg_text.value = f"✅ PDF salvo: {caminho_pdf}"
                msg_text.color = ft.colors.GREEN_700
                page.update()

        except Exception as ex:
            import traceback; traceback.print_exc()
            print(f"[extrato] exportar_pdf: {ex}")
            msg_text.value = "❌ Erro ao gerar PDF."
            msg_text.color = ft.colors.RED_700
            page.update()

    carregar_tabela()

    # ── VIEW ──────────────────────────────────────────────────────────────
    return ft.View(
        route="/extrato",
        controls=[
            get_menu(page),
            ft.Divider(),
            ft.Container(
                padding=20, expand=True,
                content=ft.Column(
                    controls=[
                        ft.Row([
                            ft.Icon(ft.icons.RECEIPT_LONG, color="#1565C0", size=26),
                            ft.Text("EXTRATO DE TRANSAÇÕES", size=18, weight="bold", color="#1565C0"),
                        ], spacing=10),
                        edicao_row,
                        ft.Divider(),
                        ft.Row([
                            f_ini, f_fim, f_tipo, f_conta,
                            ft.ElevatedButton("🔍 FILTRAR", bgcolor=ft.colors.BLUE_700,
                                color=ft.colors.WHITE, icon=ft.icons.SEARCH, on_click=filtrar),
                            ft.ElevatedButton("LIMPAR", bgcolor=ft.colors.GREY_300,
                                color=ft.colors.BLACK, icon=ft.icons.FILTER_ALT_OFF,
                                on_click=limpar_filtros),
                            ft.ElevatedButton("📄 EXPORTAR PDF", bgcolor=ft.colors.RED_700,
                                color=ft.colors.WHITE, on_click=exportar_pdf),
                        ], spacing=12, wrap=True),
                        ft.Container(
                            bgcolor="#F5F5F5", border_radius=8,
                            padding=ft.padding.symmetric(horizontal=16, vertical=10),
                            content=total_text,
                        ),
                        msg_text,
                        ft.Divider(),
                        lista_col,
                    ],
                    scroll=ft.ScrollMode.ALWAYS,
                    expand=True,
                )
            )
        ]
    )