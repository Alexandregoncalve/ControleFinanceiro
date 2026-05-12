from database import db_session

def ajustar_sequencias():
    print("🔄 Corrigindo contadores de ID no PostgreSQL...")
    with db_session() as cur:
        try:
            # Lista de tabelas do seu projeto
            tabelas = ["usuarios", "bancos", "categorias", "subcontas", "transacoes", "metas"]
            
            for tabela in tabelas:
                # Este comando SQL reseta o contador de ID para o próximo número disponível real
                sql = f"SELECT setval(pg_get_serial_sequence('{tabela}', 'id'), COALESCE(MAX(id), 0) + 1, false) FROM {tabela};"
                cur.execute(sql)
                print(f"✅ Tabela {tabela}: OK")
            
            # Aproveitamos para limpar as categorias vazias sem subcontas (o "lixo" do dropdown)
            cur.execute("DELETE FROM categorias WHERE id NOT IN (SELECT DISTINCT categoria_id FROM subcontas)")
            print(f"🧹 Limpeza de categorias órfãs: Concluída ({cur.rowcount} removidas)")
            
        except Exception as e:
            print(f"❌ Erro técnico: {e}")

if __name__ == "__main__":
    ajustar_sequencias()