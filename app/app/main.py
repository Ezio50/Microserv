import psycopg2
from flask import Flask, request, jsonify
import logging

app = Flask(__name__)

DATABASE_CONFIG = {
    "dbname": "microservice_db",
    "user": "user",
    "password": "password",
    "host": "db",  # Имя сервиса из docker-compose.yml
    "port": 5432
}

def get_db_connection():
    return psycopg2.connect(**DATABASE_CONFIG)

# Инициализация таблицы
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# API-эндпоинты (без изменений)

@app.route('/')
def home():
    return """
    <h1>Микросервис работает!</h1>
    <p>Доступные эндпоинты:</p>
    <ul>
        <li>GET /items - Получить список всех элементов</li>
        <li>POST /items - Создать новый элемент</li>
        <li>GET /items/&lt;id&gt; - Получить элемент по ID</li>
        <li>PATCH /items/&lt;id&gt; - Обновить элемент по ID</li>
        <li>DELETE /items/&lt;id&gt; - Удалить элемент по ID</li>
    </ul>
    """

@app.route('/items', methods=['GET'])
def get_items():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM items')
    items = cursor.fetchall()
    conn.close()
    return jsonify([
        {'id': item[0], 'name': item[1], 'description': item[2]} for item in items
    ]), 200

@app.route('/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM items WHERE id = %s', (item_id,))
    item = cursor.fetchone()
    conn.close()
    if item:
        return jsonify({'id': item[0], 'name': item[1], 'description': item[2]}), 200
    return jsonify({'error': 'Item not found'}), 404

logging.basicConfig(level=logging.INFO)

@app.before_request
def log_request():
    logging.info(f'Received request: {request.method} {request.url}')

@app.after_request
def log_response(response):
    logging.info(f'Response: {response.status_code}')
    return response

@app.route('/items', methods=['POST'])
def create_item():
    data = request.json
    if 'name' not in data or 'description' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO items (name, description) VALUES (%s, %s)', (data['name'], data['description']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Item created'}), 201

@app.route('/items/<int:item_id>', methods=['PATCH'])
def update_item(item_id):
    data = request.json
    fields = []
    values = []

    if 'name' in data:
        fields.append('name = %s')
        values.append(data['name'])
    if 'description' in data:
        fields.append('description = %s')
        values.append(data['description'])

    if not fields:
        return jsonify({'error': 'No fields to update'}), 400

    values.append(item_id)
    query = f'UPDATE items SET {", ".join(fields)} WHERE id = %s RETURNING id'

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, values)
    updated_item = cursor.fetchone()
    conn.commit()
    conn.close()
    if updated_item:
        return jsonify({'message': 'Item updated'}), 200
    return jsonify({'error': 'Item not found'}), 404

@app.route('/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM items WHERE id = %s RETURNING id', (item_id,))
    deleted_item = cursor.fetchone()
    conn.commit()
    conn.close()
    if deleted_item:
        return jsonify({'message': 'Item deleted'}), 200
    return jsonify({'error': 'Item not found'}), 404

# Дополните остальные эндпоинты аналогично...

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
