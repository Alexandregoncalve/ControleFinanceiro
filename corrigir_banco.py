from database import db_session

def consertar_tudo():
    print("🚀 Iniciando manutenção do banco...")
    with db_session() as cur:
        try:
            # 1. Ajusta o contador de IDs de todas as tabelas (Resolve o erro de 'Duplicate Key')
            tabelas = ["usuarios", "bancos", "categorias", "subcontas", "transacoes", "metas"]
            for t in tabelas:
                cur.execute(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), COALESCE(MAX(id), 0) + 1, false) FROM {t};")
            
            # 2. Remove as categorias que não tem subcontas (Limpa o lixo do Dropdown)
            cur.execute("""
                DELETE FROM categorias 
                WHERE id NOT IN (SELECT DISTINCT categoria_id FROM subcontas)
            """)
            removidos = cur.rowcount
            
            print(f"✅ IDs sincronizados e {removidos} categorias vazias removidas!")
        except Exception as e:
            print(f"❌ Erro: {e}")

if __name__ == "__main__":
    consertar_tudo()