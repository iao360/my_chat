from flask import Flask, render_template, request, jsonify
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)

# На Render можно писать только в /tmp
DB_PATH = '/tmp/chat.db'

def init_db():
    """Создаёт таблицы, если их нет"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Таблица одобренных пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, 
                  password TEXT, 
                  is_approved INTEGER DEFAULT 0)''')
    
    # Таблица заявок на регистрацию
    c.execute('''CREATE TABLE IF NOT EXISTS pending
                 (username TEXT PRIMARY KEY, 
                  password TEXT)''')
    
    # Таблица сообщений
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  author TEXT, 
                  text TEXT, 
                  time TEXT, 
                  timestamp INTEGER)''')
    
    # Добавляем админа, если его нет
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, is_approved) VALUES ('admin', 'Xk9#mP2$vL7@qR4!wN6', 1)")
        print("✅ Админ создан")
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

# ВАЖНО: вызываем init_db() ПРИ ЗАПУСКЕ
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/users')
def get_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE is_approved = 1 AND username != 'admin'")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return jsonify(users)

@app.route('/api/pending')
def get_pending():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM pending")
    pending = [row[0] for row in c.fetchall()]
    conn.close()
    return jsonify(pending)

@app.route('/api/messages')
def get_messages():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT author, text, time, timestamp FROM messages ORDER BY timestamp ASC")
    messages = [{'author': row[0], 'text': row[1], 'time': row[2], 'timestamp': row[3]} for row in c.fetchall()]
    conn.close()
    return jsonify(messages)

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        if c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Пользователь уже существует'})
        
        c.execute("SELECT * FROM pending WHERE username = ?", (username,))
        if c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Заявка уже отправлена'})
        
        c.execute("INSERT INTO pending VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ? AND is_approved = 1", (username, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Неверный логин или пароль'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/approve', methods=['POST'])
def approve():
    try:
        data = request.json
        username = data.get('username')
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT password FROM pending WHERE username = ?", (username,))
        row = c.fetchone()
        
        if row:
            password = row[0]
            c.execute("INSERT INTO users (username, password, is_approved) VALUES (?, ?, 1)", (username, password))
            c.execute("DELETE FROM pending WHERE username = ?", (username,))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        
        conn.close()
        return jsonify({'success': False})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/reject', methods=['POST'])
def reject():
    try:
        data = request.json
        username = data.get('username')
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM pending WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send_message', methods=['POST'])
def send_message():
    try:
        data = request.json
        author = data.get('author')
        text = data.get('text')
        time = data.get('time')
        timestamp = data.get('timestamp')
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO messages (author, text, time, timestamp) VALUES (?, ?, ?, ?)",
                  (author, text, time, timestamp))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
