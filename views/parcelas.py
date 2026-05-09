import flet as ft
from datetime import datetime
from collections import defaultdict
from menu import get_menu
from database import get_connection


def parcelas_view(page: ft.Page):

    uid = page.session.get("user_id")

    def fmt(v):
        return f"R$ {v:_.2f}".replace(".", ",").replace("_", ".")

    tabela = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Descrição")),
            ft.DataColumn(ft.Text("Conta")),
            ft.DataColumn(ft.Text("Valor Parcela")),
            ft.DataColumn(ft.Text("Total")),
            ft.DataColumn(ft.Text("Progresso")),
            ft.DataColumn(ft.Text("Próx. Vencimento")),
            ft.DataColumn(ft.Text("Status")),
        ],
        rows=[],
    )

    msg         = ft.Text("", size=13)
    resumo_text = ft.Text("", size=13, weight="bold", color=ft.colors.BLUE_700)

    def desc_base(descricao: str) -> str:
        if not descricao:
            return ""
        partes = descricao.rsplit(" ", 1)
        if len(partes) == 2:
            sufixo = partes[1]
            if "/" in sufixo:
                lados = sufixo.split("/")
                if len(lados) == 2 and lados[0].isdigit() and lados[1].isdigit():
                    return partes[0]
        return descricao

    def carregar():
        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute("""
                SELECT
                    t.descricao,
                    s.nome as conta,
                    t.valor,
                    t.parcela_atual,
                    t.total_parcelas,
                    t.data
                FROM transacoes t
                JOIN subcontas s ON t.subconta_id = s.id
                WHERE t.total_parcelas > 1 AND t.usuario_id = ?
                ORDER BY t.data ASC
            """, (uid,))
            rows = cur.fetchall()
            conn.close()

            grupos = defaultdict(list)
            for r in rows:
                base  = desc_base(r["descricao"] or "")
                chave = f"{base}||{r['conta']}||{r['total_parcelas']}"
                grupos[chave].append(r)

            tabela.rows.clear()
            hoje            = datetime.now()
            total_em_aberto = 0.0
            total_pago      = 0.0

            for chave, parcelas in grupos.items():
                partes_chave   = chave.split("||")
                desc_b         = partes_chave[0]
                conta          = partes_chave[1]
                total_parcelas = int(partes_chave[2])
                valor_parcela  = parcelas[0]["valor"]
                valor_total    = valor_parcela * total_parcelas
                parcelas_ord   = sorted(parcelas, key=lambda x: x["data"])

                pagas = sum(
                    1 for p in parcelas_ord
                    if datetime.strptime(p["data"], "%d/%m/%Y") <= hoje
                )
                restantes = total_parcelas - pagas

                proxima = None
                for p in parcelas_ord:
                    try:
                        dt = datetime.strptime(p["data"], "%d/%m/%Y")
                        if dt > hoje:
                            proxima = p["data"]
                            break
                    except Exception:
                        pass

                pct = (pagas / total_parcelas) if total_parcelas > 0 else 0

                if restantes == 0:
                    status     = "✅ Quitado"
                    cor_status = ft.colors.GREEN_700
                    cor_barra  = "green"
                elif pagas == 0:
                    status     = "🔴 Não iniciado"
                    cor_status = ft.colors.RED_700
                    cor_barra  = "red"
                else:
                    status     = f"⏳ {pagas}/{total_parcelas} pagas"
                    cor_status = ft.colors.ORANGE_700
                    cor_barra  = "orange"

                total_em_aberto += valor_parcela * restantes
                total_pago      += valor_parcela * pagas

                tabela.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(desc_b, size=12)),
                    ft.DataCell(ft.Text(conta, size=12)),
                    ft.DataCell(ft.Text(fmt(valor_parcela), size=12, weight="bold")),
                    ft.DataCell(ft.Text(fmt(valor_total), size=12)),
                    ft.DataCell(ft.Column([
                        ft.Text(f"{pagas}/{total_parcelas}", size=11, color="grey"),
                        ft.ProgressBar(value=pct, color=cor_barra, height=8, width=120),
                    ], spacing=2)),
                    ft.DataCell(ft.Text(
                        proxima or "-", size=12,
                        color=ft.colors.BLUE_700 if proxima else ft.colors.GREY_400
                    )),
                    ft.DataCell(ft.Text(status, size=12, color=cor_status, weight="bold")),
                ]))

            resumo_text.value = (
                f"💳 Total parcelado: {fmt(total_pago + total_em_aberto)}  |  "
                f"✅ Pago: {fmt(total_pago)}  |  "
                f"⏳ Em aberto: {fmt(total_em_aberto)}"
            )
            msg.value = "" if tabela.rows else "Nenhuma compra parcelada encontrada."
            page.update()

        except Exception as ex:
            print(f"[parcelas] carregar: {ex}")
            msg.value = "❌ Erro ao carregar parcelas."
            page.update()

    carregar()

    return ft.View(
        route="/parcelas",
        controls=[
            get_menu(page),
            ft.Divider(),
            ft.Container(
                padding=20, expand=True,
                content=ft.Column([
                    ft.Row([
                        ft.Text("HISTÓRICO DE PARCELAS", size=18, weight="bold", color="blue"),
                        ft.ElevatedButton("🔄 ATUALIZAR", bgcolor=ft.colors.BLUE_100,
                                          color=ft.colors.BLUE_900, on_click=lambda _: carregar()),
                    ], alignment="spaceBetween"),
                    ft.Text("Acompanhe todas as compras parceladas em andamento.", size=12, color="grey"),
                    ft.Divider(),
                    resumo_text,
                    msg,
                    ft.Divider(),
                    ft.Row(controls=[tabela], scroll=ft.ScrollMode.ALWAYS),
                ], scroll=ft.ScrollMode.ALWAYS, expand=True)
            )
        ]
    )