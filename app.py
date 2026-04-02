from flask import Flask, render_template, request, jsonify
from datetime import datetime
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, is_approved INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS pending
                 (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, text TEXT, time TEXT, timestamp INTEGER)''')
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, is_approved) VALUES ('admin', 'Xk9#mP2$vL7@qR4!wN6', 1)")
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/users')
def get_users():
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE is_approved = 1 AND username != 'admin'")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return jsonify(users)

@app.route('/api/pending')
def get_pending():
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("SELECT username FROM pending")
    pending = [row[0] for row in c.fetchall()]
    conn.close()
    return jsonify(pending)

@app.route('/api/messages')
def get_messages():
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("SELECT author, text, time, timestamp FROM messages ORDER BY timestamp ASC")
    messages = [{'author': row[0], 'text': row[1], 'time': row[2], 'timestamp': row[3]} for row in c.fetchall()]
    conn.close()
    return jsonify(messages)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    conn = sqlite3.connect('chat.db')
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

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ? AND is_approved = 1", (username, password))
    user = c.fetchone()
    conn.close()
    if user:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Неверный логин или пароль'})

@app.route('/api/approve', methods=['POST'])
def approve():
    data = request.json
    username = data.get('username')
    conn = sqlite3.connect('chat.db')
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

@app.route('/api/reject', methods=['POST'])
def reject():
    data = request.json
    username = data.get('username')
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("DELETE FROM pending WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/send_message', methods=['POST'])
def send_message():
    data = request.json
    author = data.get('author')
    text = data.get('text')
    time = data.get('time')
    timestamp = data.get('timestamp')
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (author, text, time, timestamp) VALUES (?, ?, ?, ?)",
              (author, text, time, timestamp))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()
    print("Server started! Open in browser: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)