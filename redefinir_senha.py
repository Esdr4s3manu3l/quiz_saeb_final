import mysql.connector
import bcrypt
import getpass # Para digitar a senha de forma segura no terminal

# --- COPIE A CONFIGURAÇÃO DO SEU app.py PARA CÁ ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root', # Lembre-se de usar sua senha real do DB
    'database': 'meu_quiz_db'
}

def redefinir_senha_usuario():
    """Pede um usuário e uma nova senha, e atualiza o hash no banco de dados."""
    
    username = input("Digite o nome de usuário que terá a senha redefinida: ")
    if not username:
        print("Nome de usuário não pode ser vazio.")
        return

    password = getpass.getpass("Digite a NOVA senha para este usuário: ")
    if not password:
        print("A senha não pode ser vazia.")
        return

    try:
        # Conecta ao banco
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Criptografa a nova senha
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt)

        # Atualiza o hash da senha no banco de dados
        query = "UPDATE usuarios SET password_hash = %s WHERE username = %s"
        cursor.execute(query, (hashed_password, username))
        
        # Verifica se alguma linha foi realmente atualizada
        if cursor.rowcount == 0:
            print(f"ERRO: Usuário '{username}' não encontrado no banco de dados.")
            print("Dica: Use a tela de login para criar o usuário primeiro, depois rode este script.")
        else:
            conn.commit()
            print(f"\nSucesso! A senha para o usuário '{username}' foi redefinida.")

    except mysql.connector.Error as err:
        print(f"\nErro de banco de dados: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    redefinir_senha_usuario()