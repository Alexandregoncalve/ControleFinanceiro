import flet as ft
from menu import get_menu
from database import get_connection, get_cursor
from utils import verificar_admin, limpar_valor, formatar_moeda_input


def contas_view(page: ft.Page):
    uid = page.session.get("user_id")

    # Campos de Entrada - Nova Conta Pai
    n_p = ft.TextField(label="Nome da Categoria (ex: LAZER)", width=300, border_radius=10)
    t_p = ft.Dropdown(
        label="Tipo", width=150, border_radius=10,
        options=[ft.dropdown.Option("Receita"), ft.dropdown.Option("Despesa")]
    )

    # Campos de Entrada - Nova Subconta
    sel_p = ft.Dropdown(label="Selecionar Conta Pai", width=300, border_radius=10)
    n_s = ft.TextField(label="Nome da Subconta (ex: CINEMA)", width=300, border_radius=10)
    fix = ft.Checkbox(label="Conta Fixa?", value=False)
    orc = ft.TextField(label="Meta de Orçamento (Opcional)", width=220, border_radius=10, on_blur=formatar_moeda_input)

    msg = ft.Text("", size=14, weight="bold")

    tabela = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Conta Pai")),
            ft.DataColumn(ft.Text("Subconta")),
            ft.DataColumn(ft.Text("Tipo")),
            ft.DataColumn(ft.Text("Orçamento")),
            ft.DataColumn(ft.Text("Ações")),
        ],
        rows=[]
    )

    def carregar_combos():
        try:
            conn = get_connection()
            cur = get_cursor(conn)
            cur.execute("SELECT id, nome FROM categorias WHERE usuario_id=%s ORDER BY nome", (uid,))
            rows = cur.fetchall()
            conn.close()

            sel_p.options = [ft.dropdown.Option(key=str(r["id"]), text=r["nome"]) for r in rows]
            page.update()
        except Exception as e:
            print(f"Erro carregar_combos: {e}")

    def carregar_tabela():
        try:
            conn = get_connection()
            cur = get_cursor(conn)
            cur.execute("""
                SELECT s.id, s.nome as sub_nome, c.nome as cat_nome, c.tipo, s.orcamento 
                FROM subcontas s 
                JOIN categorias c ON s.categoria_id = c.id 
                WHERE s.usuario_id=%s 
                ORDER BY c.nome, s.nome
            """, (uid,))
            rows = cur.fetchall()
            conn.close()

            tabela.rows.clear()
            for r in rows:
                tabela.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(r["cat_nome"])),
                        ft.DataCell(ft.Text(r["sub_nome"])),
                        ft.DataCell(ft.Text(r["tipo"])),
                        ft.DataCell(
                            ft.Text(f"R$ {r['orcamento']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))),
                        ft.DataCell(
                            ft.IconButton(
                                ft.icons.DELETE_OUTLINE,
                                icon_color="red",
                                on_click=lambda _, sid=r["id"]: confirmar_exclusao(sid)
                            )
                        ),
                    ])
                )
            page.update()
        except Exception as e:
            print(f"Erro carregar_tabela: {e}")

    def salvar_pai(e):
        if not n_p.value or not t_p.value:
            msg.value = "⚠️ Preencha o nome e o tipo da Conta Pai!"
            msg.color = "red"
            page.update()
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO categorias (usuario_id, nome, tipo) VALUES (%s, %s, %s)",
                (uid, n_p.value.upper(), t_p.value)
            )
            conn.commit()
            conn.close()
            n_p.value = ""
            msg.value = "✅ Conta Pai criada!"
            msg.color = "green"
            carregar_combos()
        except Exception as ex:
            msg.value = f"❌ Erro: {ex}"
            page.update()

    def salvar_sub(e):
        if not sel_p.value or not n_s.value:
            msg.value = "⚠️ Selecione a Conta Pai e o nome da Subconta!"
            msg.color = "red"
            page.update()
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            valor_orc = limpar_valor(orc.value)
            cur.execute("""
                INSERT INTO subcontas (usuario_id, categoria_id, nome, fixa, orcamento) 
                VALUES (%s, %s, %s, %s, %s)
            """, (uid, int(sel_p.value), n_s.value.upper(), 1 if fix.value else 0, valor_orc))
            conn.commit()
            conn.close()
            n_s.value = ""
            orc.value = ""
            msg.value = "✅ Subconta salva!"
            msg.color = "green"
            carregar_tabela()
        except Exception as ex:
            msg.value = f"❌ Erro ao salvar: {ex}"
            page.update()

    def confirmar_exclusao(sub_id):
        def deletar():
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM subcontas WHERE id=%s AND usuario_id=%s", (sub_id, uid))
                conn.commit()
                conn.close()
                carregar_tabela()
            except Exception as ex:
                print(f"Erro ao deletar: {ex}")

        verificar_admin(page, deletar)

    # Inicialização da tela
    carregar_combos()
    carregar_tabela()

    return ft.View(
        route="/contas",
        controls=[
            get_menu(page),
            ft.Divider(),
            ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("GERENCIAR PLANO DE CONTAS", size=20, weight="bold", color="blue"),

                    # Seção Conta Pai
                    ft.Container(
                        content=ft.Column([
                            ft.Text("1. Criar Categoria Principal (Conta Pai)", weight="bold"),
                            ft.Row([n_p, t_p, ft.ElevatedButton("CRIAR PAI", bgcolor="teal", color="white",
                                                                on_click=salvar_pai)]),
                        ]),
                        padding=15, bgcolor="#E3F2FD", border_radius=10
                    ),

                    # Seção Subconta
                    ft.Container(
                        content=ft.Column([
                            ft.Text("2. Criar Item de Gasto (Subconta)", weight="bold"),
                            ft.Row([sel_p, n_s, fix], wrap=True),
                            ft.Row([orc, ft.ElevatedButton("SALVAR SUBCONTA", bgcolor="blue", color="white",
                                                           on_click=salvar_sub)]),
                        ]),
                        padding=15, bgcolor="#F5F5F5", border_radius=10
                    ),

                    msg,
                    ft.Divider(),
                    ft.Text("SEU PLANO DE CONTAS ATUAL", weight="bold"),
                    ft.Column([ft.Row([tabela], scroll=ft.ScrollMode.ALWAYS)], scroll=ft.ScrollMode.ALWAYS, expand=True)
                ], spacing=15, scroll=ft.ScrollMode.ALWAYS, expand=True)
            )
        ]
    )