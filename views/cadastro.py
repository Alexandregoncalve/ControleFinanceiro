import flet as ft
import re
from datetime import datetime
from menu import get_menu
from database import get_connection, criar_usuario
from utils import formatar_moeda_input, limpar_valor


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def validar_cpf(cpf: str) -> bool:
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum(int(cpf[n]) * ((i + 1) - n) for n in range(i))
        if int(cpf[i]) != ((soma * 10) % 11) % 10:
            return False
    return True


def set_field_state(field: ft.TextField, valido):
    if valido is True:
        field.border_color = ft.colors.GREEN_600
        field.suffix_icon  = ft.icons.CHECK_CIRCLE
        field.error_text   = None
    elif valido is False:
        field.border_color = ft.colors.RED_600
        field.suffix_icon  = ft.icons.CANCEL
    else:
        field.border_color = None
        field.suffix_icon  = None
        field.error_text   = None


def salvar_perfil_db(usuario_id: int, dados: dict) -> bool:
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT id FROM perfil WHERE usuario_id = ?", (usuario_id,))
        if cur.fetchone():
            cur.execute("""
                UPDATE perfil SET
                    nome=:nome, cpf=:cpf, rg=:rg, email=:email,
                    data_nasc=:data_nasc, telefone=:telefone,
                    cep=:cep, logradouro=:logradouro, numero=:numero,
                    complemento=:complemento, bairro=:bairro,
                    cidade=:cidade, estado=:estado,
                    empresa=:empresa, cargo=:cargo,
                    salario=:salario, dia_pagamento=:dia_pagamento,
                    vale=:vale, dia_vale=:dia_vale
                WHERE usuario_id=:usuario_id
            """, {**dados, "usuario_id": usuario_id})
        else:
            cur.execute("""
                INSERT INTO perfil (
                    usuario_id, nome, cpf, rg, email, data_nasc, telefone,
                    cep, logradouro, numero, complemento, bairro,
                    cidade, estado, empresa, cargo,
                    salario, dia_pagamento, vale, dia_vale
                ) VALUES (
                    :usuario_id, :nome, :cpf, :rg, :email, :data_nasc, :telefone,
                    :cep, :logradouro, :numero, :complemento, :bairro,
                    :cidade, :estado, :empresa, :cargo,
                    :salario, :dia_pagamento, :vale, :dia_vale
                )
            """, {**dados, "usuario_id": usuario_id})
        conn.commit()
        conn.close()
        return True
    except Exception as ex:
        print(f"[salvar_perfil_db] {ex}")
        return False


def carregar_perfil_db(usuario_id: int) -> dict:
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM perfil WHERE usuario_id = ?", (usuario_id,))
        row  = cur.fetchone()
        conn.close()
        return dict(row) if row else {}
    except Exception as ex:
        print(f"[carregar_perfil_db] {ex}")
        return {}


# ──────────────────────────────────────────────
# View
# ──────────────────────────────────────────────
def cadastro_view(page: ft.Page):
    uid       = page.session.get("user_id")
    novo_user = uid is None

    # ── Campos de acesso ──────────────────────
    login_f  = ft.TextField(
        label="E-mail (será seu login)", width=350,
        icon=ft.icons.EMAIL, visible=novo_user,
        hint_text="exemplo@email.com"
    )
    senha_f  = ft.TextField(
        label="Senha (mín. 6 caracteres)", width=250,
        icon=ft.icons.LOCK, password=True,
        can_reveal_password=True, visible=novo_user
    )
    senha2_f = ft.TextField(
        label="Confirmar Senha", width=250,
        icon=ft.icons.LOCK_OUTLINE, password=True,
        can_reveal_password=True, visible=novo_user
    )

    # ── Campos pessoais ───────────────────────
    nome      = ft.TextField(label="Nome Completo",   width=400, icon=ft.icons.PERSON)
    email     = ft.TextField(label="E-mail",          width=400, icon=ft.icons.EMAIL,
                             visible=not novo_user)
    cpf       = ft.TextField(label="CPF (000.000.000-00)",  width=220, icon=ft.icons.CREDIT_CARD,
                             hint_text="Somente números", max_length=14)
    rg        = ft.TextField(label="RG",              width=200, icon=ft.icons.BADGE,
                             hint_text="Somente números", max_length=12)
    data_nasc = ft.TextField(label="Nascimento (DD/MM/AAAA)", width=220, icon=ft.icons.CAKE,
                             hint_text="DD/MM/AAAA", max_length=10)
    telefone  = ft.TextField(label="WhatsApp",        width=220, icon=ft.icons.PHONE_ANDROID,
                             hint_text="(00) 00000-0000", max_length=15)

    # ── Endereço ──────────────────────────────
    cep         = ft.TextField(label="CEP",         width=150, icon=ft.icons.MAP,
                               hint_text="00000-000", max_length=9)
    endereco    = ft.TextField(label="Endereço",    width=350, icon=ft.icons.HOME)
    numero      = ft.TextField(label="Número",      width=100, icon=ft.icons.NUMBERS)
    complemento = ft.TextField(label="Complemento", width=190, icon=ft.icons.APARTMENT)
    bairro      = ft.TextField(label="Bairro",      width=220, icon=ft.icons.LOCATION_ON)
    cidade      = ft.TextField(label="Cidade",      width=220, icon=ft.icons.LOCATION_CITY)
    estado      = ft.TextField(label="UF",          width=80,  icon=ft.icons.MAP_OUTLINED,
                               hint_text="RS", max_length=2)

    # ── Profissional ──────────────────────────
    empresa  = ft.TextField(label="Empresa Atual",  width=320, icon=ft.icons.BUSINESS)
    cargo    = ft.TextField(label="Cargo / Função", width=280, icon=ft.icons.WORK)
    salario  = ft.TextField(label="Salário Bruto",  width=180, icon=ft.icons.ATTACH_MONEY,
                            prefix_text="R$ ", value="0,00")
    dia_pag  = ft.TextField(label="Dia Pagamento",  width=140, icon=ft.icons.CALENDAR_MONTH,
                            hint_text="1-31", max_length=2)
    vale     = ft.TextField(label="Valor Vale",     width=180, icon=ft.icons.MONEY,
                            prefix_text="R$ ", value="0,00")
    dia_vale = ft.TextField(label="Dia do Vale",    width=140, icon=ft.icons.CALENDAR_TODAY,
                            hint_text="1-31", max_length=2)

    msg_geral = ft.Text("", size=13)

    # ── Validações no blur (ao sair do campo) ─
    def on_blur_cpf(e):
        digits = re.sub(r'\D', '', cpf.value)
        if len(digits) == 0:
            set_field_state(cpf, False)
            cpf.error_text = "CPF obrigatório"
        elif len(digits) != 11:
            set_field_state(cpf, False)
            cpf.error_text = f"CPF incompleto ({len(digits)}/11 dígitos)"
        elif not validar_cpf(digits):
            set_field_state(cpf, False)
            cpf.error_text = "CPF inválido"
        else:
            # Formata ao sair
            cpf.value = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
            set_field_state(cpf, True)
        cpf.update()

    def on_blur_rg(e):
        digits = re.sub(r'\D', '', rg.value)
        if len(digits) == 0:
            set_field_state(rg, False)
            rg.error_text = "RG obrigatório"
        elif len(digits) < 7:
            set_field_state(rg, False)
            rg.error_text = f"RG incompleto ({len(digits)}/7 dígitos mín.)"
        else:
            set_field_state(rg, True)
        rg.update()

    def on_blur_data(e):
        v = data_nasc.value.strip()
        digits = re.sub(r'\D', '', v)
        if len(digits) == 0:
            set_field_state(data_nasc, False)
            data_nasc.error_text = "Data obrigatória"
        elif len(digits) != 8:
            set_field_state(data_nasc, False)
            data_nasc.error_text = "Use o formato DD/MM/AAAA"
        else:
            # Formata ao sair
            data_nasc.value = f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"
            try:
                dt = datetime.strptime(data_nasc.value, "%d/%m/%Y")
                if dt > datetime.now():
                    set_field_state(data_nasc, False)
                    data_nasc.error_text = "Data não pode ser futura"
                else:
                    set_field_state(data_nasc, True)
            except ValueError:
                set_field_state(data_nasc, False)
                data_nasc.error_text = "Data inválida"
        data_nasc.update()

    def on_blur_telefone(e):
        digits = re.sub(r'\D', '', telefone.value)
        if len(digits) == 0:
            set_field_state(telefone, False)
            telefone.error_text = "WhatsApp obrigatório"
        elif len(digits) < 10:
            set_field_state(telefone, False)
            telefone.error_text = f"Incompleto ({len(digits)}/11 dígitos com DDD)"
        else:
            # Formata ao sair
            if len(digits) == 11:
                telefone.value = f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
            else:
                telefone.value = f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
            set_field_state(telefone, True)
        telefone.update()

    def on_blur_cep(e):
        digits = re.sub(r'\D', '', cep.value)
        if len(digits) == 0:
            set_field_state(cep, False)
            cep.error_text = "CEP obrigatório"
        elif len(digits) != 8:
            set_field_state(cep, False)
            cep.error_text = f"CEP incompleto ({len(digits)}/8 dígitos)"
        else:
            cep.value = f"{digits[:5]}-{digits[5:]}"
            set_field_state(cep, True)
        cep.update()

    def on_blur_estado(e):
        estado.value = estado.value.strip().upper()
        if len(estado.value) == 2 and estado.value.isalpha():
            set_field_state(estado, True)
        else:
            set_field_state(estado, False)
            estado.error_text = "UF inválida (ex: RS)"
        estado.update()

    def on_blur_nome(e):
        v = nome.value.strip()
        if len(v.split()) < 2:
            set_field_state(nome, False)
            nome.error_text = "Digite nome e sobrenome"
        else:
            set_field_state(nome, True)
        nome.update()

    def on_blur_login(e):
        v = login_f.value.strip()
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.(com|com\.br|net|org)$', v.lower()):
            set_field_state(login_f, False)
            login_f.error_text = "E-mail inválido"
        else:
            set_field_state(login_f, True)
        login_f.update()

    def on_blur_senha(e):
        if len(senha_f.value) < 6:
            set_field_state(senha_f, False)
            senha_f.error_text = "Mínimo 6 caracteres"
        else:
            set_field_state(senha_f, True)
        senha_f.update()

    def on_blur_senha2(e):
        if senha2_f.value != senha_f.value:
            set_field_state(senha2_f, False)
            senha2_f.error_text = "Senhas não coincidem"
        else:
            set_field_state(senha2_f, True)
        senha2_f.update()

    def on_blur_obrigatorio(field, label):
        def _blur(e):
            if len(field.value.strip()) < 2:
                set_field_state(field, False)
                field.error_text = f"{label} obrigatório"
            else:
                set_field_state(field, True)
            field.update()
        return _blur

    # Vincula eventos blur
    nome.on_blur      = on_blur_nome
    cpf.on_blur       = on_blur_cpf
    rg.on_blur        = on_blur_rg
    data_nasc.on_blur = on_blur_data
    telefone.on_blur  = on_blur_telefone
    cep.on_blur       = on_blur_cep
    estado.on_blur    = on_blur_estado
    login_f.on_blur   = on_blur_login
    senha_f.on_blur   = on_blur_senha
    senha2_f.on_blur  = on_blur_senha2
    salario.on_blur   = formatar_moeda_input
    vale.on_blur      = formatar_moeda_input

    endereco.on_blur  = on_blur_obrigatorio(endereco, "Endereço")
    bairro.on_blur    = on_blur_obrigatorio(bairro,   "Bairro")
    cidade.on_blur    = on_blur_obrigatorio(cidade,   "Cidade")
    empresa.on_blur   = on_blur_obrigatorio(empresa,  "Empresa")
    cargo.on_blur     = on_blur_obrigatorio(cargo,    "Cargo")

    # ── Validação completa ao salvar ──────────
    def validar_todos() -> list:
        erros = []

        class FakeEvent:
            def __init__(self, ctrl): self.control = ctrl

        if novo_user:
            on_blur_login(None)
            on_blur_senha(None)
            on_blur_senha2(None)
            if login_f.border_color == ft.colors.RED_600:  erros.append("E-mail de login")
            if senha_f.border_color == ft.colors.RED_600:  erros.append("Senha")
            if senha2_f.border_color == ft.colors.RED_600: erros.append("Confirmação de senha")

        on_blur_nome(None)
        on_blur_cpf(None)
        on_blur_rg(None)
        on_blur_data(None)
        on_blur_telefone(None)
        on_blur_cep(None)
        on_blur_estado(None)
        on_blur_obrigatorio(endereco, "Endereço")(None)
        on_blur_obrigatorio(bairro,   "Bairro")(None)
        on_blur_obrigatorio(cidade,   "Cidade")(None)

        for field in [nome, cpf, rg, data_nasc, telefone,
                      cep, endereco, bairro, cidade, estado]:
            if field.border_color == ft.colors.RED_600:
                erros.append(field.label)

        page.update()
        return erros

    # ── Salvar ────────────────────────────────
    def salvar(e):
        erros = validar_todos()
        if erros:
            nomes = ", ".join(erros[:3])
            extra = f" e mais {len(erros) - 3}..." if len(erros) > 3 else ""
            msg_geral.value = f"⚠️ Corrija: {nomes}{extra}"
            msg_geral.color = ft.colors.RED_700
            page.update()
            return

        usuario_id = uid

        if novo_user:
            resultado = criar_usuario(
                nome=nome.value.strip(),
                login=login_f.value.strip(),
                senha=senha_f.value,
            )
            if not resultado["ok"]:
                msg_geral.value = f"❌ {resultado['erro']}"
                msg_geral.color = ft.colors.RED_700
                set_field_state(login_f, False)
                login_f.error_text = resultado["erro"]
                page.update()
                return
            usuario_id = resultado["id"]

        dados = {
            "nome":          nome.value.strip(),
            "cpf":           cpf.value.strip(),
            "rg":            rg.value.strip(),
            "email":         login_f.value.strip() if novo_user else email.value.strip(),
            "data_nasc":     data_nasc.value.strip(),
            "telefone":      telefone.value.strip(),
            "cep":           cep.value.strip(),
            "logradouro":    endereco.value.strip(),
            "numero":        numero.value.strip(),
            "complemento":   complemento.value.strip(),
            "bairro":        bairro.value.strip(),
            "cidade":        cidade.value.strip(),
            "estado":        estado.value.strip(),
            "empresa":       empresa.value.strip(),
            "cargo":         cargo.value.strip(),
            "salario":       limpar_valor(salario.value),
            "dia_pagamento": int(dia_pag.value) if dia_pag.value.strip().isdigit() else None,
            "vale":          limpar_valor(vale.value),
            "dia_vale":      int(dia_vale.value) if dia_vale.value.strip().isdigit() else None,
        }

        ok = salvar_perfil_db(usuario_id, dados)
        if ok:
            msg_geral.value = "✅ Cadastro salvo com sucesso!"
            msg_geral.color = ft.colors.GREEN_700
            page.update()
            if novo_user:
                page.go("/login")
        else:
            msg_geral.value = "❌ Erro ao salvar. Tente novamente."
            msg_geral.color = ft.colors.RED_700
            page.update()

    # ── Pré-carrega perfil existente ──────────
    if not novo_user:
        perfil = carregar_perfil_db(uid)
        if perfil:
            nome.value        = perfil.get("nome", "")
            email.value       = perfil.get("email", "")
            cpf.value         = perfil.get("cpf", "")
            rg.value          = perfil.get("rg", "")
            data_nasc.value   = perfil.get("data_nasc", "")
            telefone.value    = perfil.get("telefone", "")
            cep.value         = perfil.get("cep", "")
            endereco.value    = perfil.get("logradouro", "")
            numero.value      = perfil.get("numero", "")
            complemento.value = perfil.get("complemento", "")
            bairro.value      = perfil.get("bairro", "")
            cidade.value      = perfil.get("cidade", "")
            estado.value      = perfil.get("estado", "")
            empresa.value     = perfil.get("empresa", "")
            cargo.value       = perfil.get("cargo", "")
            salario.value     = f"{float(perfil.get('salario', 0) or 0):,.2f}"
            dia_pag.value     = str(perfil.get("dia_pagamento", "") or "")
            vale.value        = f"{float(perfil.get('vale', 0) or 0):,.2f}"
            dia_vale.value    = str(perfil.get("dia_vale", "") or "")
            for f in [nome, email, cpf, rg, data_nasc, telefone,
                      endereco, bairro, cidade, estado, empresa, cargo]:
                if f.value:
                    set_field_state(f, True)

    # ── Layout ────────────────────────────────
    titulo = "CRIAR CONTA" if novo_user else "MEU CADASTRO"

    conteudo = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=16,
        controls=[
            ft.Text(titulo, size=20, weight="bold", color="#1565C0"),
            ft.Divider(),

            # Acesso
            ft.Container(
                visible=novo_user,
                bgcolor="#E8F5E9",
                border_radius=10,
                padding=16,
                content=ft.Column([
                    ft.Text("🔐 DADOS DE ACESSO", size=15, weight="bold", color="#2E7D32"),
                    ft.Row([login_f], wrap=True, spacing=10),
                    ft.Row([senha_f, senha2_f], wrap=True, spacing=10),
                ], spacing=10)
            ),

            # Identificação
            ft.Container(
                bgcolor="#E3F2FD",
                border_radius=10,
                padding=16,
                content=ft.Column([
                    ft.Text("👤 1. IDENTIFICAÇÃO E CONTATO",
                            size=15, weight="bold", color="#1565C0"),
                    ft.Row([nome], wrap=True, spacing=10),
                    ft.Row([cpf, rg, data_nasc, telefone], wrap=True, spacing=10),
                ], spacing=10)
            ),

            # Endereço
            ft.Container(
                bgcolor="#FFF3E0",
                border_radius=10,
                padding=16,
                content=ft.Column([
                    ft.Text("🏠 2. ENDEREÇO RESIDENCIAL",
                            size=15, weight="bold", color="#E65100"),
                    ft.Text("💡 Digite o CEP e preencha o endereço manualmente.",
                            size=11, color=ft.colors.GREY_600, italic=True),
                    ft.Row([cep, endereco, numero, complemento], wrap=True, spacing=10),
                    ft.Row([bairro, cidade, estado], wrap=True, spacing=10),
                ], spacing=10)
            ),

            # Profissional
            ft.Container(
                bgcolor="#F3E5F5",
                border_radius=10,
                padding=16,
                content=ft.Column([
                    ft.Text("💼 3. DADOS PROFISSIONAIS E RENDA",
                            size=15, weight="bold", color="#6A1B9A"),
                    ft.Row([empresa, cargo], wrap=True, spacing=10),
                    ft.Row([salario, dia_pag, vale, dia_vale], wrap=True, spacing=10),
                ], spacing=10)
            ),

            msg_geral,

            ft.Row([
                ft.ElevatedButton(
                    "CRIAR CONTA" if novo_user else "SALVAR ALTERAÇÕES",
                    icon=ft.icons.PERSON_ADD if novo_user else ft.icons.SAVE,
                    height=50, bgcolor="#1565C0", color="white",
                    on_click=salvar,
                )
            ], alignment=ft.MainAxisAlignment.CENTER),
        ]
    )

    controles = [
        ft.Container(
            padding=ft.padding.symmetric(horizontal=24, vertical=16),
            expand=True,
            content=conteudo,
        )
    ]

    if not novo_user:
        controles.insert(0, ft.Divider())
        controles.insert(0, get_menu(page))

    return ft.View(
        route="/cadastro",
        controls=controles,
    )