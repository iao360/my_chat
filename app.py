from flask import Flask, render_template, request, jsonify
from datetime import datetime
import requests

app = Flask(__name__)

# ========== НАСТРОЙКИ SUPABASE ==========
SUPABASE_URL = "https://llkfbzaancbjlyxwjqmo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxsa2ZiemFhbmNiamx5eHdqcW1vIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUxNDU2OTEsImV4cCI6MjA5MDcyMTY5MX0._ZgQ9uVejj5gJwOT9_B5Z3sAMpqHMXEVwSal4Dkls64"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def supabase_get(table, select="*", eq_column=None, eq_value=None, limit=None, order=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}"
    if eq_column and eq_value:
        url += f"&{eq_column}=eq.{eq_value}"
    if order:
        url += f"&order={order}"
    if limit:
        url += f"&limit={limit}"
    response = requests.get(url, headers=HEADERS)
    return response.json()

def supabase_post(table, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    response = requests.post(url, headers=HEADERS, json=data)
    return response.json() if response.status_code == 201 else None

def supabase_delete(table, eq_column, eq_value):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{eq_column}=eq.{eq_value}"
    response = requests.delete(url, headers=HEADERS)
    return response.status_code == 204

def supabase_delete_all(table):
    """Удалить все записи из таблицы"""
    url = f"{SUPABASE_URL}/rest/v1/{table}?select=id"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        rows = response.json()
        for row in rows:
            supabase_delete(table, "id", row["id"])
    return True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/users')
def get_users():
    users = supabase_get("users", select="username", eq_column="is_approved", eq_value=1)
    if isinstance(users, dict) and "error" in users:
        return jsonify([])
    usernames = [u["username"] for u in users if u["username"] != "admin"]
    return jsonify(usernames)

@app.route('/api/pending')
def get_pending():
    pending = supabase_get("pending", select="username")
    if isinstance(pending, dict) and "error" in pending:
        return jsonify([])
    usernames = [p["username"] for p in pending]
    return jsonify(usernames)

@app.route('/api/messages')
def get_messages():
    messages = supabase_get("messages", select="*", order="timestamp.desc", limit=100)
    if isinstance(messages, dict) and "error" in messages:
        return jsonify([])
    messages.sort(key=lambda x: x.get("timestamp", 0))
    return jsonify(messages)

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        existing = supabase_get("users", select="username", eq_column="username", eq_value=username)
        if existing and len(existing) > 0:
            return jsonify({'success': False, 'error': 'Пользователь уже существует'})
        
        existing_pending = supabase_get("pending", select="username", eq_column="username", eq_value=username)
        if existing_pending and len(existing_pending) > 0:
            return jsonify({'success': False, 'error': 'Заявка уже отправлена'})
        
        supabase_post("pending", {"username": username, "password": password})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        users = supabase_get("users", select="*", eq_column="username", eq_value=username)
        
        if users and len(users) > 0:
            user = users[0]
            if user.get("password") == password and user.get("is_approved") == 1:
                return jsonify({'success': True})
        
        return jsonify({'success': False, 'error': 'Неверный логин или пароль'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/approve', methods=['POST'])
def approve():
    try:
        data = request.json
        username = data.get('username')
        
        pending = supabase_get("pending", select="*", eq_column="username", eq_value=username)
        if not pending or len(pending) == 0:
            return jsonify({'success': False})
        
        password = pending[0]["password"]
        supabase_post("users", {"username": username, "password": password, "is_approved": 1})
        supabase_delete("pending", "username", username)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/reject', methods=['POST'])
def reject():
    try:
        data = request.json
        username = data.get('username')
        supabase_delete("pending", "username", username)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete_user', methods=['POST'])
def delete_user():
    """Админ удаляет пользователя и все его сообщения"""
    try:
        data = request.json
        username = data.get('username')
        
        # Удаляем сообщения пользователя
        messages = supabase_get("messages", select="id", eq_column="author", eq_value=username)
        if messages and len(messages) > 0:
            for msg in messages:
                supabase_delete("messages", "id", msg["id"])
        
        # Удаляем пользователя
        supabase_delete("users", "username", username)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete_message', methods=['POST'])
def delete_message():
    """Пользователь удаляет своё сообщение"""
    try:
        data = request.json
        message_id = data.get('message_id')
        supabase_delete("messages", "id", message_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/clear_chat', methods=['POST'])
def clear_chat():
    """Админ полностью очищает чат"""
    try:
        supabase_delete_all("messages")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send_message', methods=['POST'])
def send_message():
    try:
        data = request.json
        result = supabase_post("messages", {
            "author": data.get('author'),
            "text": data.get('text'),
            "time": data.get('time'),
            "timestamp": data.get('timestamp')
        })
        return jsonify({'success': True, 'message_id': result.get('id') if result else None})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
