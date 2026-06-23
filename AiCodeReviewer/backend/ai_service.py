import requests
import json
import re
from config import AGNES_API_KEY, MODEL, BASE_URL, SYSTEM_PROMPT

def analyze_code(code: str, language: str = "python") -> dict:
    """Отправляет код на анализ в Agnes AI и возвращает структурированный отчёт"""
    
    user_prompt = f"""
    Проанализируй этот код на {language}:

    ```{language}
    {code}
    ```
    Верни ТОЛЬКО JSON без пояснений. Используй структуру из системного промпта.
    """
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    
    url = f"{BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {AGNES_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 2000,
        "temperature": 0.3
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Извлекаем JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    return fallback_response("Ошибка парсинга ответа ИИ")
        else:
            return fallback_response(f"Ошибка API: {response.status_code}")
    except requests.exceptions.Timeout:
        return fallback_response("Превышено время ожидания")
    except requests.exceptions.ConnectionError:
        return fallback_response("Нет соединения с сервером")
    except Exception as e:
        return fallback_response(str(e))

def fallback_response(error: str) -> dict:
    """Возвращает структурированный ответ при ошибке"""
    return {
        "summary": f"❌ {error}",
        "score": 0,
        "issues": [{"severity": "high", "line": None, "message": error, "suggestion": "Попробуйте позже"}],
        "best_practices": ["Проверьте интернет-соединение", "Попробуйте перезапустить приложение"],
        "optimized_code": "",
        "security": []
    }