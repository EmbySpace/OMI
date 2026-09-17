```markdown
# OMI — Open Mesh Informator

Open Mesh Informator (OMI) — автономный сервис генерации и рассылки ИИ-сводок погоды в радиосетях LoRa (MeshCore / Meshtastic).

Скрипт запрашивает данные о погоде, формирует короткое эфирное приветствие через локальную Ollama (Qwen2.5:3b), оптимизирует байтовый размер сообщения, режет текст под размер пакета LoRa и отправляет его через MeshCore CLI.

## Возможности

* Оптимизация кириллицы (Cyrillic Homoglyphs): заменяет совпадающие символы кириллицы на 1-байтовую латиницу, экономя до 15-20% байт в UTF-8.
* Сплиттер по пунктуации: делит длинный текст по предложениям с добавлением индексов пагинации ([1/2], [2/2]) и паузой в 10 секунд между пакетами.
* Фильтрация вывода: удаляет из ответа LLM иероглифы, переносы строк и лишние кавычки.
* Защита COM-порта: вызовы CLI ограничены таймаутом в 15 секунд.
* Offline-режим: при отсутствии сети wttr.in используется локальный фолбэк-шаблон.

## Архитектура


```

[wttr.in] ------> [OMI Engine] --------> [Ollama Qwen2.5:3b]
|                          |
v                          v
[MeshCore CLI] <------- [Homoglyph Opt & Splitter]
|
v
[Serial Port] ---> [LoRa Radio] ---> Mesh Network

```

## Установка и запуск

1. Установите зависимости:
   ```bash
   pip install requests meshcore-cli

```

2. Подготовьте Ollama:
```bash
ollama pull qwen2.5:3b

```


3. Настройте параметры в `main_qwen2.5-3b.py`:
```python
SERIAL_PORT = "COM12"  # /dev/ttyACM0 для Linux
MAX_BYTES = 110
OLLAMA_MODEL = "qwen2.5:3b"

```


4. Запустите:
```bash
python main_qwen2.5-3b.py

```



## Лицензия

MIT

```

<ElicitationsGroup message="Что дальше для настройки репозитория?">
  <Elicitation label="Создать файл LICENSE" query="Напиши стандартный текст файла LICENSE (MIT) для проекта OMI."/>
  <Elicitation label="Создать файл requirements.txt" query="Сделай файл requirements.txt для проекта OMI."/>
</ElicitationsGroup>

```
