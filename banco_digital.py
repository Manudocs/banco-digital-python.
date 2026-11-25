"""
Banco digital simples no terminal (projeto de estudo).
Todos os dados são fictícios. NÃO use CPF ou senhas reais.
"""
import getpass
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime
from decimal import Decimal, InvalidOperation

ARQUIVO = "contas.json"
MAX_TENTATIVAS = 3


# ---------- Arquivo ----------
def carregar_contas():
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, encoding="utf-8") as f:
            return json.load(f)
    return {}


def salvar_contas(contas):
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(contas, f, ensure_ascii=False, indent=2)


# ---------- Segurança ----------
def gerar_hash(pin, salt_hex):
    """Guarda o PIN como hash (PBKDF2 + salt), nunca em texto puro."""
    return hashlib.pbkdf2_hmac(
        "sha256", pin.encode(), bytes.fromhex(salt_hex), 100_000
    ).hex()


def pin_correto(conta, pin):
    return hmac.compare_digest(conta["pin_hash"], gerar_hash(pin, conta["salt"]))


# ---------- Valores (guardados em centavos para evitar erro de arredondamento) ----------
def formatar(centavos):
    reais, cent = divmod(abs(centavos), 100)
    sinal = "-" if centavos < 0 else ""
    return f"{sinal}R$ {reais:,}".replace(",", ".") + f",{cent:02d}"


def ler_valor(mensagem):
    texto = input(mensagem).strip().replace(",", ".")
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        print("Valor inválido.")
        return None
    if not valor.is_finite() or valor <= 0 or valor.as_tuple().exponent < -2:
        print("Digite um valor positivo com até 2 casas decimais.")
        return None
    return int(valor * 100)


def registrar(conta, tipo, centavos, descricao):
    conta["extrato"].append({
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "tipo": tipo,
        "valor": centavos,
        "descricao": descricao,
    })


# ---------- Operações da conta ----------
def depositar(conta, centavos):
    conta["saldo"] += centavos
    registrar(conta, "Depósito", centavos, "Depósito em conta")


def sacar(conta, centavos):
    if centavos > conta["saldo"]:
        return False
    conta["saldo"] -= centavos
    registrar(conta, "Saque", -centavos, "Saque")
    return True


def transferir(origem, destino, centavos):
    if centavos > origem["saldo"]:
        return False
    origem["saldo"] -= centavos
    destino["saldo"] += centavos
    registrar(origem, "Pix enviado", -centavos, f"Para {destino['nome']}")
    registrar(destino, "Pix recebido", centavos, f"De {origem['nome']}")
    return True


# ---------- Telas ----------
def criar_conta(contas):
    print("\n--- Abrir conta (use dados fictícios) ---")
    nome = input("Nome: ").strip()
    cpf = input("CPF (11 números, fictício): ").strip()
    if not nome or not (cpf.isdigit() and len(cpf) == 11):
        print("Nome vazio ou CPF inválido.")
        return
    if cpf in contas:
        print("Já existe uma conta com esse CPF.")
        return
    pin = getpass.getpass("Crie um PIN de 4 números: ")
    if not (pin.isdigit() and len(pin) == 4):
        print("O PIN precisa ter exatamente 4 números.")
        return
    salt = secrets.token_hex(16)
    contas[cpf] = {
        "nome": nome,
        "salt": salt,
        "pin_hash": gerar_hash(pin, salt),
        "saldo": 0,
        "extrato": [],
    }
    salvar_contas(contas)
    print("Conta criada com sucesso!")


def entrar(contas):
    print("\n--- Entrar ---")
    cpf = input("CPF: ").strip()
    conta = contas.get(cpf)
    for _ in range(MAX_TENTATIVAS):
        pin = getpass.getpass("PIN: ")
        # mensagem igual para CPF ou PIN errado, para não revelar quais CPFs existem
        if conta and pin_correto(conta, pin):
            return cpf
        print("CPF ou PIN incorreto.")
    print("Muitas tentativas. Voltando ao menu.")
    return None


def mostrar_extrato(conta):
    print("\n--- Extrato ---")
    if not conta["extrato"]:
        print("Nenhuma movimentação ainda.")
        return
    for mov in conta["extrato"]:
        print(f"{mov['data']} | {mov['tipo']:<12} | {formatar(mov['valor']):>14} | {mov['descricao']}")


def menu_conta(contas, cpf):
    conta = contas[cpf]
    while True:
        print(f"\nOlá, {conta['nome']}!  Saldo: {formatar(conta['saldo'])}")
        print("1. Depositar  2. Sacar  3. Enviar Pix  4. Extrato  5. Sair")
        opcao = input("Escolha: ").strip()

        if opcao == "1":
            valor = ler_valor("Valor do depósito: ")
            if valor:
                depositar(conta, valor)
                salvar_contas(contas)
                print("Depósito realizado!")
        elif opcao == "2":
            valor = ler_valor("Valor do saque: ")
            if valor:
                print("Saque realizado!" if sacar(conta, valor) else "Saldo insuficiente.")
                salvar_contas(contas)
        elif opcao == "3":
            cpf_destino = input("CPF de quem vai receber: ").strip()
            destino = contas.get(cpf_destino)
            if destino is None or cpf_destino == cpf:
                print("Destinatário não encontrado.")
                continue
            valor = ler_valor(f"Valor do Pix para {destino['nome']}: ")
            if valor:
                print("Pix enviado!" if transferir(conta, destino, valor) else "Saldo insuficiente.")
                salvar_contas(contas)
        elif opcao == "4":
            mostrar_extrato(conta)
        elif opcao == "5":
            print("Até logo!")
            return
        else:
            print("Opção inválida.")


def main():
    contas = carregar_contas()
    while True:
        print("\n=== Banco Digital ===")
        print("1. Abrir conta  2. Entrar  3. Sair")
        opcao = input("Escolha: ").strip()
        if opcao == "1":
            criar_conta(contas)
        elif opcao == "2":
            cpf = entrar(contas)
            if cpf:
                menu_conta(contas, cpf)
        elif opcao == "3":
            break
        else:
            print("Opção inválida.")


if __name__ == "__main__":
    main()
