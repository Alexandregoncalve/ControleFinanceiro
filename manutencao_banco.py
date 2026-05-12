from database import get_connection

def executar_manutencao():
    conn = get_connection()
    cur = conn.cursor()
    
    # Lista de tabelas para sincronizar IDs
    tabelas = ["usuarios", "perfil", "bancos", "cartoes", "categorias", "subcontas", "transacoes", "metas"]
    
    try:
        print("🔄 Sincronizando sequências (IDs)...")
        for t in tabelas:
            # Ajusta o contador para o próximo ID disponível real
            cur.execute(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), COALESCE(MAX(id), 1)) FROM {t};")
        
        print("🧹 Limpando categorias sem subcontas (Contas Pai vazias)...")
        cur.execute("""
            DELETE FROM categorias 
            WHERE id NOT IN (SELECT DISTINCT categoria_id FROM subcontas)
        """)
        removidos = cur.rowcount
        
        conn.commit()
        print(f"✅ Sucesso! Sequências ajustadas e {removidos} categorias órfãs removidas.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    executar_manutencao()