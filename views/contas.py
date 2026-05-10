import flet as ft
from menu import get_menu
from database import get_connection, get_cursor
from utils import verificar_admin, limpar_valor, formatar_moeda_input


def contas_view(page: ft.Page):
    uid   = page.session.get("user_id")
    state = {"editing_id": None}

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
                SELECT s.id, s.nome, c.tipo, s.categoria_id, s.fixa, s.orcamento, c.nome as cat_nome
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

    tabela = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Subconta")),
            ft.DataColumn(ft.Text("Conta Pai")),
            ft.DataColumn(ft.Text("Tipo")),
            ft.DataColumn(ft.Text("Fixa")),
            ft.DataColumn(ft.Text("Orçamento")),
            ft.DataColumn(ft.Text("Ações")),
        ],
        rows=[],
    )

    msg = ft.Text("", size=13)

    def atualizar_tabela():
        tabela.rows.clear()
        for s in obter_subcontas():
            cor = ft.colors.GREEN_700 if s["tipo"] == "Receita" else ft.colors.RED_700
            orc = fmt(s["orcamento"]) if s["orcamento"] else "-"
            tabela.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(s["nome"])),
                ft.DataCell(ft.Text(s["cat_nome"])),
                ft.DataCell(ft.Text(s["tipo"], color=cor)),
                ft.DataCell(ft.Icon(
                    ft.icons.CHECK_CIRCLE if s["fixa"] else ft.icons.REMOVE,
                    color=ft.colors.BLUE_600 if s["fixa"] else ft.colors.GREY_400,
                    size=18,
                )),
                ft.DataCell(ft.Text(orc, color=ft.colors.BLUE_700, weight="bold")),
                ft.DataCell(ft.Row([
                    ft.TextButton("Alterar", on_click=lambda _, d=s: preparar_edicao(d)),
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

    def preparar_edicao(s):
        state["editing_id"] = s["id"]
        n_s.value   = s["nome"]
        sel_p.value = str(s["categoria_id"])
        fix.value   = bool(s["fixa"])
        orc.value   = f"{s['orcamento']:_.2f}".replace(".", ",").replace("_", ".") if s["orcamento"] else ""
        btn_sub.text = "CONFIRMAR ALTERAÇÃO"
        btn_cancelar.visible = True
        msg.value = ""
        page.update()

    def cancelar_edicao(e):
        state["editing_id"] = None
        n_s.value = ""
        orc.value = ""
        fix.value = False
        btn_sub.text = "SALVAR SUBCONTA"
        btn_cancelar.visible = False
        msg.value = ""
        page.update()

    n_p = ft.TextField(label="Nome Conta Pai", width=280)
    t_p = ft.Dropdown(
        label="Tipo", width=140,
        options=[ft.dropdown.Option("Despesa"), ft.dropdown.Option("Receita")]
    )

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
            sel_p.options = [
                ft.dropdown.Option(key=str(c["id"]), text=f"{c['nome']} ({c['tipo']})")
                for c in obter_categorias()
            ]
            msg.value = "✅ Conta pai criada."
            atualizar_tabela()
        except Exception as ex:
            print(f"[contas] salvar_pai: {ex}")
            msg.value = "❌ Erro ao criar conta pai."
            page.update()

    sel_p = ft.Dropdown(
        label="Vincular à Conta Pai", width=280,
        options=[
            ft.dropdown.Option(key=str(c["id"]), text=f"{c['nome']} ({c['tipo']})")
            for c in obter_categorias()
        ]
    )
    n_s = ft.TextField(label="Nome Subconta", width=280)
    fix = ft.Checkbox(label="Fixa?")
    orc = ft.TextField(label="Orçamento mensal (ex: 500,00)", width=220, on_blur=formatar_moeda_input)
    btn_sub      = ft.ElevatedButton("SALVAR SUBCONTA", bgcolor="blue", color="white",
                                     on_click=lambda e: salvar_sub(e))
    btn_cancelar = ft.ElevatedButton("CANCELAR", bgcolor="grey", color="white",
                                     on_click=cancelar_edicao, visible=False)

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

            if state["editing_id"] is None:
                cur.execute(
                    "INSERT INTO subcontas (usuario_id, categoria_id, nome, fixa, orcamento) VALUES (%s,%s,%s,%s,%s)",
                    (uid, int(sel_p.value), n_s.value.strip().upper(), fixa_val, orc_val)
                )
                msg.value = "✅ Subconta criada."
            else:
                cur.execute(
                    "UPDATE subcontas SET categoria_id=%s, nome=%s, fixa=%s, orcamento=%s WHERE id=%s AND usuario_id=%s",
                    (int(sel_p.value), n_s.value.strip().upper(), fixa_val, orc_val,
                     state["editing_id"], uid)
                )
                msg.value = "✅ Subconta atualizada."
                state["editing_id"] = None
                btn_sub.text = "SALVAR SUBCONTA"
                btn_cancelar.visible = False
            conn.commit()
            conn.close()
            n_s.value = ""
            orc.value = ""
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
                                    ft.ElevatedButton("CRIAR PAI", bgcolor="teal", color="white",
                                                      on_click=salvar_pai)]),
                        ], spacing=8),
                        padding=14, bgcolor="#F5F5F5", border_radius=8,
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Subconta", weight="bold", size=13),
                            ft.Row([sel_p, n_s, fix, btn_sub, btn_cancelar], wrap=True),
                            ft.Row([orc], wrap=True),
                        ], spacing=8),
                        padding=14, bgcolor="#F5F5F5", border_radius=8,
                    ),
                    msg,
                    ft.Divider(),
                    tabela,
                ], spacing=14, scroll=ft.ScrollMode.ALWAYS, expand=True)
            )
        ]
    )