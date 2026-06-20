import flet as ft
import re
import os
from datetime import datetime, date as ddate
from menu import get_menu
from database import get_connection, get_cursor


def conciliacao_view(page: ft.Page):
    uid  = page.session.get("user_id")
    hoje = datetime.now()

    state = {
        "trans_banco": [],
        "trans_app":   [],
        "resultado":   [],
        "banco_id":    None,
        "banco_nome":  None,
        "banco_conta": None,
        "conc_id":     None,
    }

    msg_text    = ft.Text("", size=13)
    resumo_text = ft.Text("", size=13, weight="bold")
    banco_text  = ft.Text("", size=12, color="#1565C0", italic=True)
    lista_col   = ft.Column([], spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)
    hist_col    = ft.Column([], spacing=4)
    hist_visible = ft.Ref[ft.Container]()

    # ── HELPERS ───────────────────────────────────────────────────────────
    def fmt(v):
        try:
            valor = float(v)
            neg   = valor < 0
            valor = abs(valor)
            inteiro = int(valor)
            cents   = round((valor - inteiro) * 100)
            s = str(inteiro)
            com_ponto = ""
            for i, c in enumerate(reversed(s)):
                if i > 0 and i % 3 == 0:
                    com_ponto = "." + com_ponto
                com_ponto = c + com_ponto
            return f"R$ {'-' if neg else ''}{com_ponto},{cents:02d}"
        except Exception:
            return "R$ 0,00"

    def parse_data_ofx(dtposted):
        try:
            dt = dtposted[:8]
            return f"{dt[6:8]}/{dt[4:6]}/{dt[0:4]}"
        except Exception:
            return dtposted

    # ── SUBCONTAS E BANCOS ────────────────────────────────────────────────
    def get_subcontas():
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("""
                SELECT s.id, s.nome, c.tipo FROM subcontas s
                JOIN categorias c ON s.categoria_id = c.id
                WHERE s.usuario_id = %s ORDER BY c.tipo, s.nome
            """, (uid,))
            rows = cur.fetchall()
            conn.close()
            return rows
        except Exception:
            return []

    subs = get_subcontas()

    # ── PARSE OFX ─────────────────────────────────────────────────────────
    def parse_ofx(conteudo):
        trans = []

        def get_tag(bloco, tag):
            m = re.search(rf'<{tag}>(.*?)</{tag}>', bloco, re.DOTALL)
            if m: return m.group(1).strip()
            m = re.search(rf'<{tag}>([^\n<]+)', bloco)
            if m: return m.group(1).strip()
            return None

        bankid = get_tag(conteudo, "BANKID") or ""
        acctid = get_tag(conteudo, "ACCTID") or ""
        state["banco_conta"] = acctid

        bancos_conhecidos = {
            "748": "Sicredi", "237": "Bradesco", "341": "Itau",
            "033": "Santander", "001": "Banco do Brasil",
            "104": "Caixa", "260": "Nubank", "208": "BTG",
        }
        nome_banco_ofx = bancos_conhecidos.get(bankid, f"Banco {bankid}")

        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("SELECT id, nome_banco FROM bancos WHERE usuario_id=%s AND codigo_banco=%s LIMIT 1", (uid, bankid))
            banco = cur.fetchone()
            if not banco:
                cur.execute("SELECT id, nome_banco FROM bancos WHERE usuario_id=%s AND UPPER(nome_banco) LIKE %s LIMIT 1",
                            (uid, f"%{nome_banco_ofx.upper()}%"))
                banco = cur.fetchone()
            if not banco:
                cur.execute("SELECT id, nome_banco FROM bancos WHERE usuario_id=%s LIMIT 1", (uid,))
                banco = cur.fetchone()
            conn.close()
            if banco:
                state["banco_id"]   = banco["id"]
                state["banco_nome"] = banco["nome_banco"]
                banco_text.value    = f"🏦 Banco: {banco['nome_banco']} | Conta: {acctid}"
            else:
                state["banco_id"]   = None
                state["banco_nome"] = nome_banco_ofx
                banco_text.value    = f"⚠️ Banco {nome_banco_ofx} não encontrado no cadastro"
        except Exception as ex:
            print(f"[conciliacao] detectar banco: {ex}")

        blocos = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', conteudo, re.DOTALL)
        for bloco in blocos:
            try:
                dtposted = get_tag(bloco, "DTPOSTED")
                trnamt   = get_tag(bloco, "TRNAMT")
                memo     = get_tag(bloco, "MEMO")
                fitid    = get_tag(bloco, "FITID")
                if not all([dtposted, trnamt, memo]): continue
                valor = float(trnamt)
                trans.append({
                    "data":  parse_data_ofx(dtposted),
                    "valor": abs(valor),
                    "tipo":  "Receita" if valor > 0 else "Despesa",
                    "desc":  memo,
                    "fitid": fitid or "",
                })
            except Exception as ex:
                print(f"[conciliacao] parse ofx erro: {ex}")
        return trans

    # ── PARSE PDF — MULTI-BANCO ───────────────────────────────────────────
    def parse_pdf(caminho):
        """Detecta o banco e extrai transações do PDF."""
        import pdfplumber
        trans  = []
        banco  = "desconhecido"

        try:
            with pdfplumber.open(caminho) as pdf:
                # Lê todo o texto para detectar o banco
                texto_completo = ""
                for p in pdf.pages:
                    texto_completo += (p.extract_text() or "") + "\n"

                # ── Detecta o banco ────────────────────────────────────────
                tc = texto_completo.upper()
                if "SICREDI" in tc or "COOPERATIVA" in tc:
                    banco = "sicredi"
                elif "BTGPACTUAL" in tc or "BTG" in tc or "BOA BRASIL" in tc:
                    banco = "btg"
                elif "RICO CORRETORA" in tc or "RICO CORRETORA DE TITULOS" in tc:
                    banco = "rico"
                elif "BRADESCO" in tc:
                    banco = "bradesco"
                elif "ITAU" in tc or "ITAÚ" in tc:
                    banco = "itau"
                elif "NUBANK" in tc:
                    banco = "nubank"
                elif "SANTANDER" in tc:
                    banco = "santander"
                elif "BANCO DO BRASIL" in tc or "BB " in tc:
                    banco = "bb"
                elif "CAIXA ECONOMICA" in tc or "CAIXA ECONÔMICA" in tc:
                    banco = "caixa"
                elif "XP INVESTIMENTOS" in tc or "XP INC" in tc:
                    banco = "xp"

                print(f"[conciliacao] banco detectado: {banco}")
                banco_text.value = f"🏦 Banco detectado no PDF: {banco.upper()}"

                # ── Atualiza banco_id no state ────────────────────────────
                try:
                    conn = get_connection()
                    cur  = get_cursor(conn)
                    cur.execute("""
                        SELECT id, nome_banco FROM bancos
                        WHERE usuario_id=%s AND UPPER(nome_banco) LIKE %s LIMIT 1
                    """, (uid, f"%{banco.upper()}%"))
                    b = cur.fetchone()
                    if not b:
                        cur.execute("SELECT id, nome_banco FROM bancos WHERE usuario_id=%s LIMIT 1", (uid,))
                        b = cur.fetchone()
                    if b:
                        state["banco_id"]   = b["id"]
                        state["banco_nome"] = b["nome_banco"]
                        banco_text.value    = f"🏦 Banco: {b['nome_banco']}"
                    conn.close()
                except Exception:
                    pass

                # ── Parsers específicos ────────────────────────────────────
                for page_pdf in pdf.pages:
                    texto = page_pdf.extract_text() or ""
                    linhas = texto.split("\n")

                    if banco == "btg":
                        trans += _parse_btg(linhas)
                    elif banco == "rico":
                        trans += _parse_rico(linhas)
                    elif banco in ("sicredi",):
                        trans += _parse_sicredi(linhas)
                    else:
                        # Parser genérico para bancos não mapeados
                        trans += _parse_generico(linhas)

        except Exception as ex:
            print(f"[conciliacao] parse pdf erro: {ex}")

        return trans

    def _parse_sicredi(linhas):
        """Parser Sicredi: DD/MM/AAAA DESCRICAO DOC -valor saldo"""
        trans = []
        for linha in linhas:
            m = re.match(
                r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(\S+)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$',
                linha.strip()
            )
            if m:
                try:
                    valor = float(m.group(4).replace(".", "").replace(",", "."))
                    trans.append({
                        "data":  m.group(1),
                        "valor": abs(valor),
                        "tipo":  "Receita" if valor > 0 else "Despesa",
                        "desc":  m.group(2).strip(),
                        "fitid": "",
                    })
                except Exception:
                    pass
        return trans

    def _parse_btg(linhas):
        """Parser BTG — suporta dois formatos:
           Formato 1 (antigo): DD/MM/AAAA DESCRICAO valor_deb valor_cred saldo
           Formato 2 (novo):   DD/MM/AAAA HHhMM Categoria Transacao Descricao R$ valor
        """
        trans = []
        cabecalho = False

        for linha in linhas:
            linha = linha.strip()

            # Ignora linhas de saldo diário, totais e cabeçalho
            if any(x in linha for x in ["Saldo Diário", "Saldo Final", "Saldo Inicial",
                                          "Total de Créditos", "Total de Débitos",
                                          "SAC", "Ouvidoria", "©BTG"]):
                continue

            # ── Formato novo: DD/MM/AAAA HHhMM ... R$ valor ou -R$ valor ──
            m_novo = re.match(
                r'(\d{2}/\d{2}/\d{4})\s+\d{2}h\d{2}\s+.*?(-?R\$\s*[\d.,]+)\s*$',
                linha
            )
            if m_novo:
                try:
                    data      = m_novo.group(1)
                    valor_str = m_novo.group(2).replace("R$", "").replace(".", "").replace(",", ".").strip()
                    valor     = float(valor_str)
                    # Extrai descrição — tudo entre hora e valor
                    desc_m = re.match(
                        r'\d{2}/\d{2}/\d{4}\s+\d{2}h\d{2}\s+(.+?)\s+-?R\$\s*[\d.,]+\s*$',
                        linha
                    )
                    desc = desc_m.group(1).strip() if desc_m else linha
                    trans.append({
                        "data":  data,
                        "valor": abs(valor),
                        "tipo":  "Receita" if valor > 0 else "Despesa",
                        "desc":  desc,
                        "fitid": "",
                    })
                except Exception:
                    pass
                continue

            # ── Formato antigo: DD/MM/AAAA DESCRICAO deb cred saldo ──────
            if "Data" in linha and "Débito" in linha:
                cabecalho = True
                continue
            if not cabecalho:
                continue

            m_ant = re.match(
                r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s{2,}(\d{1,3}(?:\.\d{3})*,\d{2})?\s*(\d{1,3}(?:\.\d{3})*,\d{2})?\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s*$',
                linha
            )
            if m_ant:
                try:
                    debito  = m_ant.group(3)
                    credito = m_ant.group(4)
                    if debito and not credito:
                        valor = float(debito.replace(".", "").replace(",", "."))
                        tipo  = "Despesa"
                    elif credito and not debito:
                        valor = float(credito.replace(".", "").replace(",", "."))
                        tipo  = "Receita"
                    else:
                        continue
                    trans.append({
                        "data":  m_ant.group(1),
                        "valor": valor,
                        "tipo":  tipo,
                        "desc":  m_ant.group(2).strip(),
                        "fitid": "",
                    })
                except Exception:
                    pass

        return trans

    def _parse_rico(linhas):
        """Parser Rico/XP — usa tabela extraída pelo pdfplumber."""
        return []  # Rico usa extract_tables, tratado no parse_pdf principal

    def _parse_rico(linhas):
        """Parser Rico/XP: Liq Mov DESCRICAO R$ valor R$ saldo
           Sempre Receita (dividendos, JCP, rendimentos)"""
        trans = []
        for linha in linhas:
            m = re.match(
                r'(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(.+?)\s+R\$\s*(-?\d{1,3}(?:\.\d{3})*,\d{2})\s+R\$\s*(-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$',
                linha.strip()
            )
            if m:
                try:
                    valor_str = m.group(4).replace(".", "").replace(",", ".")
                    valor = float(valor_str)
                    tipo  = "Receita" if valor >= 0 else "Despesa"
                    trans.append({
                        "data":  m.group(1),
                        "valor": abs(valor),
                        "tipo":  tipo,
                        "desc":  m.group(3).strip(),
                        "fitid": "",
                    })
                except Exception:
                    pass
        return trans

    def _parse_generico(linhas):
        """Parser genérico: tenta extrair DD/MM/AAAA ... valor saldo"""
        trans = []
        for linha in linhas:
            # Tenta padrão comum: data + descrição + valor + saldo
            m = re.match(
                r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$',
                linha.strip()
            )
            if m:
                try:
                    valor = float(m.group(3).replace(".", "").replace(",", "."))
                    trans.append({
                        "data":  m.group(1),
                        "valor": abs(valor),
                        "tipo":  "Receita" if valor > 0 else "Despesa",
                        "desc":  m.group(2).strip(),
                        "fitid": "",
                    })
                except Exception:
                    pass
        return trans

    # ── PARSE EXCEL — MULTI-BANCO ─────────────────────────────────────────
    def parse_excel(caminho):
        """Detecta o banco e extrai transações de XLS/XLSX."""
        import openpyxl
        trans = []
        banco = "desconhecido"

        try:
            # Suporte a XLS e XLSX
            if caminho.lower().endswith(".xls"):
                try:
                    import xlrd
                    wb_xls = xlrd.open_workbook(caminho)
                    ws_xls = wb_xls.sheet_by_index(0)
                    rows = [ws_xls.row_values(i) for i in range(ws_xls.nrows)]
                except ImportError:
                    msg_text.value = "❌ Instale xlrd: pip install xlrd"
                    msg_text.color = ft.colors.RED_700
                    page.update()
                    return []
            else:
                wb = openpyxl.load_workbook(caminho, data_only=True)
                ws = wb.active
                rows = [list(row) for row in ws.iter_rows(values_only=True)]

            # Detecta banco pelo conteúdo
            texto_completo = " ".join(str(c) for r in rows[:15] for c in r if c).upper()

            if "SICREDI" in texto_completo or "COOPERATIVA" in texto_completo:
                banco = "sicredi"
            elif "BTGPACTUAL" in texto_completo or "BTG" in texto_completo:
                banco = "btg"
            elif "RICO CORRETORA" in texto_completo or "CONTA RICO" in texto_completo:
                banco = "rico"
            elif "BRADESCO" in texto_completo:
                banco = "bradesco"
            elif "ITAU" in texto_completo or "ITAÚ" in texto_completo:
                banco = "itau"
            elif "NUBANK" in texto_completo:
                banco = "nubank"
            elif "SANTANDER" in texto_completo:
                banco = "santander"
            elif "BANCO DO BRASIL" in texto_completo:
                banco = "bb"
            elif "CAIXA" in texto_completo:
                banco = "caixa"
            elif "XP INVESTIMENTOS" in texto_completo:
                banco = "xp"

            print(f"[conciliacao] banco excel detectado: {banco}")

            # Atualiza banco_id
            try:
                conn = get_connection()
                cur  = get_cursor(conn)
                cur.execute("""
                    SELECT id, nome_banco FROM bancos
                    WHERE usuario_id=%s AND UPPER(nome_banco) LIKE %s LIMIT 1
                """, (uid, f"%{banco.upper()}%"))
                b = cur.fetchone()
                if not b:
                    cur.execute("SELECT id, nome_banco FROM bancos WHERE usuario_id=%s LIMIT 1", (uid,))
                    b = cur.fetchone()
                if b:
                    state["banco_id"]   = b["id"]
                    state["banco_nome"] = b["nome_banco"]
                    banco_text.value    = f"🏦 Banco: {b['nome_banco']} (Excel)"
                conn.close()
            except Exception:
                pass

            # Parsers específicos
            if banco == "sicredi":
                trans = _parse_excel_sicredi(rows)
            elif banco == "rico":
                trans = _parse_excel_rico(rows)
            elif banco == "btg":
                trans = _parse_excel_btg(rows)
            else:
                trans = _parse_excel_generico(rows)

        except Exception as ex:
            print(f"[conciliacao] parse excel erro: {ex}")

        return trans

    def _parse_excel_sicredi(rows):
        """Sicredi XLS: Data | Descricao | Documento | Valor | Saldo"""
        trans = []
        cabecalho = False
        for row in rows:
            if not cabecalho:
                if str(row[0]).strip() == "Data":
                    cabecalho = True
                continue
            try:
                data = row[0]
                desc = str(row[1]).strip()
                valor = float(row[3])
                if not data or not desc or desc in ("Saldo Anterior", ""):
                    continue
                # Converte data
                if hasattr(data, "strftime"):
                    data_str = data.strftime("%d/%m/%Y")
                elif isinstance(data, float):
                    import xlrd
                    dt = xlrd.xldate_as_datetime(data, 0)
                    data_str = dt.strftime("%d/%m/%Y")
                else:
                    data_str = str(data)[:10]

                trans.append({
                    "data":  data_str,
                    "valor": abs(valor),
                    "tipo":  "Receita" if valor > 0 else "Despesa",
                    "desc":  desc,
                    "fitid": "",
                })
            except Exception:
                pass
        return trans

    def _parse_excel_rico(rows):
        """Rico XLSX: Movimentacao | Liquidacao | Lancamento | None | Valor | Saldo"""
        trans = []
        cabecalho = False
        for row in rows:
            if not cabecalho:
                vals = [str(c).strip() for c in row if c]
                if "Movimentação" in vals or "Movimentacao" in vals:
                    cabecalho = True
                continue
            try:
                data = row[1]  # coluna Movimentação
                desc = str(row[3]).strip() if row[3] else ""
                valor = float(row[5]) if row[5] else 0

                if not data or not desc or valor == 0:
                    continue

                if hasattr(data, "strftime"):
                    data_str = data.strftime("%d/%m/%Y")
                else:
                    data_str = str(data)[:10]

                tipo = "Receita" if valor >= 0 else "Despesa"
                trans.append({
                    "data":  data_str,
                    "valor": abs(valor),
                    "tipo":  tipo,
                    "desc":  desc,
                    "fitid": "",
                })
            except Exception:
                pass
        return trans

    def _parse_excel_btg(rows):
        """BTG XLSX: Data | Descricao | Debito | Credito | Saldo"""
        trans = []
        cabecalho = False
        for row in rows:
            if not cabecalho:
                vals = [str(c).strip().lower() for c in row if c]
                if "débito" in vals or "debito" in vals:
                    cabecalho = True
                continue
            try:
                data  = row[0]
                desc  = str(row[1]).strip()
                deb   = row[2]
                cred  = row[3]

                if not data or not desc:
                    continue
                if any(x in desc.lower() for x in ["saldo", "total"]):
                    continue

                if hasattr(data, "strftime"):
                    data_str = data.strftime("%d/%m/%Y")
                else:
                    data_str = str(data)[:10]

                if deb and float(deb) > 0:
                    valor = float(deb)
                    tipo  = "Despesa"
                elif cred and float(cred) > 0:
                    valor = float(cred)
                    tipo  = "Receita"
                else:
                    continue

                trans.append({
                    "data":  data_str,
                    "valor": valor,
                    "tipo":  tipo,
                    "desc":  desc,
                    "fitid": "",
                })
            except Exception:
                pass
        return trans

    def _parse_excel_generico(rows):
        """Parser genérico: procura colunas com data e valor."""
        trans = []
        col_data = col_desc = col_valor = -1

        for row in rows:
            # Detecta cabeçalho
            if col_data == -1:
                for i, c in enumerate(row):
                    cs = str(c).lower().strip()
                    if cs in ("data", "date"):           col_data  = i
                    if cs in ("descrição", "descricao", "historico", "histórico", "lançamento"): col_desc = i
                    if cs in ("valor", "value", "montante", "débito", "credito"): col_valor = i
                if col_data >= 0 and col_desc >= 0 and col_valor >= 0:
                    continue

            if col_data < 0: continue
            try:
                data  = row[col_data]
                desc  = str(row[col_desc]).strip() if col_desc >= 0 and row[col_desc] else ""
                valor = float(row[col_valor]) if col_valor >= 0 and row[col_valor] else 0

                if not data or not desc or valor == 0:
                    continue

                if hasattr(data, "strftime"):
                    data_str = data.strftime("%d/%m/%Y")
                else:
                    data_str = str(data)[:10]

                trans.append({
                    "data":  data_str,
                    "valor": abs(valor),
                    "tipo":  "Receita" if valor > 0 else "Despesa",
                    "desc":  desc,
                    "fitid": "",
                })
            except Exception:
                pass
        return trans

    # ── VERIFICAR PERÍODO DUPLICADO ────────────────────────────────────────
    def verificar_periodo_duplicado(ini, fim, callback_sim, callback_nao):
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("""
                SELECT id, data_exec FROM conciliacoes
                WHERE usuario_id=%s AND banco_id=%s AND data_ini=%s AND data_fim=%s
                ORDER BY id DESC LIMIT 1
            """, (uid, state["banco_id"], ini, fim))
            existente = cur.fetchone()
            conn.close()

            if existente:
                dlg = ft.AlertDialog(
                    title=ft.Text("⚠️ Período já conciliado"),
                    content=ft.Text(
                        f"Já existe uma conciliação para este período\n"
                        f"executada em {existente['data_exec']}.\n\n"
                        f"Deseja substituir ou criar uma nova?"
                    ),
                    actions=[
                        ft.TextButton("CANCELAR", on_click=lambda _: page.close(dlg)),
                        ft.ElevatedButton("SUBSTITUIR", bgcolor=ft.colors.ORANGE_700,
                            color="white",
                            on_click=lambda _: (page.close(dlg), callback_sim(existente["id"]))),
                        ft.ElevatedButton("CRIAR NOVA", bgcolor=ft.colors.BLUE_700,
                            color="white",
                            on_click=lambda _: (page.close(dlg), callback_nao())),
                    ],
                )
                page.open(dlg)
            else:
                callback_nao()
        except Exception as ex:
            print(f"[conciliacao] verificar periodo: {ex}")
            callback_nao()

    # ── CARREGAR APP ───────────────────────────────────────────────────────
    def carregar_app(data_ini, data_fim):
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("""
                SELECT t.id, t.data, s.nome, t.valor, t.tipo, t.descricao
                FROM transacoes t
                JOIN subcontas s ON t.subconta_id = s.id
                WHERE t.usuario_id = %s
                AND TO_DATE(t.data, 'DD/MM/YYYY') >= %s
                AND TO_DATE(t.data, 'DD/MM/YYYY') <= %s
                ORDER BY TO_DATE(t.data, 'DD/MM/YYYY') DESC
            """, (uid, data_ini, data_fim))
            trans = cur.fetchall()
            conn.close()
            return trans
        except Exception as ex:
            print(f"[conciliacao] carregar_app: {ex}")
            return []

    # ── COMPARAR ──────────────────────────────────────────────────────────
    def comparar(trans_banco, trans_app):
        resultado  = []
        app_usados = set()
        for tb in trans_banco:
            encontrado = None
            for i, ta in enumerate(trans_app):
                if i in app_usados: continue
                if (abs(float(ta["valor"]) - float(tb["valor"])) < 0.02 and
                        ta["tipo"] == tb["tipo"]):
                    encontrado = i
                    break
            if encontrado is not None:
                app_usados.add(encontrado)
                resultado.append({"status": "ok",    "banco": tb, "app": trans_app[encontrado]})
            else:
                resultado.append({"status": "falta", "banco": tb, "app": None})
        for i, ta in enumerate(trans_app):
            if i not in app_usados:
                resultado.append({"status": "extra", "banco": None, "app": ta})
        return resultado

    # ── SALVAR CONCILIAÇÃO ─────────────────────────────────────────────────
    def salvar_conciliacao(resultado, substituir_id=None):
        try:
            ok    = len([r for r in resultado if r["status"] == "ok"])
            falta = len([r for r in resultado if r["status"] == "falta"])
            extra = len([r for r in resultado if r["status"] == "extra"])
            conn  = get_connection()
            cur   = get_cursor(conn)

            if substituir_id:
                cur.execute("DELETE FROM conciliacao_itens WHERE conciliacao_id=%s", (substituir_id,))
                cur.execute("DELETE FROM conciliacoes WHERE id=%s", (substituir_id,))

            cur.execute("""
                INSERT INTO conciliacoes
                (usuario_id, banco_id, data_ini, data_fim, data_exec,
                 total_banco, conciliados, pendentes, extras)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """, (uid, state["banco_id"], f_ini.value, f_fim.value,
                  hoje.strftime("%d/%m/%Y %H:%M"),
                  len(state["trans_banco"]), ok, falta, extra))
            conc_id = cur.fetchone()["id"]
            state["conc_id"] = conc_id

            for r in resultado:
                tb = r["banco"]
                ta = r["app"]
                cur.execute("""
                    INSERT INTO conciliacao_itens
                    (conciliacao_id, status, data, descricao, valor, tipo, transacao_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (
                    conc_id, r["status"],
                    tb["data"] if tb else (str(ta["data"])[:10] if ta else ""),
                    tb["desc"] if tb else (ta["descricao"] or ta["nome"] if ta else ""),
                    float(tb["valor"]) if tb else float(ta["valor"]) if ta else 0,
                    tb["tipo"] if tb else (ta["tipo"] if ta else ""),
                    ta["id"] if ta else None,
                ))
            conn.commit()
            conn.close()
        except Exception as ex:
            print(f"[conciliacao] salvar_conciliacao: {ex}")

    # ── LINHA REATIVA ──────────────────────────────────────────────────────
    def linha_falta(tb):
        expanded  = {"v": False}
        cor       = ft.colors.GREEN_700 if tb["tipo"] == "Receita" else ft.colors.RED_700
        sub_state = {"id": None, "nome": ""}

        busca_sub = ft.TextField(label="Categoria", width=260, hint_text="Digite para buscar...")
        lista_sub = ft.Column(spacing=0, visible=False)
        sub_cont  = ft.Container(content=lista_sub, border=ft.border.all(1, "#DDD"),
                                  border_radius=6, bgcolor="white", width=260, visible=False)
        desc_f    = ft.TextField(label="Descrição", value=tb["desc"], width=300)
        msg_f     = ft.Text("", size=11, color=ft.colors.RED_700)

        def filtrar_sub(e):
            texto = busca_sub.value.upper()
            lista_sub.controls.clear()
            sub_state["id"] = None
            filtradas = [s for s in subs if texto in s["nome"].upper() and s["tipo"] == tb["tipo"]]
            if not filtradas or not texto:
                lista_sub.visible = False
                sub_cont.visible  = False
                page.update()
                return
            for s in filtradas[:8]:
                def fazer_sel(s=s):
                    sub_state["id"]   = s["id"]
                    sub_state["nome"] = s["nome"]
                    busca_sub.value   = s["nome"]
                    lista_sub.controls.clear()
                    lista_sub.visible = False
                    sub_cont.visible  = False
                    page.update()
                lista_sub.controls.append(ft.Container(
                    content=ft.Text(s["nome"], size=12),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    bgcolor="white",
                    border=ft.border.only(bottom=ft.BorderSide(1, "#EEE")),
                    on_click=lambda _, f=fazer_sel: f(),
                    ink=True,
                ))
            lista_sub.visible = True
            sub_cont.visible  = True
            page.update()

        busca_sub.on_change = filtrar_sub

        form_row = ft.Container(
            bgcolor="#FFFDE7",
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border=ft.border.only(left=ft.BorderSide(3, "#FFB300"),
                                   bottom=ft.BorderSide(1, "#FFE082")),
            visible=False,
            content=ft.Column([
                ft.Row([busca_sub, sub_cont], spacing=8, wrap=True),
                ft.Row([desc_f], spacing=8, wrap=True),
                msg_f,
                ft.Row([
                    ft.ElevatedButton("✅ CONFIRMAR", bgcolor=ft.colors.GREEN_700,
                        color="white", height=36,
                        on_click=lambda _: confirmar_lancamento(tb, sub_state, desc_f, msg_f, form_row)),
                    ft.TextButton("Cancelar", on_click=lambda _: fechar_form()),
                ], spacing=8),
            ], spacing=8),
        )

        def abrir_form(_):
            expanded["v"] = not expanded["v"]
            form_row.visible = expanded["v"]
            page.update()

        def fechar_form():
            expanded["v"]    = False
            form_row.visible = False
            page.update()

        return ft.Column([
            ft.Container(
                bgcolor="#FFF8E1", border_radius=ft.border_radius.only(top_left=8, top_right=8),
                padding=ft.padding.symmetric(horizontal=16, vertical=8),
                border=ft.border.all(1, "#FFB300"),
                content=ft.Row([
                    ft.Container(width=100, content=ft.Text(tb["data"], size=12, color="#555")),
                    ft.Container(expand=True, content=ft.Text(tb["desc"], size=12)),
                    ft.Container(width=120, content=ft.Text(fmt(tb["valor"]), size=13, weight="bold", color=cor)),
                    ft.Container(width=80,  content=ft.Text(tb["tipo"], size=11, color=cor)),
                    ft.ElevatedButton("LANÇAR ▼", bgcolor=ft.colors.ORANGE_700,
                                      color="white", height=32, on_click=abrir_form),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ),
            form_row,
        ], spacing=0)

    def confirmar_lancamento(tb, sub_state, desc_f, msg_f, form_row):
        if not sub_state["id"]:
            msg_f.value = "⚠️ Selecione uma categoria"
            page.update()
            return
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("""
                INSERT INTO transacoes
                (usuario_id, data, valor, descricao, subconta_id, tipo, banco_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """, (uid, tb["data"], tb["valor"], desc_f.value,
                  sub_state["id"], tb["tipo"], state["banco_id"]))
            tid = cur.fetchone()["id"]
            if state["conc_id"]:
                cur.execute("""
                    UPDATE conciliacao_itens SET status='ok', transacao_id=%s
                    WHERE conciliacao_id=%s AND descricao=%s AND valor=%s AND status='falta'
                """, (tid, state["conc_id"], tb["desc"], tb["valor"]))
            conn.commit()
            conn.close()
            msg_text.value = f"✅ Lançado: {desc_f.value}"
            msg_text.color = ft.colors.GREEN_700
            form_row.visible = False
            page.update()
            processar()
        except Exception as ex:
            print(f"[conciliacao] confirmar: {ex}")
            msg_f.value = f"❌ Erro: {ex}"
            page.update()

    # ── RENDERIZAR ─────────────────────────────────────────────────────────
    def renderizar_resultado(resultado):
        lista_col.controls.clear()
        ok    = [r for r in resultado if r["status"] == "ok"]
        falta = [r for r in resultado if r["status"] == "falta"]
        extra = [r for r in resultado if r["status"] == "extra"]

        resumo_text.value = (
            f"✅ Conciliados: {len(ok)}  |  "
            f"⚠️ Faltam no app: {len(falta)}  |  "
            f"❌ Só no app: {len(extra)}"
        )

        if falta:
            lista_col.controls.append(ft.Container(
                bgcolor="#FFF3E0", border_radius=8,
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                margin=ft.margin.only(bottom=4),
                content=ft.Text(f"⚠️ {len(falta)} lançamento(s) no banco que FALTAM no app:",
                                size=13, weight="bold", color="#E65100"),
            ))
            for r in falta:
                lista_col.controls.append(linha_falta(r["banco"]))

        if extra:
            lista_col.controls.append(ft.Container(
                bgcolor="#FCE4EC", border_radius=8,
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                margin=ft.margin.only(top=12, bottom=4),
                content=ft.Text(f"❌ {len(extra)} lançamento(s) no app que NÃO estão no banco:",
                                size=13, weight="bold", color="#880E4F"),
            ))
            for r in extra:
                ta  = r["app"]
                cor = ft.colors.GREEN_700 if ta["tipo"] == "Receita" else ft.colors.RED_700
                lista_col.controls.append(ft.Container(
                    bgcolor="#FFF0F5", border_radius=8,
                    padding=ft.padding.symmetric(horizontal=16, vertical=8),
                    margin=ft.margin.only(bottom=2),
                    border=ft.border.all(1, "#F48FB1"),
                    content=ft.Row([
                        ft.Container(width=100, content=ft.Text(str(ta["data"])[:10], size=12, color="#555")),
                        ft.Container(expand=True, content=ft.Text(ta["descricao"] or ta["nome"], size=12)),
                        ft.Container(width=120, content=ft.Text(fmt(ta["valor"]), size=13, weight="bold", color=cor)),
                        ft.Container(width=80,  content=ft.Text(ta["tipo"], size=11, color=cor)),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ))

        if ok:
            lista_col.controls.append(ft.Container(
                bgcolor="#E8F5E9", border_radius=8,
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                margin=ft.margin.only(top=12, bottom=4),
                content=ft.Text(f"✅ {len(ok)} lançamento(s) conciliados:",
                                size=13, weight="bold", color="#1B5E20"),
            ))
            for r in ok:
                tb  = r["banco"]
                cor = ft.colors.GREEN_700 if tb["tipo"] == "Receita" else ft.colors.RED_700
                lista_col.controls.append(ft.Container(
                    bgcolor="#F1F8E9", border_radius=8,
                    padding=ft.padding.symmetric(horizontal=16, vertical=6),
                    margin=ft.margin.only(bottom=2),
                    border=ft.border.all(1, "#A5D6A7"),
                    content=ft.Row([
                        ft.Container(width=100, content=ft.Text(tb["data"], size=12, color="#555")),
                        ft.Container(expand=True, content=ft.Text(tb["desc"], size=12)),
                        ft.Container(width=120, content=ft.Text(fmt(tb["valor"]), size=13, weight="bold", color=cor)),
                        ft.Container(width=80,  content=ft.Text(tb["tipo"], size=11, color=cor)),
                        ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN_700, size=20),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ))
        page.update()

    # ── HISTÓRICO ──────────────────────────────────────────────────────────
    def carregar_historico():
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("""
                SELECT c.id, c.data_ini, c.data_fim, c.data_exec,
                       c.conciliados, c.pendentes, c.extras, c.total_banco,
                       b.nome_banco
                FROM conciliacoes c
                LEFT JOIN bancos b ON c.banco_id = b.id
                WHERE c.usuario_id = %s
                ORDER BY c.id DESC LIMIT 20
            """, (uid,))
            rows = cur.fetchall()
            conn.close()

            hist_col.controls.clear()
            if not rows:
                hist_col.controls.append(
                    ft.Text("Nenhuma conciliação encontrada.", size=12, color="#888", italic=True))
                page.update()
                return

            for row in rows:
                def ver_conc(row=row):
                    carregar_conciliacao_id(row["id"])

                hist_col.controls.append(ft.Container(
                    bgcolor="white",
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=16, vertical=10),
                    border=ft.border.all(1, "#E0E0E0"),
                    margin=ft.margin.only(bottom=4),
                    content=ft.Row([
                        ft.Column([
                            ft.Text(f"🏦 {row['nome_banco'] or 'Banco'}",
                                    size=13, weight="bold"),
                            ft.Text(f"📅 {row['data_ini']} a {row['data_fim']}",
                                    size=12, color="#555"),
                            ft.Text(f"🕐 {row['data_exec']}", size=11, color="#888"),
                        ], spacing=2, expand=True),
                        ft.Column([
                            ft.Text(f"✅ {row['conciliados']}", size=12, color=ft.colors.GREEN_700),
                            ft.Text(f"⚠️ {row['pendentes']}", size=12, color=ft.colors.ORANGE_700),
                            ft.Text(f"❌ {row['extras']}", size=12, color=ft.colors.RED_700),
                        ], spacing=2),
                        ft.ElevatedButton("VER", bgcolor=ft.colors.BLUE_700,
                                          color="white", height=32,
                                          on_click=lambda _, r=row: ver_conc()),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ))
            page.update()
        except Exception as ex:
            print(f"[conciliacao] carregar_historico: {ex}")

    def carregar_conciliacao_id(conc_id):
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("""
                SELECT c.*, b.nome_banco FROM conciliacoes c
                LEFT JOIN bancos b ON c.banco_id = b.id
                WHERE c.id = %s
            """, (conc_id,))
            conc = cur.fetchone()

            cur.execute("""
                SELECT * FROM conciliacao_itens WHERE conciliacao_id = %s ORDER BY id
            """, (conc_id,))
            itens = cur.fetchall()
            conn.close()

            state["conc_id"]    = conc["id"]
            state["banco_id"]   = conc["banco_id"]
            state["banco_nome"] = conc["nome_banco"]

            f_ini.value = conc["data_ini"]
            f_fim.value = conc["data_fim"]
            banco_text.value = (
                f"🏦 Banco: {conc['nome_banco']} | "
                f"Período: {conc['data_ini']} a {conc['data_fim']} | "
                f"Executada: {conc['data_exec']}"
            )

            resultado = []
            for item in itens:
                tb = {"data": item["data"], "desc": item["descricao"],
                      "valor": item["valor"], "tipo": item["tipo"], "fitid": ""}
                if item["status"] == "ok":
                    resultado.append({"status": "ok",    "banco": tb, "app": tb})
                elif item["status"] == "falta":
                    resultado.append({"status": "falta", "banco": tb, "app": None})
                else:
                    resultado.append({"status": "extra", "banco": None, "app": {
                        "data": item["data"], "descricao": item["descricao"],
                        "nome": item["descricao"], "valor": item["valor"],
                        "tipo": item["tipo"],
                    }})

            state["resultado"]   = resultado
            state["trans_banco"] = [r["banco"] for r in resultado if r["banco"]]
            renderizar_resultado(resultado)

            # Fecha histórico
            hist_container.visible = False
            page.update()
        except Exception as ex:
            print(f"[conciliacao] carregar_conc_id: {ex}")

    # ── FILTROS E PROCESSAMENTO ────────────────────────────────────────────
    f_ini = ft.TextField(label="Data Inicial", width=140,
                         value=f"01/{hoje.month:02d}/{hoje.year}",
                         hint_text="DD/MM/AAAA")
    f_fim = ft.TextField(label="Data Final", width=140,
                         value=f"{hoje.day:02d}/{hoje.month:02d}/{hoje.year}",
                         hint_text="DD/MM/AAAA")

    def processar(substituir_id=None):
        if not state["trans_banco"]:
            msg_text.value = "⚠️ Importe um arquivo OFX/PDF primeiro."
            msg_text.color = ft.colors.ORANGE_700
            page.update()
            return
        try:
            def to_date(s):
                p = s.split("/")
                return ddate(int(p[2]), int(p[1]), int(p[0]))
            d_ini = to_date(f_ini.value)
            d_fim = to_date(f_fim.value)
        except Exception:
            msg_text.value = "❌ Data inválida."
            msg_text.color = ft.colors.RED_700
            page.update()
            return

        def executar(sub_id=None):
            trans_app = carregar_app(d_ini, d_fim)
            state["trans_app"] = trans_app

            def in_periodo(t):
                try:
                    p = t["data"].split("/")
                    d = ddate(int(p[2]), int(p[1]), int(p[0]))
                    return d_ini <= d <= d_fim
                except Exception:
                    return True

            banco_filtrado = [t for t in state["trans_banco"] if in_periodo(t)]
            resultado = comparar(banco_filtrado, list(trans_app))
            state["resultado"] = resultado
            salvar_conciliacao(resultado, sub_id)
            renderizar_resultado(resultado)

        verificar_periodo_duplicado(
            f_ini.value, f_fim.value,
            callback_sim=lambda sub_id: executar(sub_id),
            callback_nao=lambda: executar(),
        )

    # ── UPLOAD ─────────────────────────────────────────────────────────────
    def processar_conteudo(conteudo, nome_arquivo):
        if nome_arquivo.lower().endswith(".ofx"):
            trans = parse_ofx(conteudo)
        else:
            trans = []
        state["trans_banco"] = trans
        msg_text.value = f"✅ Importado: {len(trans)} lançamentos | {banco_text.value}"
        msg_text.color = ft.colors.GREEN_700
        page.update()
        processar()

    def on_upload_progress(e: ft.FilePickerUploadEvent):
        if e.progress == 1.0:
            try:
                upload_dir = os.path.join(os.path.dirname(
                    os.path.dirname(__file__)), "uploads")
                caminho = os.path.join(upload_dir, e.file_name)
                if os.path.exists(caminho):
                    nome = e.file_name.lower()
                    if nome.endswith(".pdf"):
                        trans = parse_pdf(caminho)
                        state["trans_banco"] = trans
                        msg_text.value = f"✅ PDF importado: {len(trans)} lançamentos"
                        msg_text.color = ft.colors.GREEN_700
                        page.update()
                        processar()
                    elif nome.endswith(".xlsx") or nome.endswith(".xls"):
                        trans = parse_excel(caminho)
                        state["trans_banco"] = trans
                        msg_text.value = f"✅ Excel importado: {len(trans)} lançamentos"
                        msg_text.color = ft.colors.GREEN_700
                        page.update()
                        processar()
                    else:
                        with open(caminho, "r", encoding="latin-1") as f:
                            conteudo = f.read()
                        processar_conteudo(conteudo, e.file_name)
                else:
                    msg_text.value = "❌ Arquivo não encontrado após upload."
                    msg_text.color = ft.colors.RED_700
                    page.update()
            except Exception as ex:
                print(f"[conciliacao] on_upload: {ex}")
                msg_text.value = f"❌ Erro: {ex}"
                msg_text.color = ft.colors.RED_700
                page.update()

    def on_file_picked(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        arquivo = e.files[0]
        try:
            if arquivo.path and os.path.exists(arquivo.path):
                nome = arquivo.name.lower()
                if nome.endswith(".pdf"):
                    trans = parse_pdf(arquivo.path)
                    state["trans_banco"] = trans
                    msg_text.value = f"✅ PDF importado: {len(trans)} lançamentos"
                    msg_text.color = ft.colors.GREEN_700
                    page.update()
                    processar()
                elif nome.endswith(".xlsx") or nome.endswith(".xls"):
                    trans = parse_excel(arquivo.path)
                    state["trans_banco"] = trans
                    msg_text.value = f"✅ Excel importado: {len(trans)} lançamentos"
                    msg_text.color = ft.colors.GREEN_700
                    page.update()
                    processar()
                else:
                    with open(arquivo.path, "r", encoding="latin-1") as f:
                        conteudo = f.read()
                    processar_conteudo(conteudo, arquivo.name)
                return

            msg_text.value = "⏳ Enviando arquivo..."
            msg_text.color = ft.colors.BLUE_700
            page.update()
            upload_url = page.get_upload_url(arquivo.name, 60)
            file_picker.upload([ft.FilePickerUploadFile(
                name=arquivo.name, upload_url=upload_url)])
        except Exception as ex:
            print(f"[conciliacao] on_file_picked: {ex}")
            msg_text.value = f"❌ Erro: {ex}"
            msg_text.color = ft.colors.RED_700
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_picked, on_upload=on_upload_progress)
    page.overlay.append(file_picker)

    hist_container = ft.Container(
        bgcolor="#F5F5F5", border_radius=8,
        padding=16, visible=False,
        content=ft.Column([
            ft.Text("📋 HISTÓRICO DE CONCILIAÇÕES", size=14, weight="bold", color="#1565C0"),
            ft.Divider(),
            hist_col,
        ], scroll=ft.ScrollMode.AUTO),
    )

    def toggle_historico(_):
        hist_container.visible = not hist_container.visible
        if hist_container.visible:
            carregar_historico()
        page.update()

    # ── CARREGA ÚLTIMA AO ABRIR ────────────────────────────────────────────
    def carregar_ultima_conciliacao():
        try:
            conn = get_connection()
            cur  = get_cursor(conn)
            cur.execute("""
                SELECT c.id FROM conciliacoes c
                WHERE c.usuario_id = %s ORDER BY c.id DESC LIMIT 1
            """, (uid,))
            row = cur.fetchone()
            conn.close()
            if row:
                carregar_conciliacao_id(row["id"])
        except Exception as ex:
            print(f"[conciliacao] carregar_ultima: {ex}")

    carregar_ultima_conciliacao()

    return ft.View(
        route="/conciliacao",
        controls=[
            get_menu(page),
            ft.Divider(),
            ft.Container(
                padding=20, expand=True,
                content=ft.Column(
                    controls=[
                        ft.Row([
                            ft.Icon(ft.icons.COMPARE_ARROWS, color="#1565C0", size=26),
                            ft.Text("CONCILIAÇÃO BANCÁRIA", size=18, weight="bold", color="#1565C0"),
                            ft.ElevatedButton(
                                "📋 HISTÓRICO",
                                bgcolor=ft.colors.GREY_300, color=ft.colors.BLACK,
                                height=32, on_click=toggle_historico,
                            ),
                        ], spacing=10),
                        hist_container,
                        ft.Divider(),
                        ft.Row([
                            f_ini, f_fim,
                            ft.ElevatedButton(
                                "📂 IMPORTAR OFX",
                                bgcolor=ft.colors.GREEN_700, color="white",
                                icon=ft.icons.UPLOAD_FILE,
                                on_click=lambda _: file_picker.pick_files(
                                    dialog_title="Selecione OFX do banco",
                                    allowed_extensions=["ofx", "OFX"],
                                ),
                            ),
                            ft.ElevatedButton(
                                "📄 IMPORTAR PDF",
                                bgcolor=ft.colors.BLUE_700, color="white",
                                icon=ft.icons.PICTURE_AS_PDF,
                                on_click=lambda _: file_picker.pick_files(
                                    dialog_title="Selecione PDF do banco",
                                    allowed_extensions=["pdf", "PDF"],
                                ),
                            ),
                            ft.ElevatedButton(
                                "📊 IMPORTAR EXCEL",
                                bgcolor=ft.colors.GREEN_800, color="white",
                                icon=ft.icons.TABLE_CHART,
                                on_click=lambda _: file_picker.pick_files(
                                    dialog_title="Selecione Excel do banco",
                                    allowed_extensions=["xlsx", "xls", "XLSX", "XLS"],
                                ),
                            ),
                            ft.ElevatedButton(
                                "🔄 COMPARAR",
                                bgcolor=ft.colors.ORANGE_700, color="white",
                                icon=ft.icons.COMPARE,
                                on_click=lambda _: processar(),
                            ),
                        ], spacing=12, wrap=True),
                        banco_text,
                        ft.Container(
                            bgcolor="#E3F2FD", border_radius=8,
                            padding=ft.padding.symmetric(horizontal=16, vertical=10),
                            content=ft.Text(
                                "📋 1) Defina o período  "
                                "2) Importe OFX ou PDF  "
                                "3) COMPARAR  "
                                "4) Clique LANÇAR ▼ nos pendentes",
                                size=12, color="#1565C0"
                            ),
                        ),
                        ft.Container(
                            bgcolor="#F5F5F5", border_radius=8,
                            padding=ft.padding.symmetric(horizontal=16, vertical=10),
                            content=resumo_text,
                        ),
                        msg_text,
                        ft.Divider(),
                        lista_col,
                    ],
                    scroll=ft.ScrollMode.ALWAYS,
                    expand=True,
                )
            )
        ]
    )