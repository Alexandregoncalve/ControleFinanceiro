from database import get_connection

def sincronizar_sequencias():
    conn = get_connection()
    cur = conn.cursor()
    
    tabelas = ["usuarios", "perfil", "bancos", "cartoes", "categorias", "subcontas", "transacoes", "metas"]
    
    try:
        print("🔄 Sincronizando sequências do PostgreSQL...")
        for tabela in tabelas:
            # Este comando ajusta o próximo valor da sequência para o maior ID atual + 1
            cur.execute(f"SELECT setval(pg_get_serial_sequence('{tabela}', 'id'), COALESCE(MAX(id), 1)) FROM {tabela};")
        
        conn.commit()
        print("✅ Sequências sincronizadas com sucesso!")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao sincronizar: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    sincronizar_sequencias()