import flet as ft
from datetime import datetime
from menu import get_menu
from database import get_connection, get_cursor
from utils import formatar_moeda_input, limpar_valor


def fixas_view(page: ft.Page):
    uid = page.session.get("user_id")
    hoje = datetime.now()
    mes = hoje.strftime("%m/%Y")

    try:
        conn = get_connection()
        cur  = get_cursor(conn)
        # ✅ Ordena pelo dia_vencimento
        cur.execute("""
            SELECT s.id, s.nome, s.dia_vencimento
            FROM subcontas s
            WHERE s.fixa=1 AND s.usuario_id=%s
            ORDER BY COALESCE(s.dia_vencimento, 99), s.nome
        """, (uid,))
        subs = cur.fetchall()
        cur.execute("SELECT subconta_id FROM transacoes WHERE data LIKE %s AND usuario_id=%s", (f"%/{mes}", uid))
        pagos = {r["subconta_id"] for r in cur.fetchall()}
        cur.execute("SELECT id, nome_banco FROM bancos WHERE usuario_id=%s ORDER BY nome_banco", (uid,))
        bancos = cur.fetchall()
        conn.close()
    except Exception as ex:
        print(f"[fixas] carregar: {ex}")
        subs, pagos, bancos = [], set(), []

    opcoes_banco = [ft.dropdown.Option("", "— Banco —")] + [
        ft.dropdown.Option(str(b["id"]), b["nome_banco"]) for b in bancos
    ]

    # ✅ Banco único persistente para todas as contas fixas
    banco_geral_dd = ft.Dropdown(
        label="🏦 Banco para todas as contas",
        width=280,
        options=opcoes_banco,
        value="",
    )

    campos = []
    for s in subs:
        if s["id"] not in pagos:
            # ✅ Data preenchida com o dia de vencimento se disponível
            if s["dia_vencimento"]:
                try:
                    data_default = hoje.replace(day=s["dia_vencimento"]).strftime("%d/%m/%Y")
                except:
                    data_default = hoje.strftime("%d/%m/%Y")
            else:
                data_default = hoje.strftime("%d/%m/%Y")

            v_f    = ft.TextField(label="Valor", width=130, on_blur=formatar_moeda_input)
            d_f    = ft.TextField(label="Descrição", value=s["nome"], width=200)
            data_f = ft.TextField(label="Data", value=data_default, width=120, read_only=True)

            # DatePicker para cada linha
            def make_date_picker(data_field):
                dp = ft.DatePicker(
                    first_date=datetime(2020, 1, 1),
                    last_date=datetime(2030, 12, 31),
                    on_change=lambda e, df=data_field: (
                        setattr(df, "value", e.control.value.strftime("%d/%m/%Y")),
                        page.update()
                    ) if e.control.value else None
                )
                page.overlay.append(dp)
                return dp

            dp = make_date_picker(data_f)
            btn_cal = ft.IconButton(
                icon=ft.icons.CALENDAR_TODAY,
                icon_color="#1565C0",
                icon_size=18,
                on_click=lambda e, d=dp: (setattr(d, "open", True), page.update()),
                tooltip="Selecionar data"
            )

            venc_label = f"Dia {s['dia_vencimento']}" if s["dia_vencimento"] else ""

            campos.append(ft.Row([
                ft.Checkbox(label=s["nome"], width=180),
                ft.Text(venc_label, size=11, color=ft.colors.ORANGE_700, width=50),
                v_f, d_f,
                ft.Row([data_f, btn_cal], spacing=2),
                ft.Text(str(s["id"]), visible=False),
            ], spacing=8))

    msg = ft.Text("", size=13)

    def baixar(e):
        msg.value = ""
        selecionados = [r for r in campos if r.controls[0].value and r.controls[2].value]
        if not selecionados:
            msg.value = "⚠️ Selecione ao menos uma conta e informe o valor."
            page.update()
            return

        banco_id = banco_geral_dd.value or None
        banco_id = int(banco_id) if banco_id else None

        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            for r in selecionados:
                sid   = int(r.controls[5].value)
                v     = limpar_valor(r.controls[2].value)
                desc  = r.controls[3].value
                # ✅ Pega a data do campo data_f (index 4 é o Row com data_f e btn)
                data_row = r.controls[4]
                data  = data_row.controls[0].value  # data_f.value
                cur.execute("""
                    SELECT c.tipo FROM categorias c
                    JOIN subcontas s ON s.categoria_id = c.id
                    WHERE s.id=%s
                """, (sid,))
                row  = cur.fetchone()
                tipo = row["tipo"] if row else "Despesa"
                cur.execute("""
                    INSERT INTO transacoes (usuario_id, data, valor, subconta_id, tipo, descricao, banco_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (uid, data, v, sid, tipo, desc, banco_id))
            conn.commit()
            conn.close()
            page.go("/")
        except Exception as ex:
            print(f"[fixas] baixar: {ex}")
            msg.value = "❌ Erro ao salvar. Tente novamente."
            page.update()

    pendentes = ft.Column(
        campos,
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
        height=450,
    ) if campos else ft.Text(
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
                expand=True,
                content=ft.Column([
                    ft.Text(f"CONTAS FIXAS — {mes}", size=18, weight="bold", color="blue"),
                    ft.Text("Selecione as contas pagas, informe o valor e a data:", size=13),
                    ft.Divider(),
                    ft.Container(
                        bgcolor="#E3F2FD", border_radius=8, padding=10,
                        content=ft.Row([
                            ft.Icon(ft.icons.INFO_OUTLINE, color="#1565C0", size=16),
                            ft.Text("O banco abaixo vale para todas as contas baixadas.",
                                    size=12, color="#1565C0", italic=True),
                        ], spacing=8)
                    ),
                    banco_geral_dd,
                    ft.Divider(),
                    # Cabeçalho
                    ft.Row([
                        ft.Text("Conta", size=12, weight="bold", width=180),
                        ft.Text("Venc.", size=12, weight="bold", width=50, color=ft.colors.ORANGE_700),
                        ft.Text("Valor", size=12, weight="bold", width=130),
                        ft.Text("Descrição", size=12, weight="bold", width=200),
                        ft.Text("Data Pagamento", size=12, weight="bold"),
                    ], spacing=8),
                    ft.Divider(height=4),
                    pendentes,
                    msg,
                    ft.ElevatedButton(
                        "BAIXAR SELECIONADAS", icon=ft.icons.CHECK_CIRCLE,
                        bgcolor="blue", color="white", height=45,
                        on_click=baixar
                    ) if campos else ft.Container(),
                ], spacing=14)
            )
        ]
    )