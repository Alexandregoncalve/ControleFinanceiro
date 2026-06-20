import os
import bcrypt
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

# Quando rodar local usa localhost, quando rodar no Railway usa a variável de ambiente
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:Discovery$010203@localhost:5432/financas"
)

# URL para o Railway apontar para sua máquina (atualizar no Railway Variables)
# DATABASE_URL = postgresql://postgres:Discovery$010203@186.237.22.34:5432/financas


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def get_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


@contextmanager
def db_session():
    conn = get_connection()
    cur  = get_cursor(conn)
    try:
        yield cur
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


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
        with db_session() as cur:
            cur.execute("SELECT id FROM usuarios WHERE login = %s", (login,))
            if cur.fetchone():
                return {"ok": False, "erro": "Este e-mail já está cadastrado."}
            cur.execute(
                "INSERT INTO usuarios (login, senha, nome) VALUES (%s, %s, %s) RETURNING id",
                (login, _hash(senha), nome)
            )
            uid = cur.fetchone()["id"]
            _criar_dados_iniciais(cur, uid)
            return {"ok": True, "id": uid}
    except Exception as ex:
        print(f"[criar_usuario] {ex}")
        return {"ok": False, "erro": "Erro interno ao criar usuário."}


def autenticar(login: str, senha: str):
    try:
        with db_session() as cur:
            cur.execute(
                "SELECT id, nome, login, senha FROM usuarios WHERE login = %s",
                (login,)
            )
            row = cur.fetchone()
            if row and _verificar_senha(senha, row["senha"]):
                return {"id": row["id"], "nome": row["nome"], "login": row["login"]}
        return None
    except Exception as ex:
        print(f"[autenticar] {ex}")
        return None


def init_db():
    with db_session() as cursor:

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id    SERIAL PRIMARY KEY,
                login TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                nome  TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS perfil (
                id            SERIAL PRIMARY KEY,
                usuario_id    INTEGER UNIQUE,
                nome          TEXT, cpf TEXT, rg TEXT, email TEXT,
                data_nasc     TEXT, telefone TEXT, cep TEXT,
                logradouro    TEXT, numero TEXT, complemento TEXT,
                bairro        TEXT, cidade TEXT, estado TEXT,
                empresa       TEXT, cargo TEXT, salario REAL,
                dia_pagamento INTEGER, vale REAL, dia_vale INTEGER,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bancos (
                id            SERIAL PRIMARY KEY,
                usuario_id    INTEGER,
                nome_banco    TEXT,
                saldo_inicial REAL,
                data_criacao  VARCHAR(10),
                agencia       VARCHAR(20),
                numero_conta  VARCHAR(30),
                codigo_banco  VARCHAR(10),
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
                banco_id          INTEGER,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY(banco_id)   REFERENCES bancos(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transferencias (
                id         SERIAL PRIMARY KEY,
                usuario_id INTEGER,
                data       TEXT,
                valor      REAL,
                banco_orig INTEGER,
                banco_dest INTEGER,
                descricao  TEXT,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY(banco_orig) REFERENCES bancos(id),
                FOREIGN KEY(banco_dest) REFERENCES bancos(id)
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conciliacoes (
                id          SERIAL PRIMARY KEY,
                usuario_id  INTEGER,
                banco_id    INTEGER,
                data_ini    TEXT,
                data_fim    TEXT,
                data_exec   TEXT,
                total_banco INTEGER DEFAULT 0,
                conciliados INTEGER DEFAULT 0,
                pendentes   INTEGER DEFAULT 0,
                extras      INTEGER DEFAULT 0,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conciliacao_itens (
                id              SERIAL PRIMARY KEY,
                conciliacao_id  INTEGER,
                status          TEXT,
                data            TEXT,
                descricao       TEXT,
                valor           REAL,
                tipo            TEXT,
                transacao_id    INTEGER,
                FOREIGN KEY(conciliacao_id) REFERENCES conciliacoes(id)
            )
        """)

        _migrar_colunas(cursor)


def _migrar_colunas(cursor):
    migracoes = [
        ("transacoes", "banco_id",     "INTEGER REFERENCES bancos(id)"),
        ("bancos",     "codigo_banco", "VARCHAR(10)"),
    ]
    for tabela, coluna, definicao in migracoes:
        try:
            cursor.execute(f"""
                ALTER TABLE {tabela}
                ADD COLUMN IF NOT EXISTS {coluna} {definicao}
            """)
            print(f"[migrate] {tabela}.{coluna} OK")
        except Exception as ex:
            print(f"[migrate] {tabela}.{coluna} ignorado: {ex}")


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

    cursor.execute(
        "INSERT INTO categorias (usuario_id,nome,tipo) VALUES (%s,%s,%s) RETURNING id",
        (uid, "TRANSFERÊNCIAS", "Despesa")
    )
    id_transf = cursor.fetchone()["id"]

    subcontas = [
        (uid, id_rec,    "SALÁRIO / PRO-LABORE",  1),
        (uid, id_rec,    "ALUGUÉIS RECEBIDOS",    0),
        (uid, id_rec,    "OUTRAS RECEITAS",        0),
        (uid, id_fix,    "ALUGUEL",                1),
        (uid, id_fix,    "CONDOMINIO",             1),
        (uid, id_fix,    "ENERGIA ELÉTRICA",       1),
        (uid, id_fix,    "ÁGUA",                   1),
        (uid, id_fix,    "INTERNET",               1),
        (uid, id_fix,    "CELULAR",                1),
        (uid, id_fix,    "SEGUROS / ASSINATURAS",  1),
        (uid, id_fix,    "DAS / MEI",              1),
        (uid, id_var,    "MERCADO",                0),
        (uid, id_var,    "REFEIÇÕES / LAZER",      0),
        (uid, id_var,    "FARMÁCIA / SAÚDE",       0),
        (uid, id_var,    "ACADEMIA",               0),
        (uid, id_var,    "OUTRAS DESPESAS",        0),
        (uid, id_tra,    "COMBUSTÍVEL",            0),
        (uid, id_tra,    "MANUTENÇÃO VEÍCULO",     0),
        (uid, id_tra,    "UBER / TAXI",            0),
        (uid, id_transf, "TRANSFERÊNCIAS",         0),
    ]
    cursor.executemany(
        "INSERT INTO subcontas (usuario_id,categoria_id,nome,fixa) VALUES (%s,%s,%s,%s)",
        subcontas
    )


def migrar_dados_existentes():
    try:
        with db_session() as cur:
            cur.execute("SELECT id FROM usuarios WHERE login='admin'")
            admin = cur.fetchone()
            uid = admin["id"] if admin else 1
            for tabela in ["bancos","cartoes","categorias","subcontas","transacoes","metas","perfil"]:
                cur.execute(f"UPDATE {tabela} SET usuario_id=%s WHERE usuario_id IS NULL", (uid,))
                if cur.rowcount > 0:
                    print(f"  ✅ {tabela}: {cur.rowcount} registro(s) migrado(s)")
        print("🎉 Migração concluída!")
    except Exception as ex:
        print(f"❌ Erro na migração: {ex}")