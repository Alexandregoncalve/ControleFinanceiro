import flet as ft
from menu import get_menu
from database import get_connection


# Paleta de cores para os cards de banco
CORES_BANCO = [
    "#1565C0",  # Azul
    "#2E7D32",  # Verde
    "#6A1B9A",  # Roxo
    "#00838F",  # Ciano
    "#E65100",  # Laranja
    "#AD1457",  # Rosa
    "#4527A0",  # Índigo
    "#37474F",  # Cinza escuro
]


def bancos_view(page: ft.Page):
    state = {"editing_banco_id": None, "editing_cartao_id": None}

    nome_banco_f    = ft.TextField(label="Nome do Banco", width=250)
    saldo_inicial_f = ft.TextField(label="Saldo Inicial (ex: 1.500,00)", width=200)
    msg_banco       = ft.Text("", size=13)

    nome_cartao_f = ft.TextField(label="Nome do Cartão", width=200)
    tipo_cartao_f = ft.Dropdown(
        label="Tipo", width=150,
        options=[
            ft.dropdown.Option("Crédito"),
            ft.dropdown.Option("Débito"),
            ft.dropdown.Option("Ambos"),
        ]
    )
    limite_f   = ft.TextField(label="Limite (ex: 5.000,00)", width=180)
    banco_dd   = ft.Dropdown(label="Banco vinculado", width=220, options=[])
    msg_cartao = ft.Text("", size=13)

    lista_bancos_col  = ft.Column([], spacing=12)
    lista_cartoes_col = ft.Column([], spacing=12)

    def limpar_valor(v):
        try:
            return float(v.replace(".", "").replace(",", "."))
        except Exception:
            return 0.0

    def fmt(v):
        return f"R$ {v:_.2f}".replace(".", ",").replace("_", ".")

    def carregar_banco_dd():
        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute("SELECT id, nome_banco FROM bancos ORDER BY nome_banco")
            bancos = cur.fetchall()
            conn.close()
            banco_dd.options = [ft.dropdown.Option(str(b["id"]), b["nome_banco"]) for b in bancos]
            page.update()
        except Exception as ex:
            print(f"[bancos] carregar_banco_dd: {ex}")

    def card_banco(b, cor):
        return ft.Container(
            width=280,
            border_radius=14,
            bgcolor=cor,
            padding=ft.padding.all(18),
            shadow=ft.BoxShadow(
                blur_radius=10,
                color=ft.colors.with_opacity(0.22, "black"),
                offset=ft.Offset(2, 4)
            ),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.ACCOUNT_BALANCE, color="white", size=28),
                    ft.Text(b["nome_banco"], color="white", weight="bold", size=16, expand=True),
                ], spacing=10),
                ft.Divider(color=ft.colors.with_opacity(0.3, "white"), height=18),
                ft.Text("Saldo Inicial", color=ft.colors.with_opacity(0.75, "white"), size=11),
                ft.Text(fmt(b["saldo_inicial"] or 0), color="white", size=20, weight="bold"),
                ft.Divider(color=ft.colors.with_opacity(0.3, "white"), height=18),
                ft.Row([
                    ft.TextButton(
                        "✏️ Editar",
                        style=ft.ButtonStyle(color="white"),
                        on_click=lambda _, b=b: preparar_edicao_banco(b)
                    ),
                    ft.TextButton(
                        "🗑️ Excluir",
                        style=ft.ButtonStyle(color=ft.colors.RED_200),
                        on_click=lambda _, bid=b["id"]: excluir_banco(bid)
                    ),
                ], alignment=ft.MainAxisAlignment.END),
            ], spacing=4),
        )

    def card_cartao(c, banco_map):
        tipo_cor = {
            "Crédito": "#E65100",
            "Débito":  "#2E7D32",
            "Ambos":   "#6A1B9A",
        }.get(c["tipo"], "#37474F")

        return ft.Container(
            width=280,
            border_radius=14,
            bgcolor=tipo_cor,
            padding=ft.padding.all(18),
            shadow=ft.BoxShadow(
                blur_radius=10,
                color=ft.colors.with_opacity(0.22, "black"),
                offset=ft.Offset(2, 4)
            ),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.CREDIT_CARD, color="white", size=28),
                    ft.Text(c["nome_cartao"], color="white", weight="bold", size=16, expand=True),
                ], spacing=10),
                ft.Container(
                    bgcolor=ft.colors.with_opacity(0.2, "white"),
                    border_radius=6,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    content=ft.Text(c["tipo"], color="white", size=11, weight="bold"),
                ),
                ft.Divider(color=ft.colors.with_opacity(0.3, "white"), height=18),
                ft.Row([
                    ft.Column([
                        ft.Text("Limite", color=ft.colors.with_opacity(0.75, "white"), size=11),
                        ft.Text(fmt(c["limite"] or 0), color="white", size=16, weight="bold"),
                    ]),
                    ft.Column([
                        ft.Text("Banco", color=ft.colors.with_opacity(0.75, "white"), size=11),
                        ft.Text(banco_map.get(c["banco_id"], "—"), color="white", size=13),
                    ]),
                ], spacing=30),
                ft.Divider(color=ft.colors.with_opacity(0.3, "white"), height=18),
                ft.Row([
                    ft.TextButton(
                        "✏️ Editar",
                        style=ft.ButtonStyle(color="white"),
                        on_click=lambda _, c=c: preparar_edicao_cartao(c)
                    ),
                    ft.TextButton(
                        "🗑️ Excluir",
                        style=ft.ButtonStyle(color=ft.colors.RED_200),
                        on_click=lambda _, cid=c["id"]: excluir_cartao(cid)
                    ),
                ], alignment=ft.MainAxisAlignment.END),
            ], spacing=4),
        )

    def carregar_listas():
        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute("SELECT id, nome_banco, saldo_inicial FROM bancos ORDER BY nome_banco")
            bancos = cur.fetchall()
            cur.execute("SELECT id, nome_cartao, tipo, limite, banco_id FROM cartoes ORDER BY nome_cartao")
            cartoes = cur.fetchall()
            conn.close()

            banco_map = {b["id"]: b["nome_banco"] for b in bancos}

            # Cards banco com cores rotativas
            lista_bancos_col.controls.clear()
            lista_bancos_col.controls.append(
                ft.Row(
                    [card_banco(b, CORES_BANCO[i % len(CORES_BANCO)]) for i, b in enumerate(bancos)]
                    if bancos else
                    [ft.Text("Nenhum banco cadastrado.", color=ft.colors.GREY_500, italic=True)],
                    wrap=True, spacing=16
                )
            )

            # Cards cartão
            lista_cartoes_col.controls.clear()
            lista_cartoes_col.controls.append(
                ft.Row(
                    [card_cartao(c, banco_map) for c in cartoes]
                    if cartoes else
                    [ft.Text("Nenhum cartão cadastrado.", color=ft.colors.GREY_500, italic=True)],
                    wrap=True, spacing=16
                )
            )

            carregar_banco_dd()
            page.update()

        except Exception as ex:
            print(f"[bancos] carregar_listas: {ex}")

    # ── BANCO ─────────────────────────────────────────────────
    def salvar_banco(e):
        nome  = nome_banco_f.value.strip()
        saldo = limpar_valor(saldo_inicial_f.value.strip() or "0")
        if not nome:
            msg_banco.value = "⚠️ Informe o nome do banco."
            msg_banco.color = ft.colors.ORANGE_700
            page.update()
            return
        try:
            conn = get_connection()
            if state["editing_banco_id"]:
                conn.execute(
                    "UPDATE bancos SET nome_banco=?, saldo_inicial=? WHERE id=?",
                    (nome, saldo, state["editing_banco_id"])
                )
                msg_banco.value = "✅ Banco atualizado!"
                state["editing_banco_id"] = None
            else:
                conn.execute(
                    "INSERT INTO bancos (nome_banco, saldo_inicial) VALUES (?, ?)",
                    (nome, saldo)
                )
                msg_banco.value = "✅ Banco cadastrado!"
            conn.commit()
            conn.close()
            msg_banco.color       = ft.colors.GREEN_700
            nome_banco_f.value    = saldo_inicial_f.value = ""
            btn_salvar_banco.text = "SALVAR BANCO"
            carregar_listas()
        except Exception as ex:
            print(f"[bancos] salvar_banco: {ex}")
            msg_banco.value = "❌ Erro ao salvar banco."
            msg_banco.color = ft.colors.RED_700
            page.update()

    def preparar_edicao_banco(b):
        state["editing_banco_id"] = b["id"]
        nome_banco_f.value        = b["nome_banco"]
        saldo_inicial_f.value     = f'{b["saldo_inicial"] or 0:_.2f}'.replace(".", ",").replace("_", ".")
        btn_salvar_banco.text     = "ATUALIZAR BANCO"
        msg_banco.value = ""
        page.update()

    def excluir_banco(bid):
        try:
            conn = get_connection()
            conn.execute("DELETE FROM bancos WHERE id=?", (bid,))
            conn.commit()
            conn.close()
            carregar_listas()
        except Exception as ex:
            print(f"[bancos] excluir_banco: {ex}")

    # ── CARTÃO ────────────────────────────────────────────────
    def salvar_cartao(e):
        nome   = nome_cartao_f.value.strip()
        tipo   = tipo_cartao_f.value
        limite = limpar_valor(limite_f.value.strip() or "0")
        bid    = banco_dd.value
        if not nome or not tipo or not bid:
            msg_cartao.value = "⚠️ Preencha nome, tipo e banco."
            msg_cartao.color = ft.colors.ORANGE_700
            page.update()
            return
        try:
            conn = get_connection()
            if state["editing_cartao_id"]:
                conn.execute(
                    "UPDATE cartoes SET nome_cartao=?, tipo=?, limite=?, banco_id=? WHERE id=?",
                    (nome, tipo, limite, int(bid), state["editing_cartao_id"])
                )
                msg_cartao.value = "✅ Cartão atualizado!"
                state["editing_cartao_id"] = None
            else:
                conn.execute(
                    "INSERT INTO cartoes (nome_cartao, tipo, limite, banco_id) VALUES (?, ?, ?, ?)",
                    (nome, tipo, limite, int(bid))
                )
                msg_cartao.value = "✅ Cartão cadastrado!"
            conn.commit()
            conn.close()
            msg_cartao.color       = ft.colors.GREEN_700
            nome_cartao_f.value    = limite_f.value = ""
            tipo_cartao_f.value    = banco_dd.value = None
            btn_salvar_cartao.text = "SALVAR CARTÃO"
            carregar_listas()
        except Exception as ex:
            print(f"[bancos] salvar_cartao: {ex}")
            msg_cartao.value = "❌ Erro ao salvar cartão."
            msg_cartao.color = ft.colors.RED_700
            page.update()

    def preparar_edicao_cartao(c):
        state["editing_cartao_id"] = c["id"]
        nome_cartao_f.value        = c["nome_cartao"]
        tipo_cartao_f.value        = c["tipo"]
        limite_f.value             = f'{c["limite"] or 0:_.2f}'.replace(".", ",").replace("_", ".")
        banco_dd.value             = str(c["banco_id"])
        btn_salvar_cartao.text     = "ATUALIZAR CARTÃO"
        msg_cartao.value = ""
        page.update()

    def excluir_cartao(cid):
        try:
            conn = get_connection()
            conn.execute("DELETE FROM cartoes WHERE id=?", (cid,))
            conn.commit()
            conn.close()
            carregar_listas()
        except Exception as ex:
            print(f"[bancos] excluir_cartao: {ex}")

    btn_salvar_banco  = ft.ElevatedButton("SALVAR BANCO",  bgcolor="#1565C0", color="white", on_click=salvar_banco)
    btn_salvar_cartao = ft.ElevatedButton("SALVAR CARTÃO", bgcolor="#E65100", color="white", on_click=salvar_cartao)

    carregar_listas()

    # Conteúdo rolável separado do menu
    conteudo = ft.Column([
        ft.Row([
            ft.Icon(ft.icons.ACCOUNT_BALANCE, color="#1565C0", size=30),
            ft.Text("BANCOS E CARTÕES", size=22, weight="bold", color="#1565C0"),
        ], spacing=10),
        ft.Divider(),

        # ── Formulário Banco ──
        ft.Container(
            bgcolor="#E3F2FD",
            border_radius=10,
            padding=16,
            content=ft.Column([
                ft.Text("🏦 Cadastrar / Editar Banco", size=15, weight="bold", color="#1565C0"),
                ft.Row([nome_banco_f, saldo_inicial_f, btn_salvar_banco], wrap=True, spacing=10),
                msg_banco,
            ], spacing=10)
        ),

        ft.Text("Bancos Cadastrados", size=15, weight="bold", color="#1565C0"),
        lista_bancos_col,
        ft.Divider(),

        # ── Formulário Cartão ──
        ft.Container(
            bgcolor="#FFF3E0",
            border_radius=10,
            padding=16,
            content=ft.Column([
                ft.Text("💳 Cadastrar / Editar Cartão", size=15, weight="bold", color="#E65100"),
                ft.Row([nome_cartao_f, tipo_cartao_f, limite_f, banco_dd, btn_salvar_cartao], wrap=True, spacing=10),
                msg_cartao,
            ], spacing=10)
        ),

        ft.Text("Cartões Cadastrados", size=15, weight="bold", color="#E65100"),
        lista_cartoes_col,

    ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)

    return ft.View(
        route="/bancos",
        controls=[
            # Menu fixo no topo — fora do scroll
            get_menu(page),
            ft.Divider(),
            # Conteúdo com scroll próprio
            ft.Container(
                padding=ft.padding.symmetric(horizontal=24, vertical=16),
                expand=True,
                content=conteudo,
            ),
        ]
    )