import os
from database import get_connection

def executar_limpeza():
    print("🚀 Iniciando limpeza de categorias vazias...")
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Remove categorias que não possuem subcontas (o "lixo" que aparece nos dropdowns)
        cur.execute("""
            DELETE FROM categorias 
            WHERE id NOT IN (SELECT DISTINCT categoria_id FROM subcontas)
        """)
        removidos = cur.rowcount
        conn.commit()
        print(f"✅ Sucesso! Foram removidas {removidos} categorias vazias.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    executar_limpeza()