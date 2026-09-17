import subprocess
import sys
import time
import re
import requests

# --- НАСТРОЙКИ ---
SERIAL_PORT = "COM12"
MAX_BYTES = 110  # Безопасный лимит байт под один пакет LoRa
OLLAMA_MODEL = "qwen2.5:3b"

def get_weather():
    print("1. Запрос погоды в Москве...")
    try:
        url = "https://wttr.in/Moscow?format=3"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            result = response.text.strip()
            print(f"-> Успешно: {result}")
            return result
        else:
            raise Exception(f"Код ответа {response.status_code}")
    except Exception as e:
        print(f"-> Ошибка погоды: {e}. Используем шаблон.")
        return "Moscow: +21°C"

def optimize_cyrillic_bytes(text):
    """Заменяет кириллические буквы на 1-байтовую латиницу."""
    homoglyphs = {
        'а': 'a', 'А': 'A', 'е': 'e', 'Е': 'E',
        'о': 'o', 'О': 'O', 'р': 'p', 'Р': 'P',
        'с': 'c', 'С': 'C', 'у': 'y', 'У': 'Y',
        'х': 'x', 'Х': 'X', 'К': 'K', 'М': 'M',
        'Т': 'T', 'В': 'B'
    }
    return "".join(homoglyphs.get(char, char) for char in text)

import random

def generate_ai_text(weather_data):
    print(f"2. Local generating via Ollama ({OLLAMA_MODEL})...")
    
    clean_weather = weather_data.replace("Moscow:", "").strip()
    url = "http://localhost:11434/api/generate"
    
    # Набор разных стилей для разнообразия генерации
    examples = [
        "Доброе утро! За окном +18°C, всем продуктивной среды и отличного настроения!",
        "Всем привет в эфире! Погода +18°C, не унываем и держим связи!",
        "Утренний привет чату! На улице +18°C, пусть день пройдет легко и успешно!",
        "С новым днем! Погода +18°C, всем бодрости духа и удачных дел!",
        "Прекрасного утра всем на частоте! Сейчас +18°C, заряжаемся позитивом!"
    ]
    
    # Выбираем случайный пример для ориентира
    selected_example = random.choice(examples)
    
    prompt = (
        f"Ты ведущий утреннего радиоэфира. Напиши ОДНО оригинальное, бодрое утреннее приветствие для чата (до 10-12 слов).\n"
        f"Учти текущую погоду: {clean_weather}.\n"
        f"Ориентир по стилю: \"{selected_example}\"\n"
        f"Напиши ТОЛЬКО текст приветствия, без кавычек:"
    )
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 40,
            "temperature": 0.75,  # Подняли температуру для креативности
            "top_p": 0.9
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            data = response.json()
            clean_text = data.get("response", "").strip()
            
            clean_text = clean_text.strip('"').strip("'").strip("«").strip("»")
            clean_text = clean_text.split('\n')[0]
            clean_text = re.sub(r'[\u4e00-\u9fff]+', '', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            print(f"-> ИИ сгенерировал: {clean_text}")
            return clean_text
        else:
            raise Exception(f"Ollama вернула код {response.status_code}")
            
    except Exception as e:
        print(f"-> Ошибка локального ИИ: {e}.")
        return f"Доброе утро! В Москве {clean_weather}. Отличного дня!"

def split_text_by_punctuation(text, max_bytes):
    """Делит текст по знакам препинания с учетом запаса под нумерацию [1/2]."""
    raw_chunks = re.split(r'([.!?;,]+)', text)
    sentences = []
    
    for i in range(0, len(raw_chunks) - 1, 2):
        sentences.append((raw_chunks[i] + raw_chunks[i+1]).strip())
    if len(raw_chunks) % 2 != 0 and raw_chunks[-1].strip():
        sentences.append(raw_chunks[-1].strip())

    parts = []
    current_part = ""
    effective_max = max_bytes - 7  # Запас под "[1/2] "

    for sentence in sentences:
        test_part = f"{current_part} {sentence}".strip() if current_part else sentence
        if len(test_part.encode('utf-8')) <= effective_max:
            current_part = test_part
        else:
            if current_part:
                parts.append(current_part)
            current_part = sentence
            
    if current_part:
        parts.append(current_part)

    final_parts = []
    for part in parts:
        if len(part.encode('utf-8')) > effective_max:
            words = part.split(' ')
            sub_part = ""
            for word in words:
                test_sub = f"{sub_part} {word}".strip() if sub_part else word
                if len(test_sub.encode('utf-8')) <= effective_max:
                    sub_part = test_sub
                else:
                    if sub_part:
                        final_parts.append(sub_part)
                    sub_part = word
            if sub_part:
                final_parts.append(sub_part)
        else:
            final_parts.append(part)

    return final_parts

def send_payload(text_to_send):
    cmd = [
        sys.executable, "-m", "meshcore_cli",
        "-s", SERIAL_PORT,
        "public", text_to_send
    ]
    # Защита от вечного зависания COM-порта (timeout=15 сек)
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if res.returncode != 0:
        raise Exception(f"CLI Error: {res.stderr.strip()}")

def send_to_lora(text):
    print(f"3. Optimizing and sending in MeshCore via {SERIAL_PORT}...")
    
    orig_bytes = len(text.encode('utf-8'))
    opt_text = optimize_cyrillic_bytes(text)
    opt_bytes = len(opt_text.encode('utf-8'))
    
    print(f"-> Оптимизация текста: {orig_bytes} байт -> {opt_bytes} байт (сэкономлено {orig_bytes - opt_bytes} б.)")

    if opt_bytes <= MAX_BYTES:
        messages = [opt_text]
    else:
        print("-> Text too large. Divide into parts...")
        raw_parts = split_text_by_punctuation(opt_text, MAX_BYTES)
        total_parts = len(raw_parts)
        messages = [f"[{i}/{total_parts}] {part}" for i, part in enumerate(raw_parts, 1)]

    for i, msg in enumerate(messages, 1):
        msg_bytes = len(msg.encode('utf-8'))
        print(f"-> Packet sending {i}/{len(messages)} ({msg_bytes} байт / {len(msg)} симв.): \"{msg}\"")
        try:
            send_payload(msg)
            print(f"   [Пакет {i} send success]")
            if i < len(messages):
                print("-> Пауза 10 секунд...")
                time.sleep(10)
        except subprocess.TimeoutExpired:
            print(f"   [Ошибка: Таймаут отправки пакета {i}. COM-порт не ответил за 15 сек]")
            break
        except Exception as e:
            print(f"   [Ошибка отправки пакета {i}: {e}]")
            break

if __name__ == "__main__":
    print("! Sending Started (PUNCTUATION SPLIT + INDEXING)")
    start_time = time.time()
    
    weather = get_weather()
    ai_message = generate_ai_text(weather)
    send_to_lora(ai_message)
    
    print(f"=== ГОТОВО ЗА {round(time.time() - start_time, 1)} СЕК ===")