const API_URL = 'http://localhost:8000/analyze';
let history = JSON.parse(localStorage.getItem('codeReviewHistory')) || [];
let currentResult = null;

// ===== Drag & Drop =====
const dropZone = document.getElementById('dropZone');
const dropOverlay = document.getElementById('dropOverlay');

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        readFile(files[0]);
    }
});

function readFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('codeInput').value = e.target.result;
        const ext = file.name.split('.').pop().toLowerCase();
        const langMap = { py: 'python', cs: 'csharp', js: 'javascript', java: 'java' };
        if (langMap[ext]) {
            document.getElementById('language').value = langMap[ext];
        }
    };
    reader.readAsText(file);
}

function loadFile(event) {
    const file = event.target.files[0];
    if (file) readFile(file);
    event.target.value = '';
}

// ===== Основной анализ =====
async function analyzeCode() {
    const code = document.getElementById('codeInput').value;
    const language = document.getElementById('language').value;
    const btn = document.getElementById('analyzeBtn');
    const output = document.getElementById('resultContent');
    const scoreSpan = document.getElementById('resultScore');
    const statusSpan = document.getElementById('resultStatus');
    const timeSpan = document.getElementById('resultTime');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');

    if (!code.trim() || code.trim().length < 5) {
        output.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">❌</div>
                <p>Код слишком короткий или пустой</p>
                <small>Минимум 5 символов</small>
            </div>
        `;
        return;
    }

    btn.disabled = true;
    btn.textContent = '⏳ Анализ...';
    statusSpan.textContent = 'Анализ...';
    statusSpan.className = 'status loading';
    progressContainer.style.display = 'block';
    progressBar.style.width = '0%';
    progressText.textContent = '⏳ Отправка запроса...';

    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += Math.random() * 8;
        if (progress > 95) progress = 95;
        progressBar.style.width = progress + '%';
    }, 200);

    const startTime = Date.now();

    try {
        progressText.textContent = '🧠 Нейросеть анализирует код...';

        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, language })
        });

        clearInterval(progressInterval);
        progressBar.style.width = '100%';

        if (!response.ok) {
            throw new Error(`Ошибка сервера: ${response.status}`);
        }

        const data = await response.json();
        currentResult = data;

        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        timeSpan.textContent = `⏱️ ${elapsed}с`;

        saveToHistory(code, language, data);
        renderResult(data, output, scoreSpan, statusSpan);

    } catch (error) {
        clearInterval(progressInterval);
        output.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">❌</div>
                <p>Ошибка: ${error.message}</p>
                <small>Проверьте, запущен ли сервер (python app.py)</small>
            </div>
        `;
        statusSpan.textContent = 'Ошибка';
        statusSpan.className = 'status error';
        timeSpan.textContent = '';
    }

    setTimeout(() => {
        progressContainer.style.display = 'none';
        progressBar.style.width = '0%';
    }, 500);

    btn.disabled = false;
    btn.textContent = '🔍 Анализировать';
}

// ===== Рендер результата =====
function renderResult(data, output, scoreSpan, statusSpan) {
    const score = data.score || 0;
    const isGood = score >= 7;
    const isExcellent = score >= 9;

    scoreSpan.textContent = `Оценка: ${score}/10`;
    scoreSpan.style.color = isExcellent ? '#3fb950' : isGood ? '#d29922' : '#f85149';

    statusSpan.textContent = isExcellent ? '⭐ Отлично' : isGood ? '✅ Хорошо' : '⚠️ Требует внимания';
    statusSpan.className = `status ${isExcellent ? 'success' : isGood ? 'warning' : 'error'}`;

    let html = '';

    if (data.summary) {
        html += `<p style="font-weight:600;font-size:1.1rem;margin-bottom:12px;">📋 ${data.summary}</p>`;
    }

    if (data.issues && data.issues.length > 0) {
        const criticalCount = data.issues.filter(i => i.severity === 'critical').length;
        const highCount = data.issues.filter(i => i.severity === 'high').length;
        html += `<h3>🔴 Найдены проблемы (${data.issues.length})</h3>`;
        if (criticalCount > 0) {
            html += `<span style="color:#f85149;">❗ ${criticalCount} критических</span> `;
        }
        if (highCount > 0) {
            html += `<span style="color:#d29922;">⚠️ ${highCount} высоких</span>`;
        }
        html += '<br><br>';

        data.issues.forEach(issue => {
            const severity = issue.severity || 'medium';
            const lineText = issue.line ? ` (строка ${issue.line})` : '';
            html += `
                <div class="issue ${severity}">
                    <div class="issue-severity">[${severity.toUpperCase()}]${lineText}</div>
                    <div class="issue-message">${issue.message}</div>
                    <div class="issue-suggestion">💡 ${issue.suggestion || 'Нет предложения'}</div>
                </div>
            `;
        });
    } else {
        html += `<p style="color:#3fb950;font-size:1.1rem;margin:12px 0;">✅ Код чистый! Проблем не обнаружено.</p>`;
    }

    if (data.best_practices && data.best_practices.length > 0) {
        html += `<h3>💡 Рекомендации</h3><ul>`;
        data.best_practices.forEach(p => {
            html += `<li>${p}</li>`;
        });
        html += `</ul>`;
    }

    if (data.security && data.security.length > 0) {
        html += `<h3>🔒 Безопасность</h3><ul>`;
        data.security.forEach(s => {
            html += `<li style="color:#f85149;">${s}</li>`;
        });
        html += `</ul>`;
    }

    if (data.optimized_code && data.optimized_code.trim()) {
        html += `<h3>✅ Оптимизированный код</h3>`;
        html += `<pre><code class="language-python">${escapeHtml(data.optimized_code)}</code></pre>`;
    }

    output.innerHTML = html;

    if (window.hljs) {
        document.querySelectorAll('.result-content pre code').forEach(block => {
            hljs.highlightElement(block);
        });
    }
}

// ===== История =====
function saveToHistory(code, language, data) {
    const entry = {
        id: Date.now(),
        date: new Date().toISOString(),
        language: language,
        preview: code.slice(0, 80) + (code.length > 80 ? '...' : ''),
        score: data.score || 0,
        summary: data.summary || 'Нет данных',
        code: code,
        result: data
    };
    history.unshift(entry);
    if (history.length > 50) history.pop();
    localStorage.setItem('codeReviewHistory', JSON.stringify(history));
}

function toggleHistory() {
    const section = document.getElementById('historySection');
    if (section.style.display === 'none') {
        section.style.display = 'block';
        renderHistory();
        document.getElementById('historyToggle').textContent = '📜 Скрыть';
    } else {
        section.style.display = 'none';
        document.getElementById('historyToggle').textContent = '📜 История';
    }
}

function renderHistory() {
    const container = document.getElementById('historyList');
    if (history.length === 0) {
        container.innerHTML = '<div class="empty-history">История пуста</div>';
        return;
    }
    let html = '';
    history.forEach(item => {
        const date = new Date(item.date);
        const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
        const langMap = { python: '🐍', csharp: '#️⃣', javascript: '⬡', java: '☕' };
        const icon = langMap[item.language] || '📄';
        const scoreColor = item.score >= 7 ? '#3fb950' : item.score >= 4 ? '#d29922' : '#f85149';
        html += `
            <div class="history-item" onclick="loadHistory(${item.id})">
                <span class="lang">${icon} ${item.language}</span>
                <span class="preview">${escapeHtml(item.preview)}</span>
                <span class="h-score" style="color:${scoreColor}">${item.score}/10</span>
                <span class="h-date">${dateStr}</span>
            </div>
        `;
    });
    container.innerHTML = html;
}

function loadHistory(id) {
    const item = history.find(h => h.id === id);
    if (!item) return;
    
    document.getElementById('codeInput').value = item.code;
    document.getElementById('language').value = item.language;
    
    const output = document.getElementById('resultContent');
    const scoreSpan = document.getElementById('resultScore');
    const statusSpan = document.getElementById('resultStatus');
    const timeSpan = document.getElementById('resultTime');
    
    renderResult(item.result, output, scoreSpan, statusSpan);
    timeSpan.textContent = `📅 ${new Date(item.date).toLocaleDateString()}`;
    
    document.getElementById('historySection').style.display = 'none';
    document.getElementById('historyToggle').textContent = '📜 История';
    
    document.querySelector('.output-section').scrollIntoView({ behavior: 'smooth' });
}

// ===== Вспомогательные функции =====
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function clearCode() {
    document.getElementById('codeInput').value = '';
    document.getElementById('resultContent').innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">🧠</div>
            <p>Вставьте код и нажмите «Анализировать»</p>
            <small>ИИ найдёт ошибки и предложит оптимизации</small>
        </div>
    `;
    document.getElementById('resultScore').textContent = 'Оценка: —';
    document.getElementById('resultStatus').textContent = 'Ожидание';
    document.getElementById('resultStatus').className = 'status';
    document.getElementById('resultTime').textContent = '';
}

function clearAll() {
    if (!confirm('Очистить всё: код, историю и результаты?')) return;
    localStorage.removeItem('codeReviewHistory');
    history = [];
    document.getElementById('historyList').innerHTML = '<div class="empty-history">История пуста</div>';
    if (document.getElementById('historySection').style.display !== 'none') {
        renderHistory();
    }
    clearCode();
}

function copyResult() {
    const content = document.getElementById('resultContent');
    const text = content.textContent || content.innerText;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.querySelector('.btn-icon');
        const original = btn.textContent;
        btn.textContent = '✅';
        setTimeout(() => { btn.textContent = original; }, 1500);
    }).catch(() => {
        alert('Не удалось скопировать');
    });
}

// ===== Горячие клавиши =====
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        analyzeCode();
    }
});

// ===== Загрузка истории при старте =====
document.addEventListener('DOMContentLoaded', () => {
    if (history.length > 0) {
        renderHistory();
    }
});