import flet as ft
from datetime import datetime
from menu import get_menu
from database import db_session  # Importando a nova função de segurança
from utils import formatar_moeda_input, limpar_valor


def dividas_view(page):
    def fmt(v):
        return f"R$ {v:_.2f}".replace(".", ",").replace("_", ".")

    hoje = datetime.now()
    uid = page.session.get("user_id")

    # Componentes de Entrada
    dd_subconta = ft.Dropdown(label="Tipo de Dívida", width=220, disabled=True)
    tf_descricao = ft.TextField(label="Descrição", width=300, hint_text="Ex: Empréstimo Banco X")
    tf_total = ft.TextField(label="Valor Total", width=160, on_blur=formatar_moeda_input)
    tf_parcelas = ft.TextField(label="Nº Parcelas", width=120, keyboard_type=ft.KeyboardType.NUMBER)
    tf_pago = ft.TextField(label="Parcelas Pagas", width=120, keyboard_type=ft.KeyboardType.NUMBER)
    tf_vencimento = ft.TextField(label="Dia Vencimento", width=140, keyboard_type=ft.KeyboardType.NUMBER)
    tf_taxa = ft.TextField(label="Taxa Juros % a.m.", width=160, on_blur=formatar_moeda_input)
    msg_form = ft.Text("", size=12)

    # Componentes de Exibição
    lista_dividas = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
    resumo_row = ft.Row(spacing=12, wrap=True)

    def carregar_subcontas():
        """Alimenta o dropdown com categorias que tenham 'DIVIDA' no nome."""
        try:
            with db_session() as cur:
                cur.execute("""
                    SELECT s.id, s.nome FROM subcontas s
                    JOIN categorias c ON s.categoria_id = c.id
                    WHERE (UPPER(c.nome) LIKE '%DIVIDA%' OR UPPER(s.nome) LIKE '%DIVIDA%') 
                    AND s.usuario_id=%s
                    ORDER BY s.nome
                """, (uid,))
                rows = cur.fetchall()

            if rows:
                dd_subconta.options = [ft.dropdown.Option(str(r["id"]), r["nome"]) for r in rows]
                dd_subconta.disabled = False
                dd_subconta.hint_text = "Selecione o tipo"
            else:
                dd_subconta.options = []
                dd_subconta.disabled = True
                dd_subconta.hint_text = "Crie uma conta de Dívida em 'CONTAS'"

            dd_subconta.update()
            page.update()
        except Exception as ex:
            print(f"[dividas] carregar_subcontas: {ex}")

    def carregar_dividas():
        """Alimenta a lista e o resumo de dívidas pagas."""
        try:
            with db_session() as cur:
                cur.execute("""
                    SELECT s.nome as tipo, t.descricao,
                           SUM(t.valor) as total_pago,
                           COUNT(*) as parcelas_pagas,
                           t.subconta_id,
                           MAX(t.data) as ultima_data
                    FROM transacoes t
                    JOIN subcontas s ON t.subconta_id = s.id
                    JOIN categorias c ON s.categoria_id = c.id
                    WHERE (UPPER(c.nome) LIKE '%DIVIDA%' OR UPPER(s.nome) LIKE '%DIVIDA%') 
                    AND t.usuario_id=%s
                    GROUP BY t.subconta_id, s.nome, t.descricao
                    ORDER BY s.nome, t.descricao
                """, (uid,))
                dividas = cur.fetchall()

            lista_dividas.controls = []

            if not dividas:
                lista_dividas.controls = [ft.Text("Nenhuma dívida cadastrada.", color="grey", italic=True, size=13)]
                resumo_row.controls = []
                page.update()
                return

            total_pago = 0.0
            for d in dividas:
                pago = float(d["total_pago"] or 0)
                total_pago += pago
                lista_dividas.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Column([
                                ft.Text(d["descricao"] or d["tipo"], size=13, weight="bold"),
                                ft.Text(d["tipo"], size=11, color="grey"),
                            ], expand=True),
                            ft.Column([
                                ft.Text("Total pago", size=10, color="grey"),
                                ft.Text(fmt(pago), size=13, weight="bold", color="#C62828"),
                            ], horizontal_alignment=ft.CrossAxisAlignment.END),
                            ft.Column([
                                ft.Text("Parcelas pagas", size=10, color="grey"),
                                ft.Text(str(d["parcelas_pagas"]), size=13, weight="bold"),
                            ], horizontal_alignment=ft.CrossAxisAlignment.END),
                            ft.Column([
                                ft.Text("Última parcela", size=10, color="grey"),
                                ft.Text(d["ultima_data"] or "—", size=11),
                            ], horizontal_alignment=ft.CrossAxisAlignment.END),
                        ], alignment="spaceBetween", vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ], spacing=4),
                    padding=ft.padding.symmetric(vertical=10, horizontal=14),
                    border=ft.border.all(1, "#E0E0E0"),
                    border_radius=10,
                    bgcolor=ft.colors.WHITE,
                    shadow=ft.BoxShadow(blur_radius=3, color=ft.colors.BLACK12),
                ))

            resumo_row.controls = [
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("💸 TOTAL PAGO", size=11, weight="bold", color=ft.colors.WHITE),
                            ft.Icon(ft.icons.PAYMENTS, size=16, color=ft.colors.WHITE),
                        ], alignment="spaceBetween"),
                        ft.Text(fmt(total_pago), size=20, weight="bold", color=ft.colors.WHITE),
                        ft.Text("soma de todas as dívidas pagas", size=10, color=ft.colors.WHITE70),
                    ], spacing=6),
                    padding=16, bgcolor="#C62828", border_radius=12, width=260,
                    shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26),
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("📋 TIPOS DE DÍVIDA", size=11, weight="bold", color=ft.colors.WHITE),
                            ft.Icon(ft.icons.LIST_ALT, size=16, color=ft.colors.WHITE),
                        ], alignment="spaceBetween"),
                        ft.Text(str(len(dividas)), size=28, weight="bold", color=ft.colors.WHITE),
                        ft.Text("dívidas registradas", size=10, color=ft.colors.WHITE70),
                    ], spacing=6),
                    padding=16, bgcolor="#1565C0", border_radius=12, width=260,
                    shadow=ft.BoxShadow(blur_radius=8, color=ft.colors.BLACK26),
                ),
            ]
            page.update()
        except Exception as ex:
            print(f"[dividas] carregar_dividas: {ex}")

    def registrar_parcela(e):
        try:
            if not dd_subconta.value:
                msg_form.value = "❌ Selecione o tipo de dívida."
                msg_form.color = ft.colors.RED_700
                page.update()
                return

            valor = limpar_valor(tf_total.value)
            if valor <= 0:
                msg_form.value = "❌ Informe o valor da parcela."
                msg_form.color = ft.colors.RED_700
                page.update()
                return

            descricao = tf_descricao.value.strip() or "Parcela dívida"
            data_str = hoje.strftime("%d/%m/%Y")

            with db_session() as cur:
                cur.execute("""
                    INSERT INTO transacoes (usuario_id, subconta_id, tipo, valor, data, descricao)
                    VALUES (%s, %s, 'Despesa', %s, %s, %s)
                """, (uid, int(dd_subconta.value), valor, data_str, descricao))

            msg_form.value = f"✅ Parcela de {fmt(valor)} registrada!"
            msg_form.color = ft.colors.GREEN_700

            # Limpa Campos
            tf_total.value = tf_descricao.value = tf_parcelas.value = ""
            tf_pago.value = tf_vencimento.value = tf_taxa.value = ""
            dd_subconta.value = None

            carregar_dividas()
            page.update()
        except Exception as ex:
            print(f"[dividas] registrar_parcela: {ex}")
            msg_form.value = f"❌ Erro: {ex}"
            msg_form.color = ft.colors.RED_700
            page.update()

    # Carga Inicial
    carregar_subcontas()
    carregar_dividas()

    def secao(titulo, subtitulo, conteudo):
        return ft.Container(
            content=ft.Column([
                ft.Text(titulo, weight="bold", size=14, color="#C62828"),
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
                    secao(
                        "➕ REGISTRAR PAGAMENTO DE PARCELA",
                        "Registra uma parcela paga como transação de despesa",
                        ft.Column([
                            ft.Row([dd_subconta, tf_descricao, tf_total, tf_vencimento], spacing=10, wrap=True),
                            ft.Row([tf_parcelas, tf_pago, tf_taxa,
                                    ft.ElevatedButton("REGISTRAR PARCELA", icon=ft.icons.SAVE,
                                                      bgcolor="#C62828", color=ft.colors.WHITE,
                                                      on_click=registrar_parcela)], spacing=10, wrap=True),
                            msg_form,
                        ], spacing=10),
                    ),
                    ft.Divider(height=8, color="transparent"),
                    secao("📋 DÍVIDAS REGISTRADAS", "Histórico de parcelas pagas por categoria", lista_dividas),
                    ft.Divider(height=16, color="transparent"),
                ], scroll=ft.ScrollMode.ALWAYS, expand=True),
            ),
        ],
    )