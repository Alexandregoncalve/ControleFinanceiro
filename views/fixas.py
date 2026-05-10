import flet as ft
from datetime import datetime
from menu import get_menu
from database import get_connection, get_cursor
from utils import formatar_moeda_input, limpar_valor


def fixas_view(page: ft.Page):
    uid = page.session.get("user_id")
    mes = datetime.now().strftime("%m/%Y")

    try:
        conn = get_connection()
        cur  = get_cursor(conn)
        cur.execute("SELECT s.id, s.nome FROM subcontas s WHERE s.fixa=1 AND s.usuario_id=%s ORDER BY s.nome", (uid,))
        subs = cur.fetchall()
        cur.execute("SELECT subconta_id FROM transacoes WHERE data LIKE %s AND usuario_id=%s", (f"%/{mes}", uid))
        pagos = {r["subconta_id"] for r in cur.fetchall()}
        conn.close()
    except Exception as ex:
        print(f"[fixas] carregar: {ex}")
        subs, pagos = [], set()

    campos = []
    for s in subs:
        if s["id"] not in pagos:
            v_f = ft.TextField(label="Valor (ex: R$150,00)", width=150, on_blur=formatar_moeda_input)
            d_f = ft.TextField(label="Descrição", value=s["nome"], width=250)
            campos.append(ft.Row([
                ft.Checkbox(label=s["nome"]),
                v_f, d_f,
                ft.Text(str(s["id"]), visible=False),
            ]))

    msg = ft.Text("", size=13)

    def baixar(e):
        msg.value = ""
        selecionados = [r for r in campos if r.controls[0].value and r.controls[1].value]
        if not selecionados:
            msg.value = "⚠️ Selecione ao menos uma conta e informe o valor."
            page.update()
            return
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            for r in selecionados:
                sid  = int(r.controls[3].value)
                v    = limpar_valor(r.controls[1].value)
                desc = r.controls[2].value
                cur.execute("""
                    SELECT c.tipo FROM categorias c
                    JOIN subcontas s ON s.categoria_id = c.id
                    WHERE s.id=%s
                """, (sid,))
                row  = cur.fetchone()
                tipo = row["tipo"] if row else "Despesa"
                cur.execute("""
                    INSERT INTO transacoes (usuario_id, data, valor, subconta_id, tipo, descricao)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, (uid, datetime.now().strftime("%d/%m/%Y"), v, sid, tipo, desc))
            conn.commit()
            conn.close()
            page.go("/")
        except Exception as ex:
            print(f"[fixas] baixar: {ex}")
            msg.value = "❌ Erro ao salvar. Tente novamente."
            page.update()

    pendentes = ft.Column(campos) if campos else ft.Text(
        "✅ Todas as contas fixas deste mês já foram baixadas!",
        color=ft.colors.GREEN_700, size=14
    )

    return ft.View(
        route="/fixas",
        controls=[
            get_menu(page),
            ft.Divider(),
            ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text(f"CONTAS FIXAS — {mes}", size=18, weight="bold", color="blue"),
                    ft.Text("Selecione as contas pagas e informe o valor:", size=13),
                    ft.Divider(),
                    pendentes, msg,
                    ft.ElevatedButton("BAIXAR SELECIONADAS", icon=ft.icons.CHECK_CIRCLE,
                                      bgcolor="blue", color="white", height=45,
                                      on_click=baixar) if campos else ft.Container(),
                ], spacing=14)
            )
        ]
    )