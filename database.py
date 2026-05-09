import sqlite3
import bcrypt

DB_PATH = "financas.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _hash(senha: str) -> bytes:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt())


def _verificar_senha(senha: str, hash_salvo) -> bool:
    try:
        h = hash_salvo if isinstance(hash_salvo, bytes) else hash_salvo.encode()
        return bcrypt.checkpw(senha.encode(), h)
    except Exception:
        return False


def criar_usuario(nome: str, login: str, senha: str) -> dict:
    """Cria novo usuário. Retorna {'ok': True} ou {'ok': False, 'erro': '...'}"""
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT id FROM usuarios WHERE login = ?", (login,))
        if cur.fetchone():
            conn.close()
            return {"ok": False, "erro": "Este e-mail já está cadastrado."}
        cur.execute(
            "INSERT INTO usuarios (login, senha, nome) VALUES (?, ?, ?)",
            (login, _hash(senha).decode(), nome)
        )
        conn.commit()
        uid = cur.lastrowid
        conn.close()
        return {"ok": True, "id": uid}
    except Exception as ex:
        print(f"[criar_usuario] {ex}")
        return {"ok": False, "erro": "Erro interno ao criar usuário."}


def autenticar(login: str, senha: str):
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            "SELECT id, nome, login, senha FROM usuarios WHERE login = ?",
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


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ── USUARIOS ──────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            nome  TEXT NOT NULL
        )
    """)
    # Admin padrão só se não existir nenhum usuário
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO usuarios (login, senha, nome) VALUES (?, ?, ?)",
            ("admin", _hash("admin123").decode(), "Administrador")
        )

    # ── PERFIL ────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS perfil (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
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
    cursor.execute("PRAGMA table_info(perfil)")
    existentes = {r[1] for r in cursor.fetchall()}
    for col, tipo in [
        ("usuario_id","INTEGER"),
        ("rg","TEXT"),("data_nasc","TEXT"),("telefone","TEXT"),
        ("numero","TEXT"),("complemento","TEXT"),("bairro","TEXT"),
        ("cidade","TEXT"),("estado","TEXT"),("empresa","TEXT"),
        ("cargo","TEXT"),("salario","REAL"),("dia_pagamento","INTEGER"),
        ("vale","REAL"),("dia_vale","INTEGER"),
    ]:
        if col not in existentes:
            cursor.execute(f"ALTER TABLE perfil ADD COLUMN {col} {tipo}")

    # ── BANCOS ────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bancos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id    INTEGER,
            nome_banco    TEXT,
            saldo_inicial REAL,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)
    cursor.execute("PRAGMA table_info(bancos)")
    if "usuario_id" not in {r[1] for r in cursor.fetchall()}:
        cursor.execute("ALTER TABLE bancos ADD COLUMN usuario_id INTEGER")

    # ── CARTÕES ───────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cartoes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
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
    cursor.execute("PRAGMA table_info(cartoes)")
    if "usuario_id" not in {r[1] for r in cursor.fetchall()}:
        cursor.execute("ALTER TABLE cartoes ADD COLUMN usuario_id INTEGER")

    # ── CATEGORIAS ────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            nome       TEXT,
            tipo       TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)
    cursor.execute("PRAGMA table_info(categorias)")
    if "usuario_id" not in {r[1] for r in cursor.fetchall()}:
        cursor.execute("ALTER TABLE categorias ADD COLUMN usuario_id INTEGER")

    # ── SUBCONTAS ─────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subcontas (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id   INTEGER,
            categoria_id INTEGER,
            nome         TEXT,
            fixa         INTEGER DEFAULT 0,
            orcamento    REAL    DEFAULT 0,
            FOREIGN KEY(usuario_id)   REFERENCES usuarios(id),
            FOREIGN KEY(categoria_id) REFERENCES categorias(id)
        )
    """)
    cursor.execute("PRAGMA table_info(subcontas)")
    cols_sub = {r[1] for r in cursor.fetchall()}
    if "orcamento" not in cols_sub:
        cursor.execute("ALTER TABLE subcontas ADD COLUMN orcamento REAL DEFAULT 0")
    if "usuario_id" not in cols_sub:
        cursor.execute("ALTER TABLE subcontas ADD COLUMN usuario_id INTEGER")

    # ── TRANSAÇÕES ────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
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
    cursor.execute("PRAGMA table_info(transacoes)")
    cols_tr = {r[1] for r in cursor.fetchall()}
    if "categoria_real_id" not in cols_tr:
        cursor.execute("ALTER TABLE transacoes ADD COLUMN categoria_real_id INTEGER DEFAULT NULL")
    if "usuario_id" not in cols_tr:
        cursor.execute("ALTER TABLE transacoes ADD COLUMN usuario_id INTEGER")

    # ── METAS ─────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metas (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id     INTEGER,
            mes            TEXT NOT NULL,
            meta_receita   REAL DEFAULT 0,
            meta_despesa   REAL DEFAULT 0,
            meta_resultado REAL DEFAULT 0,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)
    cursor.execute("PRAGMA table_info(metas)")
    if "usuario_id" not in {r[1] for r in cursor.fetchall()}:
        cursor.execute("ALTER TABLE metas ADD COLUMN usuario_id INTEGER")

    # ── DADOS INICIAIS ────────────────────────────────────────────────────
    cursor.execute("SELECT COUNT(*) FROM categorias")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id FROM usuarios WHERE login='admin'")
        admin = cursor.fetchone()
        uid = admin["id"] if admin else 1
        _criar_dados_iniciais(cursor, uid)

    conn.commit()
    conn.close()


def _criar_dados_iniciais(cursor, uid: int):
    """Cria categorias e subcontas padrão para um novo usuário."""
    cursor.execute("INSERT INTO categorias (usuario_id,nome,tipo) VALUES (?,?,?)", (uid,"RECEITAS","Receita"))
    id_rec = cursor.lastrowid
    cursor.execute("INSERT INTO categorias (usuario_id,nome,tipo) VALUES (?,?,?)", (uid,"DESPESAS FIXAS","Despesa"))
    id_fix = cursor.lastrowid
    cursor.execute("INSERT INTO categorias (usuario_id,nome,tipo) VALUES (?,?,?)", (uid,"DESPESAS VARIÁVEIS","Despesa"))
    id_var = cursor.lastrowid
    cursor.execute("INSERT INTO categorias (usuario_id,nome,tipo) VALUES (?,?,?)", (uid,"TRANSPORTE","Despesa"))
    id_tra = cursor.lastrowid

    cursor.executemany("INSERT INTO subcontas (usuario_id,categoria_id,nome,fixa) VALUES (?,?,?,?)", [
        (uid,id_rec,"SALÁRIO / PRO-LABORE",1),(uid,id_rec,"ALUGUÉIS RECEBIDOS",0),(uid,id_rec,"OUTRAS RECEITAS",0),
        (uid,id_fix,"ALUGUEL",1),(uid,id_fix,"CONDOMINIO",1),(uid,id_fix,"ENERGIA ELÉTRICA",1),
        (uid,id_fix,"ÁGUA",1),(uid,id_fix,"INTERNET",1),(uid,id_fix,"CELULAR",1),
        (uid,id_fix,"SEGUROS / ASSINATURAS",1),(uid,id_fix,"DAS / MEI",1),
        (uid,id_var,"MERCADO",0),(uid,id_var,"REFEIÇÕES / LAZER",0),
        (uid,id_var,"FARMÁCIA / SAÚDE",0),(uid,id_var,"ACADEMIA",0),
        (uid,id_var,"OUTRAS DESPESAS",0),
        (uid,id_tra,"COMBUSTÍVEL",0),(uid,id_tra,"MANUTENÇÃO VEÍCULO",0),
        (uid,id_tra,"UBER / TAXI",0),
    ])


def migrar_dados_existentes():
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT id FROM usuarios WHERE login='admin'")
        admin = cur.fetchone()
        uid = admin["id"] if admin else 1
        for tabela in ["bancos","cartoes","categorias","subcontas","transacoes","metas","perfil"]:
            cur.execute(f"UPDATE {tabela} SET usuario_id=? WHERE usuario_id IS NULL", (uid,))
            if cur.rowcount > 0:
                print(f"  ✅ {tabela}: {cur.rowcount} registro(s) migrado(s)")
        conn.commit()
        conn.close()
        print("🎉 Migração concluída!")
    except Exception as ex:
        print(f"❌ Erro na migração: {ex}")