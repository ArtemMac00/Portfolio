const API_URL = 'http://0.0.0.0:5000/api';
let currentFilter = 'all';
let charts = {};

function loadTasks(status) {
    if (status) currentFilter = status;
    const url = currentFilter === 'all' ? '/tasks' : `/tasks?status=${currentFilter}`;
    fetch(`${API_URL}${url}`)
        .then(res => res.json())
        .then(tasks => renderTasks(tasks))
        .catch(err => console.error('Ошибка загрузки задач:', err));
}

function searchTasks() {
    const query = document.getElementById('searchInput').value;
    if (!query.trim()) { loadTasks('all'); return; }
    fetch(`${API_URL}/tasks/search?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(tasks => renderTasks(tasks))
        .catch(err => console.error('Ошибка поиска:', err));
}

function renderTasks(tasks) {
    const container = document.getElementById('taskList');
    if (tasks.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:40px;color:#8b949e;">📭 Задач нет</div>';
        return;
    }
    let html = '';
    tasks.forEach(t => {
        const statusMap = { 'InProgress': '🟡 В работе', 'Done': '✅ Выполнено', 'Archived': '📦 Архив' };
        const priorityColors = { 'High': 'priority-high', 'Medium': 'priority-medium', 'Low': 'priority-low' };
        html += `
            <div class="task-item">
                <div class="task-info">
                    <div class="task-title">
                        ${t.title}
                        <span class="task-priority ${priorityColors[t.priority] || 'priority-medium'}">${t.priority}</span>
                        <span class="task-status status-${t.status}">${statusMap[t.status] || t.status}</span>
                    </div>
                    <div class="task-desc">${t.description || 'Нет описания'}</div>
                    <div style="font-size:0.7rem;color:#484f58;">Создано: ${t.created_at.slice(0,10)}</div>
                </div>
                <div class="task-actions">
                    <button onclick="updateTask(${t.id}, 'InProgress')" class="btn btn-secondary" title="В работу">🟡</button>
                    <button onclick="updateTask(${t.id}, 'Done')" class="btn btn-secondary" title="Выполнено">✅</button>
                    <button onclick="updateTask(${t.id}, 'Archived')" class="btn btn-secondary" title="Архив">📦</button>
                    <button onclick="deleteTask(${t.id})" class="btn btn-secondary" title="Удалить">🗑️</button>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

function addTask() {
    const title = document.getElementById('taskTitle').value;
    const description = document.getElementById('taskDesc').value;
    const priority = document.getElementById('taskPriority').value;
    
    if (!title) { alert('Введите название задачи'); return; }
    
    fetch(`${API_URL}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description, priority: priority || undefined })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            document.getElementById('taskTitle').value = '';
            document.getElementById('taskDesc').value = '';
            document.getElementById('taskPriority').value = '';
            loadTasks(currentFilter);
            loadStats();
            if (data.priority) {
                document.getElementById('taskPriority').value = data.priority;
            }
        }
    })
    .catch(err => console.error('Ошибка добавления задачи:', err));
}

function updateTask(id, status) {
    fetch(`${API_URL}/tasks/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
    })
    .then(() => { loadTasks(currentFilter); loadStats(); })
    .catch(err => console.error('Ошибка обновления статуса:', err));
}

function deleteTask(id) {
    if (!confirm('Удалить задачу?')) return;
    fetch(`${API_URL}/tasks/${id}`, {
        method: 'DELETE'
    })
    .then(() => { loadTasks(currentFilter); loadStats(); })
    .catch(err => console.error('Ошибка удаления задачи:', err));
}

function loadStats() {
    fetch(`${API_URL}/stats`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('totalTasks').textContent = data.stats.total;
            document.getElementById('inProgressTasks').textContent = data.stats.in_progress;
            document.getElementById('doneTasks').textContent = data.stats.done;
            document.getElementById('overdueTasks').textContent = data.overdue_count;
            document.getElementById('avgTime').textContent = data.avg_completion_days + ' дн';
            updateCharts(data);
        })
        .catch(err => console.error('Ошибка загрузки статистики:', err));
}

function updateCharts(data) {
    const ctx1 = document.getElementById('priorityChart').getContext('2d');
    if (charts.priority) charts.priority.destroy();
    charts.priority = new Chart(ctx1, {
        type: 'doughnut',
        data: {
            labels: ['High', 'Medium', 'Low'],
            datasets: [{
                data: [
                    data.priority_distribution.High || 0,
                    data.priority_distribution.Medium || 0,
                    data.priority_distribution.Low || 0
                ],
                backgroundColor: ['#f85149', '#d29922', '#3fb950']
            }]
        },
        options: { 
            responsive: true, 
            plugins: { 
                legend: { 
                    labels: { color: '#c9d1d9' } 
                } 
            }
        }
    });
    
    const ctx2 = document.getElementById('timelineChart').getContext('2d');
    if (charts.timeline) charts.timeline.destroy();
    const dates = [...new Set(data.timeline.map(t => t.date))];
    const statuses = ['InProgress', 'Done', 'Archived'];
    const colors = { 'InProgress': '#d29922', 'Done': '#3fb950', 'Archived': '#484f58' };
    const datasets = statuses.map(status => ({
        label: status,
        data: dates.map(d => {
            const item = data.timeline.find(t => t.date === d && t.status === status);
            return item ? item.count : 0;
        }),
        borderColor: colors[status],
        backgroundColor: colors[status] + '33',
        tension: 0.3,
        fill: true
    }));
    charts.timeline = new Chart(ctx2, {
        type: 'line',
        data: { labels: dates, datasets },
        options: {
            responsive: true,
            plugins: { legend: { labels: { color: '#c9d1d9' } } },
            scales: {
                x: { ticks: { color: '#8b949e' }, grid: { color: '#30363d' } },
                y: { ticks: { color: '#8b949e', stepSize: 1 }, grid: { color: '#30363d' } }
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    loadTasks('all');
    loadStats();
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.id === 'taskTitle') addTask();
});
