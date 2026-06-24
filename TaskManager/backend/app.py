from flask import Flask, request, jsonify
from flask_cors import CORS
from database import *
from ai_service import ai_suggest_priority
import os

app = Flask(__name__)

# Разрешаем все адреса для CORS
CORS(app, origins="*")

# ID пользователя по умолчанию (для демонстрации без авторизации)
DEFAULT_USER_ID = 1

# Эндпоинты задач

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    status = request.args.get('status')
    tasks = get_user_tasks(DEFAULT_USER_ID, status)
    return jsonify([{
        "id": t[0],
        "title": t[2],
        "description": t[3],
        "priority": t[4],
        "status": t[5],
        "created_at": t[6],
        "updated_at": t[7],
        "deadline": t[8]
    } for t in tasks])

@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.json
    title = data.get('title')
    description = data.get('description', '')
    priority = data.get('priority')
    
    if not title:
        return jsonify({"error": "Title is required"}), 400
    
    if not priority:
        priority = ai_suggest_priority(description or title)
    
    if add_task(DEFAULT_USER_ID, title, description, priority):
        return jsonify({"success": True, "priority": priority})
    return jsonify({"error": "Failed to create task"}), 400

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.json
    status = data.get('status')
    if not status:
        return jsonify({"error": "Status required"}), 400
    
    if update_task_status(task_id, DEFAULT_USER_ID, status):
        return jsonify({"success": True})
    return jsonify({"error": "Task not found"}), 404

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task_route(task_id):
    if delete_task(task_id, DEFAULT_USER_ID):
        return jsonify({"success": True})
    return jsonify({"error": "Task not found"}), 404

@app.route('/api/tasks/search', methods=['GET'])
def search_tasks_route():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    tasks = search_tasks(DEFAULT_USER_ID, query)
    return jsonify([{
        "id": t[0],
        "title": t[2],
        "description": t[3],
        "priority": t[4],
        "status": t[5],
        "created_at": t[6],
        "updated_at": t[7]
    } for t in tasks])

# Эндпоинты статистики

@app.route('/api/stats', methods=['GET'])
def get_stats_route():
    stats = get_stats(DEFAULT_USER_ID)
    avg_time = get_avg_completion_time(DEFAULT_USER_ID)
    priority_dist = get_priority_distribution(DEFAULT_USER_ID)
    overdue = len(get_overdue_tasks(DEFAULT_USER_ID))
    timeline = get_status_timeline(DEFAULT_USER_ID)
    
    return jsonify({
        "stats": stats,
        "avg_completion_days": avg_time,
        "priority_distribution": priority_dist,
        "overdue_count": overdue,
        "timeline": [{"date": t[0], "status": t[1], "count": t[2]} for t in timeline]
    })

# Запуск сервера

if __name__ == '__main__':
    init_db()
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    app.run(host=host, port=port, debug=debug)
