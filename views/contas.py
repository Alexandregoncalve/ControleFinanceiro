import flet as ft
from menu import get_menu
from database import get_connection, get_cursor
from utils import verificar_admin, limpar_valor, formatar_moeda_input


def contas_view(page: ft.Page):
    uid = page.session.get("user_id")

    def obter_categorias():
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("SELECT id, nome, tipo FROM categorias WHERE usuario_id=%s ORDER BY tipo, nome", (uid,))
            rows = cur.fetchall()
            conn.close()
            return rows
        except Exception as ex:
            print(f"[contas] obter_categorias: {ex}")
            return []

    def obter_subcontas():
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("""
                SELECT s.id, s.nome, c.tipo, s.categoria_id, s.fixa, s.orcamento,
                       c.nome as cat_nome, s.dia_vencimento
                FROM subcontas s
                JOIN categorias c ON s.categoria_id = c.id
                WHERE s.usuario_id=%s ORDER BY c.nome, s.nome
            """, (uid,))
            rows = cur.fetchall()
            conn.close()
            return rows
        except Exception as ex:
            print(f"[contas] obter_subcontas: {ex}")
            return []

    def fmt(v):
        return f"R$ {v:_.2f}".replace(".", ",").replace("_", ".")

    msg = ft.Text("", size=13)

    tabela = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Subconta")),
            ft.DataColumn(ft.Text("Conta Pai")),
            ft.DataColumn(ft.Text("Tipo")),
            ft.DataColumn(ft.Text("Fixa")),
            ft.DataColumn(ft.Text("Vencimento")),
            ft.DataColumn(ft.Text("Orçamento")),
            ft.DataColumn(ft.Text("Ações")),
        ],
        rows=[],
    )

    # ── Modal de edição ───────────────────────────────────────────────────
    modal_state    = {"id": None}
    modal_nome     = ft.TextField(label="Nome da Subconta", width=320)
    modal_fixa     = ft.Checkbox(label="Fixa?")
    modal_venc     = ft.TextField(label="Dia Vencimento (1-31)", width=160,
                                   keyboard_type=ft.KeyboardType.NUMBER,
                                   hint_text="Ex: 10")
    modal_orc      = ft.TextField(label="Orçamento mensal (ex: 500,00)", width=220, on_blur=formatar_moeda_input)
    modal_msg      = ft.Text("", size=12, color=ft.colors.RED_700)
    modal_pai      = ft.Dropdown(label="Conta Pai", width=320, options=[])

    def fechar_modal(e):
        modal.open = False
        page.update()

    def salvar_modal(e):
        if not modal_nome.value.strip():
            modal_msg.value = "⚠️ Preencha o nome da subconta."
            page.update()
            return
        if not modal_pai.value:
            modal_msg.value = "⚠️ Selecione a conta pai."
            page.update()
            return
        try:
            conn     = get_connection()
            cur      = get_cursor(conn)
            fixa_val = 1 if modal_fixa.value else 0
            orc_val  = limpar_valor(modal_orc.value) if modal_orc.value else 0.0
            venc_val = int(modal_venc.value) if modal_venc.value and modal_venc.value.isdigit() else None
            cur.execute(
                "UPDATE subcontas SET categoria_id=%s, nome=%s, fixa=%s, orcamento=%s, dia_vencimento=%s WHERE id=%s AND usuario_id=%s",
                (int(modal_pai.value), modal_nome.value.strip().upper(),
                 fixa_val, orc_val, venc_val, modal_state["id"], uid)
            )
            conn.commit()
            conn.close()
            modal.open      = False
            msg.value       = "✅ Subconta atualizada!"
            modal_msg.value = ""
            atualizar_tabela()
        except Exception as ex:
            print(f"[contas] salvar_modal: {ex}")
            modal_msg.value = "❌ Erro ao salvar."
            page.update()

    modal = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.icons.EDIT, color="#1565C0"),
            ft.Text("Editar Subconta", size=16, weight="bold", color="#1565C0"),
        ], spacing=8),
        content=ft.Column([
            modal_nome, modal_pai,
            ft.Row([modal_fixa, modal_venc], spacing=16),
            modal_orc, modal_msg,
        ], spacing=14, tight=True, width=340),
        actions=[
            ft.TextButton("CANCELAR", on_click=fechar_modal),
            ft.ElevatedButton("SALVAR ALTERAÇÃO", bgcolor="#1565C0", color="white", on_click=salvar_modal),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(modal)

    def abrir_modal_edicao(s):
        modal_state["id"] = s["id"]
        modal_nome.value  = s["nome"]
        modal_fixa.value  = bool(s["fixa"])
        modal_orc.value   = f"{float(s['orcamento'] or 0):_.2f}".replace(".", ",").replace("_", ".") if s["orcamento"] else ""
        modal_venc.value  = str(s["dia_vencimento"]) if s["dia_vencimento"] else ""
        modal_msg.value   = ""
        modal_pai.options = [
            ft.dropdown.Option(key=str(c["id"]), text=f"{c['nome']} ({c['tipo']})")
            for c in obter_categorias()
        ]
        modal_pai.value = str(s["categoria_id"])
        modal.open = True
        page.update()

    def atualizar_tabela():
        tabela.rows.clear()
        for s in obter_subcontas():
            cor  = ft.colors.GREEN_700 if s["tipo"] == "Receita" else ft.colors.RED_700
            orc  = fmt(float(s["orcamento"] or 0)) if s["orcamento"] else "—"
            venc = f"Dia {s['dia_vencimento']}" if s["dia_vencimento"] else "—"
            tabela.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(s["nome"])),
                ft.DataCell(ft.Text(s["cat_nome"])),
                ft.DataCell(ft.Text(s["tipo"], color=cor)),
                ft.DataCell(ft.Icon(
                    ft.icons.CHECK_CIRCLE if s["fixa"] else ft.icons.REMOVE,
                    color=ft.colors.BLUE_600 if s["fixa"] else ft.colors.GREY_400,
                    size=18,
                )),
                ft.DataCell(ft.Text(venc, color=ft.colors.ORANGE_700 if s["dia_vencimento"] else ft.colors.GREY_400)),
                ft.DataCell(ft.Text(orc, color=ft.colors.BLUE_700, weight="bold")),
                ft.DataCell(ft.Row([
                    ft.TextButton("Alterar", on_click=lambda _, d=s: abrir_modal_edicao(d)),
                    ft.TextButton(
                        "Excluir",
                        style=ft.ButtonStyle(color=ft.colors.RED_700),
                        on_click=lambda _, sid=s["id"]: verificar_admin(page, lambda sid=sid: deletar(sid))
                    ),
                ])),
            ]))
        page.update()

    def deletar(sid):
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("DELETE FROM subcontas WHERE id=%s AND usuario_id=%s", (sid, uid))
            conn.commit()
            conn.close()
            msg.value = "✅ Subconta excluída."
            atualizar_tabela()
        except Exception as ex:
            print(f"[contas] deletar: {ex}")
            msg.value = "❌ Erro ao excluir."
            page.update()

    # ── Formulário Conta Pai ──────────────────────────────────────────────
    n_p = ft.TextField(label="Nome Conta Pai", width=280)
    t_p = ft.Dropdown(label="Tipo", width=140,
                       options=[ft.dropdown.Option("Despesa"), ft.dropdown.Option("Receita")])

    def salvar_pai(e):
        if not n_p.value or not t_p.value:
            msg.value = "⚠️ Preencha nome e tipo da conta pai."
            page.update()
            return
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute(
                "INSERT INTO categorias (usuario_id, nome, tipo) VALUES (%s,%s,%s)",
                (uid, n_p.value.strip().upper(), t_p.value)
            )
            conn.commit()
            conn.close()
            n_p.value = ""
            t_p.value = None
            novas = obter_categorias()
            sel_p.options = [
                ft.dropdown.Option(key=str(c["id"]), text=f"{c['nome']} ({c['tipo']})")
                for c in novas
            ]
            msg.value = "✅ Conta pai criada!"
            sel_p.update()
            msg.update()
            atualizar_tabela()
        except Exception as ex:
            print(f"[contas] salvar_pai: {ex}")
            msg.value = "❌ Erro ao criar conta pai."
            page.update()

    # ── Formulário Nova Subconta ──────────────────────────────────────────
    sel_p = ft.Dropdown(
        label="Vincular à Conta Pai", width=280,
        options=[
            ft.dropdown.Option(key=str(c["id"]), text=f"{c['nome']} ({c['tipo']})")
            for c in obter_categorias()
        ]
    )
    n_s   = ft.TextField(label="Nome Subconta", width=280)
    fix   = ft.Checkbox(label="Fixa?")
    venc  = ft.TextField(label="Dia Vencimento (1-31)", width=160,
                          keyboard_type=ft.KeyboardType.NUMBER, hint_text="Ex: 10")
    orc   = ft.TextField(label="Orçamento mensal (ex: 500,00)", width=220, on_blur=formatar_moeda_input)

    def salvar_sub(e):
        if not n_s.value or not sel_p.value:
            msg.value = "⚠️ Preencha nome e conta pai."
            page.update()
            return
        try:
            conn     = get_connection()
            cur      = get_cursor(conn)
            fixa_val = 1 if fix.value else 0
            orc_val  = limpar_valor(orc.value) if orc.value else 0.0
            venc_val = int(venc.value) if venc.value and venc.value.isdigit() else None
            cur.execute(
                "INSERT INTO subcontas (usuario_id, categoria_id, nome, fixa, orcamento, dia_vencimento) VALUES (%s,%s,%s,%s,%s,%s)",
                (uid, int(sel_p.value), n_s.value.strip().upper(), fixa_val, orc_val, venc_val)
            )
            conn.commit()
            conn.close()
            msg.value = "✅ Subconta criada."
            n_s.value = venc.value = orc.value = ""
            fix.value = False
            atualizar_tabela()
        except Exception as ex:
            print(f"[contas] salvar_sub: {ex}")
            msg.value = "❌ Erro ao salvar subconta."
            page.update()

    atualizar_tabela()

    return ft.View(
        route="/contas",
        controls=[
            get_menu(page),
            ft.Divider(),
            ft.Container(
                padding=20, expand=True,
                content=ft.Column([
                    ft.Text("GERENCIAR CONTAS", size=18, weight="bold", color="blue"),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Nova Conta Pai", weight="bold", size=13),
                            ft.Row([n_p, t_p,
                                    ft.ElevatedButton("CRIAR PAI", bgcolor="teal", color="white", on_click=salvar_pai)]),
                        ], spacing=8),
                        padding=14, bgcolor="#E3F2FD", border_radius=8,
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Nova Subconta", weight="bold", size=13),
                            ft.Row([sel_p, n_s, fix], wrap=True, spacing=10),
                            ft.Row([venc, orc,
                                    ft.ElevatedButton("SALVAR SUBCONTA", bgcolor="blue", color="white", on_click=salvar_sub)],
                                   spacing=10, wrap=True),
                        ], spacing=8),
                        padding=14, bgcolor="#F5F5F5", border_radius=8,
                    ),
                    msg,
                    ft.Divider(),
                    ft.Column(
                        controls=[ft.Row(controls=[tabela], scroll=ft.ScrollMode.ALWAYS)],
                        scroll=ft.ScrollMode.ALWAYS,
                        expand=True,
                    ),
                ], spacing=14, scroll=ft.ScrollMode.ALWAYS, expand=True)
            )
        ]
    )