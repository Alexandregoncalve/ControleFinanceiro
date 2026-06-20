import flet as ft
import unicodedata
from datetime import datetime

from database import db_session


def _normalizar(s):
    """Remove acentos e deixa em maiúsculas, para comparação de nomes."""
    if not s:
        return ""
    return unicodedata.normalize("NFKD", s).upper().encode("ASCII", "ignore").decode("ASCII")


def cartao_view(page: ft.Page):
    hoje = datetime.now()
    state = {"mes": hoje.month, "ano": hoje.year}
    uid = page.session.get("user_id")

    def get_mes_str():
        return f"{state['mes']:02d}/{state['ano']}"

    def get_meses_opcoes():
        opcoes = []
        m, a = hoje.month, hoje.year
        for _ in range(12):
            opcoes.append(ft.dropdown.Option(f"{m:02d}/{a}"))
            m -= 1
            if m == 0:
                m = 12
                a -= 1
        return opcoes

    def fmt(v):
        try:
            return f"R$ {float(v):_.2f}".replace(".", ",").replace("_", ".")
        except Exception:
            return "R$ 0,00"

    cartoes_col = ft.Column(spacing=16)

    TIPO_CORES = {"Crédito": "#1565C0", "Débito": "#2E7D32", "Ambos": "#6A1B9A"}

    def carregar(mes_str):
        m_sel, a_sel = int(mes_str.split("/")[0]), int(mes_str.split("/")[1])

        try:
            with db_session() as cur:
                # Cartões cadastrados (tela Bancos > Cartões)
                cur.execute("""
                    SELECT c.id, c.nome_cartao, c.tipo, c.limite, c.banco_id, b.nome_banco
                    FROM cartoes c
                    LEFT JOIN bancos b ON c.banco_id = b.id
                    WHERE c.usuario_id=%s
                    ORDER BY c.nome_cartao
                """, (uid,))
                cartoes = cur.fetchall()

                # Subcontas usadas para lançar compras no cartão (Avulso)
                cur.execute("""
                    SELECT id, nome, orcamento FROM subcontas
                    WHERE usuario_id=%s AND (nome ILIKE %s OR nome ILIKE %s)
                """, (uid, '%CARTAO%', '%CARTÃO%'))
                subcontas_cartao = cur.fetchall()

                # ── Casa cada cartão com sua subconta de lançamentos ──────────
                usados = set()
                pares = []  # (cartao_dict_ou_None, subconta_dict_ou_None)

                for c in cartoes:
                    palavras = [p for p in _normalizar(c['nome_cartao']).split() if len(p) >= 3]
                    sub_match = None
                    for s in subcontas_cartao:
                        if s['id'] in usados:
                            continue
                        nome_sub_norm = _normalizar(s['nome'])
                        if any(p in nome_sub_norm for p in palavras):
                            sub_match = s
                            break
                    if sub_match:
                        usados.add(sub_match['id'])
                    pares.append((c, sub_match))

                # Subcontas de cartão sem cadastro correspondente em "cartoes"
                for s in subcontas_cartao:
                    if s['id'] not in usados:
                        pares.append((None, s))

                blocos = []
                for cartao_info, subconta in pares:
                    if subconta:
                        cur.execute("""
                            SELECT descricao, valor, parcela_atual, total_parcelas
                            FROM transacoes
                            WHERE usuario_id=%s AND subconta_id=%s AND tipo='Despesa' AND data LIKE %s
                            ORDER BY valor DESC
                        """, (uid, subconta['id'], f"%%/{mes_str}"))
                        compras = cur.fetchall()
                        fatura_atual = sum(float(x['valor']) for x in compras)

                        cur.execute("""
                            SELECT COALESCE(SUM(valor),0) as total FROM transacoes
                            WHERE usuario_id=%s AND subconta_id=%s AND tipo='Despesa' AND total_parcelas>1
                            AND (
                                CAST(SPLIT_PART(data,'/',3) AS INTEGER) > %s OR
                                (CAST(SPLIT_PART(data,'/',3) AS INTEGER) = %s AND CAST(SPLIT_PART(data,'/',2) AS INTEGER) > %s)
                            )
                        """, (uid, subconta['id'], a_sel, a_sel, m_sel))
                        parcelas_futuras = float(cur.fetchone()['total'] or 0)
                    else:
                        compras = []
                        fatura_atual = 0.0
                        parcelas_futuras = 0.0

                    if cartao_info:
                        nome   = cartao_info['nome_cartao']
                        tipo   = cartao_info['tipo'] or "Crédito"
                        limite = float(cartao_info['limite'] or 0)
                        banco_nome = cartao_info['nome_banco'] or "—"
                    else:
                        nome   = subconta['nome']
                        tipo   = "—"
                        limite = float(subconta['orcamento'] or 0)
                        banco_nome = "—"

                    blocos.append({
                        "nome": nome,
                        "tipo": tipo,
                        "banco_nome": banco_nome,
                        "limite": limite,
                        "fatura_atual": fatura_atual,
                        "parcelas_futuras": parcelas_futuras,
                        "compras": compras,
                        "tem_subconta": subconta is not None,
                    })

        except Exception as ex:
            import traceback
            print(f"[cartao] carregar erro: {ex}")
            traceback.print_exc()
            cartoes_col.controls = [ft.Text("Erro ao carregar dados do cartão.", color="red")]
            page.update()
            return

        if not blocos:
            cartoes_col.controls = [
                ft.Container(
                    padding=16, bgcolor="#FFF8E1", border_radius=10,
                    content=ft.Text(
                        "Nenhum cartão encontrado. Cadastre um cartão em Bancos > Cartões, "
                        "e crie uma subconta com \"CARTAO\" ou \"CARTÃO\" no nome (Cadastro de Contas) "
                        "para lançar as compras pelo Avulso.",
                        size=13, color="#F57F17",
                    ),
                )
            ]
            page.update()
            return

        secoes = []
        for b in blocos:
            limite = b["limite"]
            fatura = b["fatura_atual"]
            disponivel = max(0.0, limite - fatura)
            pct_uso = (fatura / limite * 100) if limite > 0 else 0
            cor_uso = "#C62828" if pct_uso >= 100 else ("#F57F17" if pct_uso >= 80 else "#1565C0")
            tipo_cor = TIPO_CORES.get(b["tipo"], "#37474F")

            # Cards de resumo
            cards_row = ft.Row([
                ft.Container(
                    expand=1, padding=14, bgcolor=tipo_cor, border_radius=12,
                    content=ft.Column([
                        ft.Text("FATURA DO MÊS", size=10, weight="bold", color="white"),
                        ft.Text(fmt(fatura), size=20, weight="bold", color="white"),
                        ft.Text(f"{len(b['compras'])} compra(s) lançada(s)", size=10, color="white"),
                    ], spacing=3),
                ),
                ft.Container(
                    expand=1, padding=14, bgcolor="#2E7D32", border_radius=12,
                    content=ft.Column([
                        ft.Text("LIMITE DISPONÍVEL", size=10, weight="bold", color="white"),
                        ft.Text(fmt(disponivel) if limite > 0 else "—", size=20, weight="bold", color="white"),
                        ft.Text(f"de {fmt(limite)}" if limite > 0 else "Limite não definido", size=10, color="white"),
                    ], spacing=3),
                ),
                ft.Container(
                    expand=1, padding=14, bgcolor="#C62828", border_radius=12,
                    content=ft.Column([
                        ft.Text("PARCELAS FUTURAS", size=10, weight="bold", color="white"),
                        ft.Text(fmt(b["parcelas_futuras"]), size=20, weight="bold", color="white"),
                        ft.Text("comprometido em meses futuros", size=10, color="white"),
                    ], spacing=3),
                ),
            ], spacing=10)

            # Barra de limite utilizado
            barra = ft.Container(height=0)
            if limite > 0:
                barra = ft.Container(
                    padding=14, border=ft.border.all(1, "#E8EEF7"), border_radius=10, bgcolor="white",
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"{fmt(fatura)} usado", size=11, color="#555555"),
                            ft.Text(f"{pct_uso:.1f}% do limite", size=11, weight="bold", color=cor_uso),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.ProgressBar(
                            value=min(pct_uso / 100, 1.0), color=cor_uso,
                            bgcolor="#F0F4FA", height=8, border_radius=4,
                        ),
                    ], spacing=6),
                )

            # Lista de compras do mês
            itens = []
            for compra in b["compras"]:
                if compra["total_parcelas"] and compra["total_parcelas"] > 1:
                    parc_txt = f"{compra['parcela_atual']}/{compra['total_parcelas']}x"
                    parc_cor = "#1565C0"
                else:
                    parc_txt = "à vista"
                    parc_cor = "#888888"
                itens.append(
                    ft.Container(
                        padding=ft.padding.symmetric(vertical=6),
                        border=ft.border.only(bottom=ft.BorderSide(0.5, "#F0F4FA")),
                        content=ft.Row([
                            ft.Text(
                                compra["descricao"] or "(sem descrição)",
                                size=12, color="#333333", expand=True,
                                overflow=ft.TextOverflow.ELLIPSIS, max_lines=1,
                            ),
                            ft.Text(fmt(float(compra["valor"])), size=12, weight="bold", color="#C62828", width=90,
                                    text_align=ft.TextAlign.RIGHT),
                            ft.Container(
                                width=60, alignment=ft.alignment.center,
                                bgcolor="#E3F2FD" if parc_cor == "#1565C0" else "#F0F4FA",
                                border_radius=10, padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                content=ft.Text(parc_txt, size=10, weight="bold", color=parc_cor,
                                                 text_align=ft.TextAlign.CENTER),
                            ),
                        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    )
                )

            aviso_sem_subconta = ft.Container(height=0)
            if not b["tem_subconta"]:
                aviso_sem_subconta = ft.Container(
                    bgcolor="#FFF8E1", border_radius=8, padding=10,
                    content=ft.Text(
                        f"⚠ Nenhuma subconta de lançamento encontrada para \"{b['nome']}\". "
                        f"Crie uma subconta contendo o nome do cartão (ex: \"CARTAO {b['nome'].upper()}\") "
                        "para que as compras feitas no Avulso apareçam aqui.",
                        size=11, color="#F57F17",
                    ),
                )

            lista_compras = ft.Container(
                padding=14, border=ft.border.all(1, "#E8EEF7"), border_radius=10, bgcolor="white",
                content=ft.Column([
                    ft.Container(
                        content=ft.Text(f"Compras lançadas — {mes_str}", weight="bold", size=13, color="#1565C0"),
                        border=ft.border.only(bottom=ft.BorderSide(2, "#E3F2FD")),
                        padding=ft.padding.only(bottom=8),
                    ),
                    ft.Column(itens, spacing=0) if itens else
                    ft.Text("Nenhuma compra lançada neste mês.", color="grey", italic=True, size=12),
                ], spacing=8),
            )

            secoes.append(
                ft.Column([
                    ft.Row([
                        ft.Text(f"💳 {b['nome']}", size=15, weight="bold", color="#1565C0"),
                        ft.Container(
                            bgcolor=tipo_cor, border_radius=10, padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            content=ft.Text(b["tipo"], size=10, weight="bold", color="white"),
                        ) if b["tipo"] != "—" else ft.Container(height=0),
                        ft.Text(f"· {b['banco_nome']}", size=11, color="#888888") if b["banco_nome"] != "—" else ft.Container(height=0),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Divider(height=4, color="transparent"),
                    cards_row,
                    ft.Divider(height=4, color="transparent"),
                    barra,
                    ft.Divider(height=4, color="transparent"),
                    aviso_sem_subconta,
                    ft.Divider(height=4, color="transparent") if not b["tem_subconta"] else ft.Container(height=0),
                    lista_compras,
                ], spacing=0)
            )

        cartoes_col.controls = secoes
        page.update()

    dd_mes = ft.Dropdown(
        label="Mês", width=160, value=get_mes_str(), options=get_meses_opcoes(),
        on_change=lambda e: (
            state.update({"mes": int(e.control.value.split("/")[0]), "ano": int(e.control.value.split("/")[1])}),
            carregar(e.control.value),
        ),
    )

    carregar(get_mes_str())

    return ft.View(route="/cartao", bgcolor="#F0F4FA", controls=[
        ft.Container(
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            expand=True,
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text("Cartão de Crédito", size=20, weight="bold", color="#1565C0"),
                        ft.Container(width=180, height=3, bgcolor="#2E7D32", border_radius=2),
                    ], spacing=3),
                    ft.Row([ft.Text("Período:", size=11, color="#999999"), dd_mes], spacing=6),
                ], spacing=16),
                ft.Divider(height=4, color="transparent"),
                cartoes_col,
            ], scroll=ft.ScrollMode.ALWAYS, expand=True),
        )
    ])