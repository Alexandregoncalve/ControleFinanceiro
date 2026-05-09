"""
Script de limpeza do projeto ControleFinanceiro.
Remove arquivos e pastas desnecessários com confirmação antes de excluir.
"""
import os
import shutil

BASE = r"C:\Alexandre\ControleFinanceiro"

# ── Arquivos na raiz para excluir ─────────────────────────────────────────────
ARQUIVOS = [
    "diagnostico.py",
    "diagnostico2.py",
    "financas.txt",
    "MAIN VALIDO.txt",
    "main.spec",
    "verificabanco.py",
    "verifica_plano_contas.py",
    "migrar_dividas.py",
    "migrar_multiusuario.py",
    "sqlite-jdbc-3.45.3.0.jar",
    "OLD_financas.db",
    "img.png",
]

# ── Pastas inteiras para excluir ──────────────────────────────────────────────
PASTAS = [
    "build",
    "dist",
    ".idea",
    "Backup",
    "database",
    "downloads",
    "__pycache__",
]

print("=" * 55)
print("   LIMPEZA DO PROJETO - CONTROLE FINANCEIRO")
print("=" * 55)

# Lista o que será excluído
print("\n📄 ARQUIVOS que serão excluídos:")
for a in ARQUIVOS:
    caminho = os.path.join(BASE, a)
    status = "✅ encontrado" if os.path.exists(caminho) else "⬜ não existe"
    print(f"   {status} — {a}")

print("\n📁 PASTAS que serão excluídas:")
for p in PASTAS:
    caminho = os.path.join(BASE, p)
    status = "✅ encontrada" if os.path.exists(caminho) else "⬜ não existe"
    print(f"   {status} — {p}\\")

# Confirmação
print("\n" + "=" * 55)
print("⚠️  ATENÇÃO: Esta ação não pode ser desfeita!")
print("   Certifique-se de ter backup do financas.db")
print("=" * 55)
resposta = input("\nDigite SIM para confirmar a limpeza: ").strip().upper()

if resposta != "SIM":
    print("\n❌ Operação cancelada. Nenhum arquivo foi excluído.")
    input("\nPressione Enter para fechar...")
    exit()

# Executa limpeza
print("\n🧹 Iniciando limpeza...\n")
erros = []

for a in ARQUIVOS:
    caminho = os.path.join(BASE, a)
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
            print(f"  🗑️  Arquivo excluído: {a}")
    except Exception as ex:
        erros.append(f"{a}: {ex}")
        print(f"  ❌ Erro ao excluir {a}: {ex}")

for p in PASTAS:
    caminho = os.path.join(BASE, p)
    try:
        if os.path.exists(caminho):
            shutil.rmtree(caminho)
            print(f"  🗑️  Pasta excluída: {p}\\")
    except Exception as ex:
        erros.append(f"{p}: {ex}")
        print(f"  ❌ Erro ao excluir {p}\\: {ex}")

print("\n" + "=" * 55)
if erros:
    print(f"⚠️  Limpeza concluída com {len(erros)} erro(s).")
    for e in erros:
        print(f"   - {e}")
else:
    print("🎉 Limpeza concluída com sucesso!")
    print("   Projeto está limpo e organizado.")
print("=" * 55)

input("\nPressione Enter para fechar...")