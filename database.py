import os
import bcrypt
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://finacassimples_db_user:xjwALfBS8PcTDsNqE2Gv6OeCsZUScSRw@dpg-d7vr3bbeo5us73f0icig-a/finacassimples_db"
)


def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def get_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def _hash(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def _verificar_senha(senha: str, hash_salvo) -> bool:
    try:
        h = hash_salvo if isinstance(hash_salvo, bytes) else hash_salvo.encode()
        return bcrypt.checkpw(senha.encode(), h)
    except Exception:
        return False


def criar_usuario(nome: str, login: str, senha: str) -> dict:
    try:
        conn = get_connection()
        cur  = get_cursor(conn)
        cur.execute("SELECT id FROM usuarios WHERE login = %s", (login,))
        if cur.fetchone():
            conn.close()
            return {"ok": False, "erro": "Este e-mail já está cadastrado."}
        cur.execute(
            "INSERT INTO usuarios (login, senha, nome) VALUES (%s, %s, %s) RETURNING id",
            (login, _hash(senha), nome)
        )
        uid = cur.fetchone()["id"]
        # Cria plano de contas para o novo usuário
        _criar_dados_iniciais(cur, uid)
        conn.commit()
        conn.close()
        return {"ok": True, "id": uid}
    except Exception as ex:
        print(f"[criar_usuario] {ex}")
        return {"ok": False, "erro": "Erro interno ao criar usuário."}


def autenticar(login: str, senha: str):
    try:
        conn = get_connection()
        cur  = get_cursor(conn)
        cur.execute(
            "SELECT id, nome, login, senha FROM usuarios WHERE login = %s",
            (login,)
        )
        row = cur.fetchone()
        conn.close()
        if row and _verificar_senha(senha, row["senha"]):
            return {"id": row["id"], "nome": row["nome"], "login": row["login"]}
        return None
    except Exception as ex:
        print(f"[autenticar] {ex}")
        return None


def restaurar_plano_contas(uid: int) -> bool:
    """Restaura o plano de contas para um usuário que não tem categorias."""
    try:
        conn = get_connection()
        cur  = get_cursor(conn)
        cur.execute("SELECT COUNT(*) as total FROM categorias WHERE usuario_id=%s", (uid,))
        if cur.fetchone()["total"] == 0:
            _criar_dados_iniciais(cur, uid)
            conn.commit()
            print(f"✅ Plano de contas restaurado para usuario_id={uid}")
        else:
            print(f"ℹ️ Usuário {uid} já tem categorias.")
        conn.close()
        return True
    except Exception as ex:
        print(f"[restaurar_plano_contas] {ex}")
        return False


def init_db():
    conn   = get_connection()
    cursor = get_cursor(conn)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id    SERIAL PRIMARY KEY,
            login TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            nome  TEXT NOT NULL
        )
    """)
    cursor.execute("SELECT COUNT(*) as total FROM usuarios")
    if cursor.fetchone()["total"] == 0:
        cursor.execute(
            "INSERT INTO usuarios (login, senha, nome) VALUES (%s, %s, %s) RETURNING id",
            ("admin", _hash("admin123"), "Administrador")
        )
        uid = cursor.fetchone()["id"]
        _criar_dados_iniciais(cursor, uid)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS perfil (
            id            SERIAL PRIMARY KEY,
            usuario_id    INTEGER UNIQUE,
            nome          TEXT,
            cpf           TEXT,
            rg            TEXT,
            email         TEXT,
            data_nasc     TEXT,
            telefone      TEXT,
            cep           TEXT,
            logradouro    TEXT,
            numero        TEXT,
            complemento   TEXT,
            bairro        TEXT,
            cidade        TEXT,
            estado        TEXT,
            empresa       TEXT,
            cargo         TEXT,
            salario       REAL,
            dia_pagamento INTEGER,
            vale          REAL,
            dia_vale      INTEGER,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bancos (
            id            SERIAL PRIMARY KEY,
            usuario_id    INTEGER,
            nome_banco    TEXT,
            saldo_inicial REAL,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cartoes (
            id             SERIAL PRIMARY KEY,
            usuario_id     INTEGER,
            nome_cartao    TEXT,
            limite         REAL,
            dia_vencimento INTEGER,
            banco_id       INTEGER,
            tipo           TEXT,
            FOREIGN KEY(banco_id)   REFERENCES bancos(id),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id         SERIAL PRIMARY KEY,
            usuario_id INTEGER,
            nome       TEXT,
            tipo       TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subcontas (
            id           SERIAL PRIMARY KEY,
            usuario_id   INTEGER,
            categoria_id INTEGER,
            nome         TEXT,
            fixa         INTEGER DEFAULT 0,
            orcamento    REAL    DEFAULT 0,
            FOREIGN KEY(usuario_id)   REFERENCES usuarios(id),
            FOREIGN KEY(categoria_id) REFERENCES categorias(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id                SERIAL PRIMARY KEY,
            usuario_id        INTEGER,
            data              TEXT,
            valor             REAL,
            descricao         TEXT,
            subconta_id       INTEGER,
            tipo              TEXT,
            metodo_pagamento  TEXT,
            cartao_id         INTEGER,
            parcela_atual     INTEGER DEFAULT 1,
            total_parcelas    INTEGER DEFAULT 1,
            categoria_real_id INTEGER DEFAULT NULL,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metas (
            id             SERIAL PRIMARY KEY,
            usuario_id     INTEGER,
            mes            TEXT NOT NULL,
            meta_receita   REAL DEFAULT 0,
            meta_despesa   REAL DEFAULT 0,
            meta_resultado REAL DEFAULT 0,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)

    # Restaura plano de contas para usuários sem categorias
    cursor.execute("SELECT id FROM usuarios")
    usuarios = cursor.fetchall()
    for u in usuarios:
        cursor.execute(
            "SELECT COUNT(*) as total FROM categorias WHERE usuario_id=%s",
            (u["id"],)
        )
        if cursor.fetchone()["total"] == 0:
            _criar_dados_iniciais(cursor, u["id"])
            print(f"✅ Plano de contas criado para usuario_id={u['id']}")

    conn.commit()
    conn.close()


def _criar_dados_iniciais(cursor, uid: int):
    cursor.execute(
        "INSERT INTO categorias (usuario_id,nome,tipo) VALUES (%s,%s,%s) RETURNING id",
        (uid, "RECEITAS", "Receita")
    )
    id_rec = cursor.fetchone()["id"]

    cursor.execute(
        "INSERT INTO categorias (usuario_id,nome,tipo) VALUES (%s,%s,%s) RETURNING id",
        (uid, "DESPESAS FIXAS", "Despesa")
    )
    id_fix = cursor.fetchone()["id"]

    cursor.execute(
        "INSERT INTO categorias (usuario_id,nome,tipo) VALUES (%s,%s,%s) RETURNING id",
        (uid, "DESPESAS VARIÁVEIS", "Despesa")
    )
    id_var = cursor.fetchone()["id"]

    cursor.execute(
        "INSERT INTO categorias (usuario_id,nome,tipo) VALUES (%s,%s,%s) RETURNING id",
        (uid, "TRANSPORTE", "Despesa")
    )
    id_tra = cursor.fetchone()["id"]

    subcontas = [
        (uid, id_rec, "SALÁRIO / PRO-LABORE",  1),
        (uid, id_rec, "ALUGUÉIS RECEBIDOS",    0),
        (uid, id_rec, "OUTRAS RECEITAS",        0),
        (uid, id_fix, "ALUGUEL",               1),
        (uid, id_fix, "CONDOMINIO",            1),
        (uid, id_fix, "ENERGIA ELÉTRICA",      1),
        (uid, id_fix, "ÁGUA",                  1),
        (uid, id_fix, "INTERNET",              1),
        (uid, id_fix, "CELULAR",               1),
        (uid, id_fix, "SEGUROS / ASSINATURAS", 1),
        (uid, id_fix, "DAS / MEI",             1),
        (uid, id_var, "MERCADO",               0),
        (uid, id_var, "REFEIÇÕES / LAZER",     0),
        (uid, id_var, "FARMÁCIA / SAÚDE",      0),
        (uid, id_var, "ACADEMIA",              0),
        (uid, id_var, "OUTRAS DESPESAS",       0),
        (uid, id_tra, "COMBUSTÍVEL",           0),
        (uid, id_tra, "MANUTENÇÃO VEÍCULO",    0),
        (uid, id_tra, "UBER / TAXI",           0),
    ]
    cursor.executemany(
        "INSERT INTO subcontas (usuario_id,categoria_id,nome,fixa) VALUES (%s,%s,%s,%s)",
        subcontas
    )