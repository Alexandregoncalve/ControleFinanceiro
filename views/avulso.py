import flet as ft
from datetime import datetime
from dateutil.relativedelta import relativedelta
from menu import get_menu
from database import get_connection, get_cursor
from utils import formatar_moeda_input, limpar_valor


def avulso_view(page: ft.Page):
    uid = page.session.get("user_id")

    def carregar_subcontas():
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("""
                SELECT s.id, s.nome, c.tipo
                FROM subcontas s
                JOIN categorias c ON s.categoria_id = c.id
                WHERE s.usuario_id=%s ORDER BY c.tipo, s.nome
            """, (uid,))
            rows = cur.fetchall()
            conn.close()
            return rows
        except Exception as ex:
            print(f"[avulso] carregar_subcontas: {ex}")
            return []

    def carregar_bancos():
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("SELECT id, nome_banco FROM bancos WHERE usuario_id=%s ORDER BY nome_banco", (uid,))
            rows = cur.fetchall()
            conn.close()
            return rows
        except Exception as ex:
            print(f"[avulso] carregar_bancos: {ex}")
            return []

    subs   = carregar_subcontas()
    bancos = carregar_bancos()
    state  = {"subconta_id": None, "subconta_nome": "", "cat_real_id": None, "cat_real_nome": ""}

    data_field = ft.TextField(label="Data", width=160, value=datetime.now().strftime("%d/%m/%Y"), read_only=True)

    def ao_selecionar_data(e):
        if date_picker.value:
            data_field.value = date_picker.value.strftime("%d/%m/%Y")
            atualizar_info_parcelas(None)
            page.update()

    date_picker = ft.DatePicker(first_date=datetime(2020, 1, 1), last_date=datetime(2030, 12, 31), on_change=ao_selecionar_data)
    page.overlay.append(date_picker)

    btn_data = ft.ElevatedButton("📅 Selecionar Data", bgcolor=ft.colors.BLUE_100, color=ft.colors.BLUE_900,
                                  on_click=lambda e: setattr(date_picker, "open", True) or page.update())

    # ── BANCO — persiste entre lançamentos ─────────────────────────────────
    opcoes_banco = [ft.dropdown.Option("", "— Selecione o banco —")] + [
        ft.dropdown.Option(str(b["id"]), b["nome_banco"]) for b in bancos
    ]
    banco_dd = ft.Dropdown(
        label="🏦 Banco utilizado", width=220,
        options=opcoes_banco,
        value="",
        hint_text="Banco fica selecionado entre lançamentos"
    )

    parcelas_row   = ft.Row(visible=False)
    parcelas_field = ft.Dropdown(label="Parcelas", width=150, value="1",
                                  options=[ft.dropdown.Option(str(i), f"{i}x") for i in range(1, 13)])
    parcelas_info  = ft.Text("", size=12, color=ft.colors.BLUE_700, italic=True)
    parcelas_row.controls = [parcelas_field, parcelas_info]

    def eh_cartao(nome: str) -> bool:
        return "CARTAO" in nome.upper() or "CARTÃO" in nome.upper()

    def get_data_base() -> datetime:
        try:
            return datetime.strptime(data_field.value, "%d/%m/%Y")
        except Exception:
            return datetime.now()

    def atualizar_info_parcelas(e):
        if not val.value or limpar_valor(val.value) == 0:
            parcelas_info.value = ""
            page.update()
            return
        try:
            total     = limpar_valor(val.value)
            n         = int(parcelas_field.value or 1)
            parcela   = total / n
            fmt_v     = lambda v: f"R$ {v:_.2f}".replace(".", ",").replace("_", ".")
            data_base = get_data_base()
            datas     = []
            for i in range(1, n + 1):
                dt = data_base + relativedelta(months=i)
                datas.append(f"{data_base.day:02d}/{dt.month:02d}/{dt.year}")
            if n == 1:
                parcelas_info.value = f"💳 À vista — vence em {datas[0]}"
            else:
                parcelas_info.value = f"💳 {n}x de {fmt_v(parcela)} — 1ª parcela em {datas[0]}, última em {datas[-1]}"
        except Exception:
            parcelas_info.value = ""
        page.update()

    parcelas_field.on_change = atualizar_info_parcelas

    busca_field     = ft.TextField(label="🔍 Buscar conta (ex: cartao, combustível...)", width=400,
                                    on_change=lambda e: filtrar_contas(e.control.value))
    lista_sugestoes = ft.Column(spacing=0, visible=False)
    sugestoes_container = ft.Container(content=lista_sugestoes, border=ft.border.all(1, "#DDD"),
                                        border_radius=8, bgcolor=ft.colors.WHITE, width=400)

    cat_real_row       = ft.Column(visible=False, spacing=4)
    busca_cat_real     = ft.TextField(label="🏷️ Categoria real (ex: mercado, combustível...)", width=400,
                                       on_change=lambda e: filtrar_cat_real(e.control.value))
    lista_cat_real     = ft.Column(spacing=0, visible=False)
    cat_real_container = ft.Container(content=lista_cat_real, border=ft.border.all(1, "#DDD"),
                                       border_radius=8, bgcolor=ft.colors.WHITE, width=400)
    cat_real_row.controls = [
        ft.Text("💡 Onde foi gasto no cartão?", size=12, color=ft.colors.ORANGE_700, weight="bold"),
        busca_cat_real, cat_real_container,
    ]

    val  = ft.TextField(label="Valor (ex: 462,00)", width=200,
                        on_blur=lambda e: (formatar_moeda_input(e), atualizar_info_parcelas(e)))
    desc = ft.TextField(label="Descrição", width=400)
    msg  = ft.Text("", size=13)

    def selecionar_conta(sid, nome, tipo):
        state["subconta_id"]   = sid
        state["subconta_nome"] = nome
        busca_field.value      = f"{nome} ({tipo})"
        lista_sugestoes.controls.clear()
        lista_sugestoes.visible = False
        # ✅ Preenche descrição automaticamente com o nome da conta
        if not desc.value.strip():
            desc.value = nome
        if eh_cartao(nome):
            parcelas_row.visible = True
            cat_real_row.visible = True
            atualizar_info_parcelas(None)
        else:
            parcelas_row.visible   = False
            parcelas_info.value    = ""
            cat_real_row.visible   = False
            state["cat_real_id"]   = None
            state["cat_real_nome"] = ""
            busca_cat_real.value   = ""
        page.update()

    def filtrar_contas(texto: str):
        lista_sugestoes.controls.clear()
        state["subconta_id"]   = None
        state["subconta_nome"] = ""
        parcelas_row.visible   = False
        cat_real_row.visible   = False
        if not texto:
            lista_sugestoes.visible = False
            page.update()
            return
        filtradas = [s for s in subs if texto.upper() in s["nome"].upper()]
        if not filtradas:
            lista_sugestoes.visible = False
            page.update()
            return
        for s in filtradas[:8]:
            cor = ft.colors.GREEN_700 if s["tipo"] == "Receita" else ft.colors.RED_700
            lista_sugestoes.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.ARROW_RIGHT, size=14, color=cor),
                        ft.Text(s["nome"], size=12, expand=True),
                        ft.Text(f"({s['tipo']})", size=11, color=cor),
                    ], spacing=6),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    bgcolor=ft.colors.WHITE,
                    border=ft.border.only(bottom=ft.BorderSide(1, "#EEE")),
                    on_click=lambda _, s=s: selecionar_conta(s["id"], s["nome"], s["tipo"]),
                    ink=True,
                )
            )
        lista_sugestoes.visible = True
        page.update()

    def selecionar_cat_real(sid, nome, tipo):
        state["cat_real_id"]   = sid
        state["cat_real_nome"] = nome
        busca_cat_real.value   = f"{nome} ({tipo})"
        lista_cat_real.controls.clear()
        lista_cat_real.visible = False
        page.update()

    def filtrar_cat_real(texto: str):
        lista_cat_real.controls.clear()
        state["cat_real_id"]   = None
        state["cat_real_nome"] = ""
        if not texto:
            lista_cat_real.visible = False
            page.update()
            return
        filtradas = [s for s in subs if texto.upper() in s["nome"].upper()]
        if not filtradas:
            lista_cat_real.visible = False
            page.update()
            return
        for s in filtradas[:8]:
            cor = ft.colors.GREEN_700 if s["tipo"] == "Receita" else ft.colors.RED_700
            lista_cat_real.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.ARROW_RIGHT, size=14, color=cor),
                        ft.Text(s["nome"], size=12, expand=True),
                        ft.Text(f"({s['tipo']})", size=11, color=cor),
                    ], spacing=6),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    bgcolor=ft.colors.WHITE,
                    border=ft.border.only(bottom=ft.BorderSide(1, "#EEE")),
                    on_click=lambda _, s=s: selecionar_cat_real(s["id"], s["nome"], s["tipo"]),
                    ink=True,
                )
            )
        lista_cat_real.visible = True
        page.update()

    def salvar(e):
        msg.value = ""
        if not state["subconta_id"]:
            msg.value = "⚠️ Selecione uma conta."
            page.update()
            return
        if not val.value or limpar_valor(val.value) == 0:
            msg.value = "⚠️ Informe um valor."
            page.update()
            return
        if eh_cartao(state["subconta_nome"]) and not state["cat_real_id"]:
            msg.value = "⚠️ Informe a categoria real do gasto no cartão."
            page.update()
            return

        banco_id = banco_dd.value or None
        banco_id = int(banco_id) if banco_id else None

        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("""
                SELECT c.tipo FROM categorias c
                JOIN subcontas s ON s.categoria_id = c.id
                WHERE s.id=%s
            """, (int(state["subconta_id"]),))
            row  = cur.fetchone()
            tipo = row["tipo"] if row else "Despesa"

            total_valor   = limpar_valor(val.value)
            n_parcelas    = int(parcelas_field.value or 1) if parcelas_row.visible else 1
            valor_parc    = round(total_valor / n_parcelas, 2)
            descricao     = desc.value.strip() or state["subconta_nome"]
            data_base     = get_data_base()
            cat_real_id   = state["cat_real_id"]
            cat_real_nome = state["cat_real_nome"]

            if n_parcelas == 1 and not parcelas_row.visible:
                data = data_base.strftime("%d/%m/%Y")
                base_desc = f"{cat_real_nome} - {descricao}" if cat_real_nome and descricao else cat_real_nome or descricao
                cur.execute("""
                    INSERT INTO transacoes
                        (usuario_id, data, valor, subconta_id, tipo, descricao,
                         parcela_atual, total_parcelas, categoria_real_id, banco_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (uid, data, total_valor, int(state["subconta_id"]), tipo,
                      base_desc, 1, 1, cat_real_id, banco_id))
            else:
                for i in range(1, n_parcelas + 1):
                    dt   = data_base + relativedelta(months=i)
                    data = f"{data_base.day:02d}/{dt.month:02d}/{dt.year}"
                    if cat_real_nome:
                        base_desc = f"{cat_real_nome} - {descricao}" if descricao else cat_real_nome
                    else:
                        base_desc = descricao
                    desc_parc = f"{base_desc} {i}/{n_parcelas}" if n_parcelas > 1 and base_desc else base_desc or f"{i}/{n_parcelas}"
                    cur.execute("""
                        INSERT INTO transacoes
                            (usuario_id, data, valor, subconta_id, tipo, descricao,
                             parcela_atual, total_parcelas, categoria_real_id, banco_id)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (uid, data, valor_parc, int(state["subconta_id"]), tipo,
                          desc_parc, i, n_parcelas, cat_real_id, banco_id))

            conn.commit()
            conn.close()

            # ✅ Limpa campos MAS mantém banco e data selecionados
            busca_field.value = ""
            val.value = ""
            desc.value = ""
            busca_cat_real.value = ""
            state.update({"subconta_id": None, "subconta_nome": "", "cat_real_id": None, "cat_real_nome": ""})
            parcelas_row.visible = False
            parcelas_info.value  = ""
            parcelas_field.value = "1"
            cat_real_row.visible = False
            lista_sugestoes.controls.clear()
            lista_sugestoes.visible = False
            lista_cat_real.controls.clear()
            lista_cat_real.visible = False
            # ✅ banco_dd.value NÃO é resetado — banco persiste!
            msg.value = f"✅ {n_parcelas}x lançamento(s) salvo(s)! Banco mantido: {banco_dd.options[[o.key for o in banco_dd.options].index(str(banco_id))].text if banco_id else '—'}"
            page.update()
        except Exception as ex:
            print(f"[avulso] salvar: {ex}")
            msg.value = "❌ Erro ao salvar. Tente novamente."
            page.update()

    return ft.View(
        route="/avulso",
        controls=[
            get_menu(page),
            ft.Divider(),
            ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("LANÇAMENTO AVULSO", size=18, weight="bold", color="blue"),
                    ft.Container(
                        bgcolor="#E3F2FD", border_radius=8, padding=10,
                        content=ft.Row([
                            ft.Icon(ft.icons.INFO_OUTLINE, color="#1565C0", size=16),
                            ft.Text("O banco selecionado permanece entre lançamentos. Troque quando necessário.",
                                    size=12, color="#1565C0", italic=True),
                        ], spacing=8)
                    ),
                    ft.Row([data_field, btn_data, banco_dd], spacing=10, wrap=True),
                    busca_field, sugestoes_container,
                    val, parcelas_row, cat_real_row, desc, msg,
                    ft.ElevatedButton("SALVAR LANÇAMENTO", icon=ft.icons.SAVE,
                                      bgcolor="blue", color="white", height=45, on_click=salvar),
                ], spacing=16)
            )
        ]
    )