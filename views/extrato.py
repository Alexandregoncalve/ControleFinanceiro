import flet as ft
import os
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

    tabela = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Data")),
            ft.DataColumn(ft.Text("Conta")),
            ft.DataColumn(ft.Text("Valor")),
            ft.DataColumn(ft.Text("Tipo")),
            ft.DataColumn(ft.Text("Descrição")),
            ft.DataColumn(ft.Text("Ações")),
        ],
        rows=[],
    )

    data_f   = ft.TextField(label="Data", width=120)
    valor_f  = ft.TextField(label="Valor (ex: 462,00)", width=150, on_blur=formatar_moeda_input)
    desc_f   = ft.TextField(label="Descrição", width=300)
    btn_salvar   = ft.ElevatedButton("SALVAR ALTERAÇÃO", bgcolor="blue", color="white",
                                     on_click=lambda e: salvar_edicao(e))
    btn_cancelar = ft.ElevatedButton("CANCELAR", bgcolor=ft.colors.GREY_400,
                                     on_click=lambda e: cancelar_edicao(e))
    edicao_row = ft.Row([data_f, valor_f, desc_f, btn_salvar, btn_cancelar], visible=False)

    def fmt(v):
        return f"R$ {v:_.2f}".replace(".", ",").replace("_", ".")

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
            tabela.rows.clear()
            total_receita = 0.0
            total_despesa = 0.0

            for t in trans:
                tid = t["id"]
                cor = ft.colors.GREEN_700 if t["tipo"] == "Receita" else ft.colors.RED_700

                if t["tipo"] == "Receita":
                    total_receita += t["valor"]
                else:
                    total_despesa += t["valor"]

                def fazer_deletar(tid=tid):
                    deletar(tid)

                def ao_clicar_excluir(_, f=fazer_deletar):
                    verificar_admin(page, f)

                tabela.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(t["data"])),
                    ft.DataCell(ft.Text(t["nome"])),
                    ft.DataCell(ft.Text(fmt(t["valor"]), color=cor, weight="bold")),
                    ft.DataCell(ft.Text(t["tipo"], color=cor)),
                    ft.DataCell(ft.Text(t["descricao"] or "")),
                    ft.DataCell(ft.Row([
                        ft.TextButton("Alterar", on_click=lambda _, d=t: preparar_edicao(d)),
                        ft.TextButton(
                            "Excluir",
                            style=ft.ButtonStyle(color=ft.colors.RED_700),
                            on_click=ao_clicar_excluir
                        ),
                    ])),
                ]))

            saldo     = total_receita - total_despesa
            cor_saldo = ft.colors.GREEN_700 if saldo >= 0 else ft.colors.RED_700
            total_text.value = (
                f"📋 {len(trans)} registros  |  "
                f"✅ Receitas: {fmt(total_receita)}  |  "
                f"❌ Despesas: {fmt(total_despesa)}  |  "
                f"💰 Saldo: {fmt(saldo)}"
            )
            total_text.color = cor_saldo
            page.update()

        except Exception as ex:
            print(f"[extrato] carregar_tabela: {ex}")

    filtro_mes.on_change   = lambda e: carregar_tabela()
    filtro_tipo.on_change  = lambda e: carregar_tabela()
    filtro_conta.on_change = lambda e: carregar_tabela()

    def limpar_filtros(e):
        filtro_mes.value   = "Todos"
        filtro_tipo.value  = "Todos"
        filtro_conta.value = "Todas"
        carregar_tabela()

    def deletar(tid):
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
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

    def exportar_pdf(e):
        try:
            trans = state["trans"]
            if not trans:
                msg_pdf.value = "⚠️ Nenhum dado para exportar."
                msg_pdf.color = ft.colors.ORANGE_700
                page.update()
                return

            pasta = "/tmp/relatorios"
            os.makedirs(pasta, exist_ok=True)
            mes_label    = (filtro_mes.value if filtro_mes.value != "Todos" else "completo").replace("/", "-")
            nome_arquivo = f"extrato_{mes_label}_{datetime.now().strftime('%d%m%Y_%H%M%S')}.pdf"
            caminho      = os.path.join(pasta, nome_arquivo)

            doc    = SimpleDocTemplate(caminho, pagesize=A4,
                                       leftMargin=1.5*cm, rightMargin=1.5*cm,
                                       topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            elems  = []

            titulo_style = ParagraphStyle("titulo", parent=styles["Title"],
                fontSize=16, textColor=colors.HexColor("#1565C0"), spaceAfter=4)
            sub_style = ParagraphStyle("sub", parent=styles["Normal"],
                fontSize=10, textColor=colors.grey, spaceAfter=12)

            filtros_str = []
            if filtro_mes.value != "Todos":   filtros_str.append(f"Mês: {filtro_mes.value}")
            if filtro_tipo.value != "Todos":  filtros_str.append(f"Tipo: {filtro_tipo.value}")
            if filtro_conta.value != "Todas": filtros_str.append(f"Conta: {filtro_conta.value}")
            filtros_label = "  |  ".join(filtros_str) if filtros_str else "Todos os registros"

            elems += [
                Paragraph("FINANÇA SIMPLES", titulo_style),
                Paragraph("EXTRATO DE TRANSAÇÕES", titulo_style),
                Paragraph(f"Filtros: {filtros_label}", sub_style),
                Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style),
                Spacer(1, 0.5*cm),
            ]

            cabecalho = ["Data", "Conta", "Valor", "Tipo", "Descrição"]
            dados_pdf = [cabecalho]
            total_rec = total_des = 0.0

            for t in trans:
                dados_pdf.append([t["data"], t["nome"], fmt(t["valor"]), t["tipo"], t["descricao"] or ""])
                if t["tipo"] == "Receita": total_rec += t["valor"]
                else:                      total_des += t["valor"]

            saldo   = total_rec - total_des
            n_dados = len(dados_pdf)
            n_total = len(trans) + 1
            dados_pdf += [
                ["", "TOTAL",    "",             "", ""],
                ["", "Receitas", fmt(total_rec), "", ""],
                ["", "Despesas", fmt(total_des), "", ""],
                ["", "Saldo",    fmt(saldo),     "", ""],
            ]

            tabela_pdf = Table(dados_pdf, colWidths=[2.5*cm, 5*cm, 3*cm, 2.5*cm, 5*cm])
            tabela_pdf.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#1565C0")),
                ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
                ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
                ("FONTSIZE",      (0, 0), (-1, 0),  9),
                ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
                ("FONTSIZE",      (0, 1), (-1, -1), 8),
                ("ROWBACKGROUNDS",(0, 1), (-1, n_total-1), [colors.white, colors.HexColor("#F5F5F5")]),
                ("GRID",          (0, 0), (-1, n_total-1), 0.5, colors.HexColor("#DDDDDD")),
                ("BACKGROUND",    (0, n_total), (-1, -1), colors.HexColor("#E3F2FD")),
                ("FONTNAME",      (0, n_total), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE",      (0, n_total), (-1, -1), 9),
                ("LINEABOVE",     (0, n_total), (-1, n_total), 1, colors.HexColor("#1565C0")),
                ("TEXTCOLOR",     (2, n_dados-1), (2, n_dados-1),
                 colors.HexColor("#1B5E20") if saldo >= 0 else colors.HexColor("#B71C1C")),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ]))
            elems.append(tabela_pdf)
            doc.build(elems)

            msg_pdf.value = f"✅ PDF gerado com sucesso!"
            msg_pdf.color = ft.colors.GREEN_700
            page.update()

        except Exception as ex:
            print(f"[extrato] exportar_pdf: {ex}")
            msg_pdf.value = "❌ Erro ao gerar PDF."
            msg_pdf.color = ft.colors.RED_700
            page.update()

    carregar_tabela()

    return ft.View(
        route="/extrato",
        controls=[
            get_menu(page),
            ft.Divider(),
            ft.Container(
                padding=20, expand=True,
                content=ft.Column(
                    controls=[
                        ft.Text("EXTRATO DE TRANSAÇÕES", size=18, weight="bold", color="blue"),
                        edicao_row,
                        ft.Divider(),
                        ft.Row([
                            filtro_mes, filtro_tipo, filtro_conta,
                            ft.ElevatedButton("LIMPAR FILTROS", icon=ft.icons.FILTER_ALT_OFF,
                                bgcolor=ft.colors.GREY_300, color=ft.colors.BLACK,
                                on_click=limpar_filtros),
                            ft.ElevatedButton("📄 EXPORTAR PDF",
                                bgcolor=ft.colors.RED_700, color=ft.colors.WHITE,
                                on_click=exportar_pdf),
                        ], spacing=12, wrap=True),
                        total_text,
                        msg_pdf,
                        ft.Divider(),
                        ft.Row(controls=[tabela], scroll=ft.ScrollMode.ALWAYS),
                    ],
                    scroll=ft.ScrollMode.ALWAYS,
                    expand=True,
                )
            )
        ]
    )