import flet as ft
import os
import base64
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from menu import get_menu
from database import get_connection, get_cursor
from utils import verificar_admin, formatar_moeda_input, limpar_valor


def extrato_view(page: ft.Page):
    state = {"editing_id": None, "trans": []}
    uid   = page.session.get("user_id")
    hoje  = datetime.now()

    # ── OPÇÕES DOS FILTROS ─────────────────────────────────────────────────
    def get_meses_opcoes():
        opcoes = [ft.dropdown.Option("Todos")]
        m, a = hoje.month, hoje.year
        for _ in range(12):
            opcoes.append(ft.dropdown.Option(f"{m:02d}/{a}"))
            m -= 1
            if m == 0:
                m = 12
                a -= 1
        return opcoes

    def get_contas_opcoes():
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("SELECT DISTINCT s.nome FROM subcontas s WHERE s.usuario_id=%s ORDER BY s.nome", (uid,))
            nomes = cur.fetchall()
            conn.close()
            opcoes = [ft.dropdown.Option("Todas")]
            for n in nomes:
                opcoes.append(ft.dropdown.Option(n["nome"]))
            return opcoes
        except Exception:
            return [ft.dropdown.Option("Todas")]

    filtro_mes   = ft.Dropdown(label="Mês",   width=150, value="Todos", options=get_meses_opcoes())
    filtro_tipo  = ft.Dropdown(label="Tipo",  width=130, value="Todos", options=[
        ft.dropdown.Option("Todos"),
        ft.dropdown.Option("Receita"),
        ft.dropdown.Option("Despesa"),
    ])
    filtro_conta = ft.Dropdown(label="Conta", width=250, value="Todas", options=get_contas_opcoes())

    total_text = ft.Text("", size=13, weight="bold")
    msg_pdf    = ft.Text("", size=13)

    # ── COLUNA PRINCIPAL onde os grupos de mês são renderizados ───────────
    lista_col = ft.Column([], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

    # ── CAMPOS DE EDIÇÃO ───────────────────────────────────────────────────
    data_f   = ft.TextField(label="Data",              width=120)
    valor_f  = ft.TextField(label="Valor (ex: 462,00)", width=150, on_blur=formatar_moeda_input)
    desc_f   = ft.TextField(label="Descrição",          width=300)
    btn_salvar   = ft.ElevatedButton("SALVAR ALTERAÇÃO", bgcolor="blue", color="white",
                                     on_click=lambda e: salvar_edicao(e))
    btn_cancelar = ft.ElevatedButton("CANCELAR", bgcolor=ft.colors.GREY_400,
                                     on_click=lambda e: cancelar_edicao(e))
    edicao_row = ft.Row([data_f, valor_f, desc_f, btn_salvar, btn_cancelar], visible=False)

    def fmt(v):
        try:
            return f"R$ {float(v):_.2f}".replace(".", ",").replace("_", ".")
        except:
            return "R$ 0,00"

    # ── MONTA LINHA DE TRANSAÇÃO ───────────────────────────────────────────
    def linha_transacao(t):
        cor = ft.colors.GREEN_700 if t["tipo"] == "Receita" else ft.colors.RED_700
        tid = t["id"]

        def fazer_deletar(tid=tid):
            deletar(tid)

        def ao_clicar_excluir(_, f=fazer_deletar):
            verificar_admin(page, f)

        return ft.Container(
            border=ft.border.only(bottom=ft.BorderSide(1, "#EEEEEE")),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            content=ft.Row([
                # Data
                ft.Container(width=100,
                    content=ft.Text(t["data"], size=12, color="#555555")),
                # Conta
                ft.Container(width=200,
                    content=ft.Text(t["nome"], size=12)),
                # Valor
                ft.Container(width=130,
                    content=ft.Text(fmt(t["valor"]), size=13, weight="bold", color=cor)),
                # Tipo
                ft.Container(width=90,
                    content=ft.Container(
                        bgcolor=ft.colors.GREEN_100 if t["tipo"] == "Receita" else ft.colors.RED_100,
                        border_radius=12, padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        content=ft.Text(t["tipo"], size=11, color=cor, weight="bold")
                    )),
                # Descrição
                ft.Container(expand=True,
                    content=ft.Text(t["descricao"] or "—", size=12, color="#666666")),
                # Ações
                ft.Row([
                    ft.IconButton(icon=ft.icons.EDIT, icon_color="#1565C0",
                                  tooltip="Alterar", icon_size=18,
                                  on_click=lambda _, d=t: preparar_edicao(d)),
                    ft.IconButton(icon=ft.icons.DELETE, icon_color=ft.colors.RED_700,
                                  tooltip="Excluir", icon_size=18,
                                  on_click=ao_clicar_excluir),
                ], spacing=0),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )

    # ── MONTA CABEÇALHO DE MÊS ────────────────────────────────────────────
    def cabecalho_mes(mes_label, rec, desp):
        saldo    = rec - desp
        cor_sald = ft.colors.GREEN_700 if saldo >= 0 else ft.colors.RED_700
        return ft.Container(
            bgcolor="#1565C0",
            border_radius=ft.border_radius.only(top_left=8, top_right=8),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            margin=ft.margin.only(top=16),
            content=ft.Row([
                ft.Text(mes_label, size=14, weight="bold", color="white", expand=True),
                ft.Row([
                    ft.Container(
                        bgcolor=ft.colors.with_opacity(0.25, "white"),
                        border_radius=6, padding=ft.padding.symmetric(horizontal=10, vertical=3),
                        content=ft.Text(f"✅ {fmt(rec)}", size=12, color="white")),
                    ft.Container(
                        bgcolor=ft.colors.with_opacity(0.25, "white"),
                        border_radius=6, padding=ft.padding.symmetric(horizontal=10, vertical=3),
                        content=ft.Text(f"❌ {fmt(desp)}", size=12, color="white")),
                    ft.Container(
                        bgcolor=ft.colors.with_opacity(0.35, "white"),
                        border_radius=6, padding=ft.padding.symmetric(horizontal=10, vertical=3),
                        content=ft.Text(f"💰 {fmt(saldo)}", size=12,
                                        color=ft.colors.GREEN_200 if saldo >= 0 else ft.colors.RED_200,
                                        weight="bold")),
                ], spacing=8),
            ]),
        )

    # ── CABEÇALHO DAS COLUNAS DA TABELA ───────────────────────────────────
    def cabecalho_colunas():
        return ft.Container(
            bgcolor="#E3F2FD",
            padding=ft.padding.symmetric(horizontal=16, vertical=6),
            content=ft.Row([
                ft.Container(width=100, content=ft.Text("Data",      size=11, weight="bold", color="#1565C0")),
                ft.Container(width=200, content=ft.Text("Conta",     size=11, weight="bold", color="#1565C0")),
                ft.Container(width=130, content=ft.Text("Valor",     size=11, weight="bold", color="#1565C0")),
                ft.Container(width=90,  content=ft.Text("Tipo",      size=11, weight="bold", color="#1565C0")),
                ft.Container(expand=True, content=ft.Text("Descrição", size=11, weight="bold", color="#1565C0")),
                ft.Container(width=80,  content=ft.Text("Ações",    size=11, weight="bold", color="#1565C0")),
            ]),
        )

    # ── CARREGA E AGRUPA POR MÊS ───────────────────────────────────────────
    def carregar_tabela():
        try:
            conn  = get_connection()
            cur   = get_cursor(conn)
            query = """
                SELECT t.id, t.data, s.nome, t.valor, t.tipo, t.descricao
                FROM transacoes t
                JOIN subcontas s ON t.subconta_id = s.id
                WHERE t.usuario_id = %s
            """
            params = [uid]

            if filtro_mes.value and filtro_mes.value != "Todos":
                query += " AND t.data LIKE %s"
                params.append(f"%{filtro_mes.value}")

            if filtro_tipo.value and filtro_tipo.value != "Todos":
                query += " AND t.tipo = %s"
                params.append(filtro_tipo.value)

            if filtro_conta.value and filtro_conta.value != "Todas":
                query += " AND s.nome = %s"
                params.append(filtro_conta.value)

            query += " ORDER BY t.data DESC, t.id DESC"
            cur.execute(query, params)
            trans = cur.fetchall()
            conn.close()

            state["trans"] = trans

            # ── Agrupa transações por mês/ano ──────────────────────────────
            grupos = {}   # { "MM/YYYY": [transações] }
            ordem  = []   # mantém a ordem cronológica decrescente

            for t in trans:
                # data pode ser "DD/MM/YYYY" ou "YYYY-MM-DD" dependendo do banco
                try:
                    data_str = str(t["data"])
                    if "/" in data_str:
                        partes = data_str.split("/")
                        chave  = f"{partes[1]}/{partes[2]}"          # MM/YYYY
                        mes_label = _mes_label(partes[1], partes[2]) # "Maio 2026"
                    else:
                        partes = data_str.split("-")
                        chave  = f"{partes[1]}/{partes[0]}"
                        mes_label = _mes_label(partes[1], partes[0])
                except:
                    chave     = "??/??"
                    mes_label = "Data inválida"

                if chave not in grupos:
                    grupos[chave] = {"label": mes_label, "trans": [], "rec": 0.0, "desp": 0.0}
                    ordem.append(chave)

                grupos[chave]["trans"].append(t)
                if t["tipo"] == "Receita":
                    grupos[chave]["rec"]  += float(t["valor"])
                else:
                    grupos[chave]["desp"] += float(t["valor"])

            # ── Monta a lista visual ───────────────────────────────────────
            lista_col.controls.clear()

            total_rec  = 0.0
            total_desp = 0.0

            for chave in ordem:
                g   = grupos[chave]
                rec  = g["rec"]
                desp = g["desp"]
                total_rec  += rec
                total_desp += desp

                # Cabeçalho do mês (azul)
                lista_col.controls.append(cabecalho_mes(g["label"], rec, desp))

                # Cabeçalho das colunas
                lista_col.controls.append(cabecalho_colunas())

                # Linhas das transações
                for t in g["trans"]:
                    lista_col.controls.append(linha_transacao(t))

                # Rodapé do grupo
                lista_col.controls.append(
                    ft.Container(
                        bgcolor="#F5F5F5",
                        border_radius=ft.border_radius.only(bottom_left=8, bottom_right=8),
                        padding=ft.padding.symmetric(horizontal=16, vertical=6),
                        content=ft.Text(
                            f"{len(g['trans'])} lançamento(s) em {g['label']}",
                            size=11, color="#888888", italic=True),
                    )
                )

            # ── Totais gerais ──────────────────────────────────────────────
            saldo     = total_rec - total_desp
            cor_saldo = ft.colors.GREEN_700 if saldo >= 0 else ft.colors.RED_700
            total_text.value = (
                f"📋 {len(trans)} registros  |  "
                f"✅ Receitas: {fmt(total_rec)}  |  "
                f"❌ Despesas: {fmt(total_desp)}  |  "
                f"💰 Saldo: {fmt(saldo)}"
            )
            total_text.color = cor_saldo
            page.update()

        except Exception as ex:
            import traceback; traceback.print_exc()
            print(f"[extrato] carregar_tabela: {ex}")

    def _mes_label(mm, yyyy):
        nomes = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                 "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
        try:
            return f"{nomes[int(mm)-1]} {yyyy}"
        except:
            return f"{mm}/{yyyy}"

    filtro_mes.on_change   = lambda e: carregar_tabela()
    filtro_tipo.on_change  = lambda e: carregar_tabela()
    filtro_conta.on_change = lambda e: carregar_tabela()

    def limpar_filtros(e):
        filtro_mes.value   = "Todos"
        filtro_tipo.value  = "Todos"
        filtro_conta.value = "Todas"
        carregar_tabela()

    # ── CRUD ───────────────────────────────────────────────────────────────
    def deletar(tid):
        try:
            conn = get_connection()
            cur  = get_cursor(conn)

            # Verifica se é transação de transferência
            cur.execute(
                "SELECT tipo, valor, data, banco_id, descricao FROM transacoes WHERE id=%s AND usuario_id=%s",
                (tid, uid)
            )
            t = cur.fetchone()

            if t and t["descricao"] and ("Transf. " in str(t["descricao"])):
                valor = t["valor"]
                data  = t["data"]
                tipo_par = "Receita" if t["tipo"] == "Despesa" else "Despesa"

                # Exclui a transação par
                cur.execute("""
                    DELETE FROM transacoes
                    WHERE usuario_id=%s AND tipo=%s AND valor=%s AND data=%s
                      AND descricao LIKE %s
                """, (uid, tipo_par, valor, data, "Transf.%"))

                # Exclui a própria transação
                cur.execute("DELETE FROM transacoes WHERE id=%s AND usuario_id=%s", (tid, uid))

                # Exclui da tabela transferencias
                cur.execute("""
                    DELETE FROM transferencias
                    WHERE usuario_id=%s AND valor=%s AND data=%s
                """, (uid, valor, data))

                conn.commit()
                conn.close()
                msg_pdf.value = "🔗 Transferência e lançamentos vinculados excluídos."
                msg_pdf.color = ft.colors.ORANGE_700
            else:
                cur.execute("DELETE FROM transacoes WHERE id=%s AND usuario_id=%s", (tid, uid))
                conn.commit()
                conn.close()

            carregar_tabela()
        except Exception as ex:
            print(f"[extrato] deletar: {ex}")

    def preparar_edicao(t):
        state["editing_id"] = t["id"]
        data_f.value  = t["data"]
        valor_f.value = f"{t['valor']:_.2f}".replace(".", ",").replace("_", ".")
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
            cur.execute(
                "UPDATE transacoes SET data=%s, valor=%s, descricao=%s WHERE id=%s AND usuario_id=%s",
                (data_f.value, limpar_valor(valor_f.value), desc_f.value, state["editing_id"], uid)
            )
            conn.commit()
            conn.close()
            cancelar_edicao(e)
            carregar_tabela()
        except Exception as ex:
            print(f"[extrato] salvar_edicao: {ex}")

    # ── EXPORTAR PDF — gera em memória e abre via base64 no browser ───────
    def exportar_pdf(e):
        try:
            trans = state["trans"]
            if not trans:
                msg_pdf.value = "⚠️ Nenhum dado para exportar."
                msg_pdf.color = ft.colors.ORANGE_700
                page.update()
                return

            msg_pdf.value = "⏳ Gerando PDF..."
            msg_pdf.color = ft.colors.BLUE_700
            page.update()

            # Gera o PDF em memória (BytesIO)
            buffer = io.BytesIO()
            doc    = SimpleDocTemplate(buffer, pagesize=A4,
                                       leftMargin=1.5*cm, rightMargin=1.5*cm,
                                       topMargin=2*cm,    bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            elems  = []

            titulo_style = ParagraphStyle("titulo", parent=styles["Title"],
                fontSize=16, textColor=colors.HexColor("#1565C0"), spaceAfter=4)
            sub_style = ParagraphStyle("sub", parent=styles["Normal"],
                fontSize=10, textColor=colors.grey, spaceAfter=12)

            filtros_str = []
            if filtro_mes.value   != "Todos":  filtros_str.append(f"Mês: {filtro_mes.value}")
            if filtro_tipo.value  != "Todos":  filtros_str.append(f"Tipo: {filtro_tipo.value}")
            if filtro_conta.value != "Todas":  filtros_str.append(f"Conta: {filtro_conta.value}")
            filtros_label = "  |  ".join(filtros_str) if filtros_str else "Todos os registros"

            elems += [
                Paragraph("FINANÇA SIMPLES", titulo_style),
                Paragraph("EXTRATO DE TRANSAÇÕES", titulo_style),
                Paragraph(f"Filtros: {filtros_label}", sub_style),
                Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style),
                Spacer(1, 0.5*cm),
            ]

            # Agrupa por mês para o PDF também
            grupos = {}
            ordem  = []
            for t in trans:
                try:
                    data_str = str(t["data"])
                    if "/" in data_str:
                        partes = data_str.split("/")
                        chave  = f"{partes[1]}/{partes[2]}"
                        label  = _mes_label(partes[1], partes[2])
                    else:
                        partes = data_str.split("-")
                        chave  = f"{partes[1]}/{partes[0]}"
                        label  = _mes_label(partes[1], partes[0])
                except:
                    chave = label = "??"
                if chave not in grupos:
                    grupos[chave] = {"label": label, "trans": [], "rec": 0.0, "desp": 0.0}
                    ordem.append(chave)
                grupos[chave]["trans"].append(t)
                if t["tipo"] == "Receita": grupos[chave]["rec"]  += float(t["valor"])
                else:                      grupos[chave]["desp"] += float(t["valor"])

            total_rec_geral = total_des_geral = 0.0

            for chave in ordem:
                g    = grupos[chave]
                rec  = g["rec"]
                desp = g["desp"]
                saldo_mes = rec - desp
                total_rec_geral  += rec
                total_des_geral  += desp

                # Título do mês
                elems.append(Paragraph(
                    f"<b>{g['label']}</b>  —  "
                    f"Receitas: {fmt(rec)}  |  Despesas: {fmt(desp)}  |  Saldo: {fmt(saldo_mes)}",
                    ParagraphStyle("mes", parent=styles["Normal"],
                        fontSize=10, textColor=colors.HexColor("#1565C0"),
                        backColor=colors.HexColor("#E3F2FD"),
                        spaceAfter=2, spaceBefore=10,
                        leftIndent=0, borderPadding=4)
                ))

                cabecalho = ["Data", "Conta", "Valor", "Tipo", "Descrição"]
                dados_pdf = [cabecalho]
                for t in g["trans"]:
                    dados_pdf.append([
                        t["data"], t["nome"], fmt(t["valor"]), t["tipo"], t["descricao"] or ""
                    ])

                n_dados = len(dados_pdf)
                dados_pdf.append(["", f"Subtotal {g['label']}",
                                   f"R: {fmt(rec)} / D: {fmt(desp)}", fmt(saldo_mes), ""])

                tabela_pdf = Table(dados_pdf, colWidths=[2.5*cm, 5*cm, 3*cm, 2.5*cm, 5*cm])
                cor_saldo_pdf = colors.HexColor("#1B5E20") if saldo_mes >= 0 else colors.HexColor("#B71C1C")
                tabela_pdf.setStyle(TableStyle([
                    ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#1565C0")),
                    ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
                    ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
                    ("FONTSIZE",      (0, 0), (-1, -1), 8),
                    ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
                    ("ROWBACKGROUNDS",(0, 1), (-1, n_dados-1),
                                               [colors.white, colors.HexColor("#F5F5F5")]),
                    ("GRID",          (0, 0), (-1, n_dados-1), 0.5, colors.HexColor("#DDDDDD")),
                    ("BACKGROUND",    (0, n_dados), (-1, -1), colors.HexColor("#E3F2FD")),
                    ("FONTNAME",      (0, n_dados), (-1, -1), "Helvetica-Bold"),
                    ("LINEABOVE",     (0, n_dados), (-1, n_dados), 1, colors.HexColor("#1565C0")),
                    ("TEXTCOLOR",     (3, n_dados), (3, n_dados), cor_saldo_pdf),
                    ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING",    (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING",   (0, 0), (-1, -1), 4),
                ]))
                elems.append(tabela_pdf)

            # Totais gerais no final
            saldo_geral = total_rec_geral - total_des_geral
            elems += [
                Spacer(1, 0.5*cm),
                Paragraph(
                    f"<b>TOTAL GERAL  —  "
                    f"Receitas: {fmt(total_rec_geral)}  |  "
                    f"Despesas: {fmt(total_des_geral)}  |  "
                    f"Saldo: {fmt(saldo_geral)}</b>",
                    ParagraphStyle("total", parent=styles["Normal"],
                        fontSize=11,
                        textColor=colors.HexColor("#1B5E20") if saldo_geral >= 0 else colors.HexColor("#B71C1C"),
                        backColor=colors.HexColor("#E8F5E9") if saldo_geral >= 0 else colors.HexColor("#FFEBEE"),
                        borderPadding=6)
                )
            ]

            doc.build(elems)

            # ── Converte para base64 e abre download no browser ────────────
            pdf_bytes  = buffer.getvalue()
            b64        = base64.b64encode(pdf_bytes).decode("utf-8")
            mes_label  = (filtro_mes.value if filtro_mes.value != "Todos" else "completo").replace("/", "-")
            nome_arq   = f"extrato_{mes_label}_{datetime.now().strftime('%d%m%Y_%H%M%S')}.pdf"

            # Dispara download direto via JS sem abrir nova aba
            js = (
                "(function(){{"
                "var a=document.createElement('a');"
                f"a.href='data:application/pdf;base64,{b64}';"
                f"a.download='{nome_arq}';"
                "document.body.appendChild(a);"
                "a.click();"
                "document.body.removeChild(a);"
                "}})()"
            )
            page.eval_javascript(js)

            msg_pdf.value = f"✅ PDF gerado: {nome_arq}"
            msg_pdf.color = ft.colors.GREEN_700
            page.update()

        except Exception as ex:
            import traceback; traceback.print_exc()
            print(f"[extrato] exportar_pdf: {ex}")
            msg_pdf.value = "❌ Erro ao gerar PDF."
            msg_pdf.color = ft.colors.RED_700
            page.update()

    carregar_tabela()

    # ── VIEW ───────────────────────────────────────────────────────────────
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
                        # Filtros
                        ft.Row([
                            filtro_mes, filtro_tipo, filtro_conta,
                            ft.ElevatedButton(
                                "LIMPAR FILTROS", icon=ft.icons.FILTER_ALT_OFF,
                                bgcolor=ft.colors.GREY_300, color=ft.colors.BLACK,
                                on_click=limpar_filtros),
                            ft.ElevatedButton(
                                "📄 EXPORTAR PDF",
                                bgcolor=ft.colors.RED_700, color=ft.colors.WHITE,
                                on_click=exportar_pdf),
                        ], spacing=12, wrap=True),
                        # Totais
                        ft.Container(
                            bgcolor="#F5F5F5", border_radius=8,
                            padding=ft.padding.symmetric(horizontal=16, vertical=10),
                            content=total_text,
                        ),
                        msg_pdf,
                        ft.Divider(),
                        # Lista agrupada por mês
                        lista_col,
                    ],
                    scroll=ft.ScrollMode.ALWAYS,
                    expand=True,
                )
            )
        ]
    )