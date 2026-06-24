import requests
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import AGNES_API_KEY, MODEL, BASE_URL, AI_SYSTEM_PROMPT


def ai_suggest_priority(description: str) -> str:
    """
    Определяет приоритет задачи с помощью Agnes AI.
    Возвращает: "High", "Medium" или "Low"
    """
    try:
        messages = [
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user", "content": description}
        ]
        
        url = f"{BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {AGNES_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": MODEL,
            "messages": messages,
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            priority = result["choices"][0]["message"]["content"].strip()
            if priority in ["High", "Medium", "Low"]:
                return priority
        else:
            print(f"[AI Priority] Ошибка API: {response.status_code}")
            
    except Exception as e:
        print(f"[AI Priority] Ошибка: {e}")
    
    return "Medium"
