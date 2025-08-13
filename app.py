import json
import random
import os
import logging
from functools import wraps
import bcrypt
import mysql.connector.pooling
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para o ambiente (para desenvolvimento local)
load_dotenv()

# --- 1. CONFIGURAÇÃO DA APLICAÇÃO ---
app = Flask(__name__)
# Lê a chave secreta a partir das variáveis de ambiente para segurança máxima
app.secret_key = os.environ.get('SECRET_KEY')

# Configura logs de erro para um arquivo, essencial para depurar em produção
if not app.debug:
    logging.basicConfig(filename='app.log', level=logging.ERROR, format='%(asctime)s %(levelname)s:%(message)s [in %(pathname)s:%(lineno)d]')

# --- 2. CONFIGURAÇÃO DO BANCO DE DADOS ---
try:
    # Usa as variáveis de ambiente para conectar ao banco de dados
    db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name='render_pool', pool_size=5,
        host=os.environ.get('DB_HOST'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME')
    )
    app.logger.info("Pool de conexões com o banco de dados criado com sucesso.")
except mysql.connector.Error as err:
    app.logger.critical(f"CRÍTICO: Não foi possível conectar ao banco de dados na inicialização: {err}")
    db_pool = None

# --- 3. DECORATORS (sem alterações) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa fazer login para acessar esta página.', 'warning')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Acesso negado. Esta área é restrita para administradores.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- 4. ROTAS DA APLICAÇÃO (sem alterações na lógica) ---
@app.route('/')
def home():
    return render_template('login.html')

# (Cole aqui todas as suas outras rotas: /login, /dashboard, /escolha, /quiz/<categoria>, etc.)
# A versão de produção que gerei anteriormente está perfeita e não precisa de mudanças na lógica das rotas.
# ...

# --- 5. EXECUÇÃO ---
if __name__ == '__main__':
    # Este bloco não será usado pelo Render, mas é útil para testes locais.
    # O Gunicorn será o responsável por iniciar o app.
    app.run(debug=False)
