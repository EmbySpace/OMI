import subprocess
import sys
import time
import re
import random
import requests
import serial.tools.list_ports

# --- НАСТРОЙКИ ---
MAX_BYTES = 110               # Лимит байт для 1 пакета LoRa
OLLAMA_MODEL = "qwen2.5:1.5b" # Оптимальная модель (отличный русский язык, ~1.1GB RAM)

def find_meshcore_port():
    """
    Автоматически находит COM/TTY порт платы LoRa.
    """
    print("0. Поиск подключенного COM/TTY порта LoRa...")
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        raise Exception("Ни одного COM/TTY порта не найдено!")
        
    for port in ports:
        port_desc = f"{port.device} - {port.description}".lower()
        print(f"   -> Найдено устройство: {port.device} ({port.description})")
        if any(chip in port_desc for chip in ['ch340', 'cp210', 'ftdi', 'usb', 'ttyacm', 'ttyusb', 'serial']):
            print(f"-> Успешно выбран порт: {port.device}")
            return port.device

    selected_port = ports[0].device
    print(f"-> Выбран доступный порт: {selected_port}")
    return selected_port

def get_weather():
    """
    Запрашивает погоду в Москве через wttr.in
    """
    print("1. Запрос погоды в Москве...")
    try:
        url = "https://wttr.in/Moscow?format=3"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            result = response.text.strip()
            print(f"-> Успешно: {result}")
            return result
        else:
            raise Exception(f"Код {response.status_code}")
    except Exception as e:
        print(f"-> Ошибка погоды ({e}). Используем стандартное значение.")
        return "Moscow: +20°C"

def optimize_cyrillic_bytes(text):
    """
    Заменяет визуально совпадающие кириллические буквы на 1-байтовую латиницу.
    Экономит 20-35% размера пакета LoRa.
    """
    homoglyphs = {
        'а': 'a', 'А': 'A', 'е': 'e', 'Е': 'E',
        'о': 'o', 'О': 'O', 'р': 'p', 'Р': 'P',
        'с': 'c', 'С': 'C', 'у': 'y', 'У': 'Y',
        'х': 'x', 'Х': 'X', 'К': 'K', 'М': 'M',
        'Т': 'T', 'В': 'B'
    }
    return "".join(homoglyphs.get(char, char) for char in text)

def generate_ai_text(weather_data):
    """
    Генерирует короткое осмысленное приветствие через qwen2.5:1.5b.
    """
    print(f"2. Генерация текста через Ollama ({OLLAMA_MODEL})...")
    
    # Извлекаем чистое значение температуры (например, "+19°C")
    temp_match = re.search(r'[+-]?\d+°C', weather_data)
    clean_temp = temp_match.group(0) if temp_match else "+19°C"
    
    url = "http://localhost:11434/api/generate"
    
    # Разнообразные роли/стили для генерации
    styles = [
        "энергичное бодрое утреннее приветствие",
        "дружеское сообщение для радиосети",
        "короткое позитивное пожелание отличного дня",
        "лаконичный утренний статус",
        "теплое приветствие с предложением выпить кофе"
    ]
    chosen_style = random.choice(styles)
    
    prompt = (
        f"Напиши {chosen_style}.\n"
        f"Укажи погоду: {clean_temp}.\n"
        f"ТРЕБОВАНИЯ: Строго одно предложение, не больше 8 слов. Никаких вводных фраз."
    )
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 30,
            "temperature": 0.8,
            "top_p": 0.9,
            "presence_penalty": 0.5
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            data = response.json()
            raw_text = data.get("response", "").strip()
            
            # Очистка от лишних кавычек и спецсимволов
            clean_text = raw_text.strip('"').strip("'").strip("«").strip("»")
            clean_text = clean_text.split('\n')[0]
            clean_text = re.sub(r'[^\w\s\d.,!?-]', '', clean_text)  # Удаляем эмодзи
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            # Проверка минимальной длины
            if len(clean_text) < 10:
                raise Exception("Слишком короткий результат")

            print(f"-> ИИ сгенерировал: {clean_text}")
            return clean_text
        else:
            raise Exception(f"Ollama вернула код {response.status_code}")
            
    except Exception as e:
        print(f"-> Ошибка ИИ ({e}). Применен резервный вариант.")
        fallbacks = [
            f"Всем привет! В Москве {clean_temp}, отличного и продуктивного дня!",
            f"С добрым утром! За окном {clean_temp}, хорошего вам настроения!",
            f"Утренний привет! На улице {clean_temp}, пусть день пройдет отлично!"
        ]
        return random.choice(fallbacks)

def split_text_by_punctuation(text, max_bytes):
    """
    Делит длинный текст по предложениям или словам, если он не влезает в 1 пакет.
    """
    raw_chunks = re.split(r'([.!?;,]+)', text)
    sentences = []
    
    for i in range(0, len(raw_chunks) - 1, 2):
        sentences.append((raw_chunks[i] + raw_chunks[i+1]).strip())
    if len(raw_chunks) % 2 != 0 and raw_chunks[-1].strip():
        sentences.append(raw_chunks[-1].strip())

    parts = []
    current_part = ""
    effective_max = max_bytes - 7

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

def send_payload(port, text_to_send):
    """
    Отправляет пакет через MeshCore CLI.
    """
    cmd = [
        sys.executable, "-m", "meshcore_cli",
        "-s", port,
        "public", text_to_send
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if res.returncode != 0:
        raise Exception(f"CLI Error: {res.stderr.strip()}")

def send_to_lora(port, text):
    print(f"3. Оптимизация и отправка в MeshCore via {port}...")
    
    orig_bytes = len(text.encode('utf-8'))
    opt_text = optimize_cyrillic_bytes(text)
    opt_bytes = len(opt_text.encode('utf-8'))
    
    print(f"-> Оптимизация: {orig_bytes} байт -> {opt_bytes} байт (сэкономлено {orig_bytes - opt_bytes} б.)")

    if opt_bytes <= MAX_BYTES:
        messages = [opt_text]
    else:
        print("-> Текст превышает лимит. Делим на части...")
        raw_parts = split_text_by_punctuation(opt_text, MAX_BYTES)
        total_parts = len(raw_parts)
        messages = [f"[{i}/{total_parts}] {part}" for i, part in enumerate(raw_parts, 1)]

    for i, msg in enumerate(messages, 1):
        msg_bytes = len(msg.encode('utf-8'))
        print(f"-> Отправка пакета {i}/{len(messages)} ({msg_bytes} байт / {len(msg)} симв.): \"{msg}\"")
        try:
            send_payload(port, msg)
            print(f"   [Пакет {i} успешно отправлен]")
            if i < len(messages):
                print("-> Пауза 10 секунд перед следующим пакетом...")
                time.sleep(10)
        except subprocess.TimeoutExpired:
            print(f"   [Ошибка: Таймаут. Порт {port} не ответил за 15 сек]")
            break
        except Exception as e:
            print(f"   [Ошибка отправки пакета {i}: {e}]")
            break

if __name__ == "__main__":
    print(f"=== STARTING LORA MESH BOT ({OLLAMA_MODEL.upper()}) ===")
    start_time = time.time()
    
    try:
        serial_port = find_meshcore_port()
        weather = get_weather()
        ai_message = generate_ai_text(weather)
        send_to_lora(serial_port, ai_message)
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
    
    print(f"=== ГОТОВО ЗА {round(time.time() - start_time, 1)} СЕК ===")