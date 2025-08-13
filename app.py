import json
import random
import os
from functools import wraps
import bcrypt
import mysql.connector.pooling
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# --- 1. CONFIGURAÇÃO DA APLICAÇÃO ---
app = Flask(__name__)
# A chave secreta é OBRIGATÓRIA para a sessão funcionar. Descomentei esta linha.
app.secret_key = 'teste' 

# --- 2. CONFIGURAÇÃO DO BANCO DE DADOS (ALTERE COM SEUS DADOS LOCAIS) ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root', # Lembre-se de colocar sua senha real aqui
    'database': 'meu_quiz_db',
    'pool_name': 'mypool_test',
    'pool_size': 5
}
try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(**DB_CONFIG)
except mysql.connector.Error as err:
    print(f"ERRO CRÍTICO: Não foi possível conectar ao banco de dados: {err}")
    db_pool = None

# --- 3. DECORATORS DE AUTENTICAÇÃO E AUTORIZAÇÃO ---
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

# --- 4. ROTAS DA APLICAÇÃO ---

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_or_register():
    if not db_pool:
        flash("Erro crítico no sistema. A conexão com o banco de dados falhou.", "danger")
        return redirect(url_for('home'))

    username_form = request.form.get('username')
    password_form = request.form.get('password')

    if not username_form or not password_form:
        flash('Nome de usuário e senha são obrigatórios.', 'warning')
        return redirect(url_for('home'))

    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, username, password_hash, is_admin FROM usuarios WHERE username = %s"
        cursor.execute(query, (username_form,))
        user_data = cursor.fetchone()

        if user_data:
            if bcrypt.checkpw(password_form.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
                session['user_id'] = user_data['id']
                session['username'] = user_data['username']
                session['is_admin'] = user_data['is_admin']
                return redirect(url_for('dashboard'))
            else:
                flash('Senha inválida.', 'danger')
                return redirect(url_for('home'))
        else:
            hashed_password = bcrypt.hashpw(password_form.encode('utf-8'), bcrypt.gensalt())
            insert_query = "INSERT INTO usuarios (username, password_hash) VALUES (%s, %s)"
            cursor.execute(insert_query, (username_form, hashed_password))
            conn.commit()
            
            session['user_id'] = cursor.lastrowid
            session['username'] = username_form
            session['is_admin'] = False
            flash(f'Bem-vindo, {username_form}! Sua conta foi criada.', 'success')
            return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"ERRO NA ROTA /login: {e}")
        flash("Ocorreu um erro inesperado. Tente novamente.", "danger")
        return redirect(url_for('home'))
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/escolha')
@login_required
def escolher_quiz():
    return render_template('escolher_quiz.html')

@app.route('/quiz/<categoria>')
@login_required
def quiz(categoria):
    try:
        with open('perguntas.json', 'r', encoding='utf-8') as f:
            todas_as_perguntas = json.load(f)
        
        perguntas_da_categoria = todas_as_perguntas.get(categoria)
        if perguntas_da_categoria is None:
            flash(f"A categoria '{categoria}' não foi encontrada.", "danger")
            return redirect(url_for('escolher_quiz'))

        random.shuffle(perguntas_da_categoria)
        return render_template('quiz.html', perguntas=perguntas_da_categoria, categoria=categoria)
    except Exception as e:
        print(f"ERRO NA ROTA /quiz/{categoria}: {e}")
        flash("Ocorreu um erro ao carregar o quiz.", "danger")
        return redirect(url_for('escolher_quiz'))

@app.route('/salvar_resultado', methods=['POST'])
@login_required
def salvar_resultado():
    data = request.get_json()
    if not all(k in data for k in ['acertos', 'erros', 'total_perguntas', 'categoria']):
        return jsonify({'message': 'Dados incompletos recebidos.'}), 400

    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO quiz_resultados (user_id, acertos, erros, total_perguntas, categoria) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(query, (session['user_id'], data['acertos'], data['erros'], data['total_perguntas'], data['categoria']))
        conn.commit()
        return jsonify({'message': 'Resultado salvo com sucesso!'})
    except Exception as e:
        print(f"ERRO AO SALVAR RESULTADO: {e}")
        return jsonify({'message': 'Erro ao salvar no banco de dados'}), 500
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/meus_resultados')
@login_required
def meus_resultados():
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM quiz_resultados WHERE user_id = %s ORDER BY data_tentativa DESC"
        cursor.execute(query, (session['user_id'],))
        resultados = cursor.fetchall()
        return render_template('meus_resultados.html', resultados=resultados)
    except Exception as e:
        print(f"ERRO AO BUSCAR MEUS RESULTADOS: {e}")
        flash("Não foi possível carregar seu histórico de resultados.", "danger")
        return redirect(url_for('dashboard'))
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/ranking_geral')
@login_required
@admin_required
def ranking_geral():
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT u.username, r.categoria, r.total_perguntas, MAX(r.acertos) AS melhor_pontuacao,
                   (SELECT r_inner.data_tentativa FROM quiz_resultados r_inner 
                    WHERE r_inner.user_id = u.id AND r_inner.categoria = r.categoria
                    ORDER BY r_inner.acertos DESC, r_inner.data_tentativa DESC LIMIT 1) AS data_tentativa
            FROM usuarios u JOIN quiz_resultados r ON u.id = r.user_id
            GROUP BY u.id, u.username, r.categoria, r.total_perguntas
            ORDER BY melhor_pontuacao DESC, data_tentativa ASC;
        """
        cursor.execute(query)
        ranking = cursor.fetchall()
        return render_template('ranking_geral.html', ranking=ranking)
    except Exception as e:
        print(f"ERRO AO GERAR RANKING GERAL: {e}")
        flash("Não foi possível carregar o ranking geral.", "danger")
        return redirect(url_for('dashboard'))
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

# --- 5. EXECUÇÃO DO SERVIDOR ---
if __name__ == '__main__':
    # A linha de execução foi corrigida para rodar corretamente.
    app.run(debug=True, host='0.0.0.0')