# MLVCS — ML Versioning Control System

Система для отслеживания ML-экспериментов, версий моделей и изменений кода.  
Разворачивается локально за 5 минут через Docker.

---

## Что умеет система

- Создавать проекты и эксперименты с параметрами и метриками
- Версионировать код через встроенный Git
- Хранить файлы моделей (`.pkl`, `.pt`, `.h5` и любые другие) в MinIO
- Сравнивать эксперименты и продвигать лучшую модель в production
- Управлять всем через CLI или браузер (Swagger UI)

---

## Что нужно установить

### Обязательно

| Инструмент | Версия | Зачем |
|------------|--------|-------|
| Docker | 20.10+ | Запускает все сервисы |
| Docker Compose | v2.0+ | Управляет контейнерами |
| Git | 2.30+ | Загрузка проекта |
| Python | 3.10+ | Запуск CLI утилиты |

### Проверить что всё установлено

```bash
docker --version
docker compose version
git --version
python3 --version
```

---

## Установка Docker

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Разрешить запуск без sudo
sudo usermod -aG docker $USER
newgrp docker
```

### macOS

Скачать и установить **Docker Desktop**: https://docs.docker.com/desktop/install/mac-install/  
После установки запустить приложение и дождаться статуса Running.

### Windows

1. Включить WSL2 — открыть PowerShell от администратора:
```powershell
wsl --install -d Ubuntu-24.04
```
2. Скачать **Docker Desktop**: https://docs.docker.com/desktop/install/windows-install/  
3. При установке включить опцию **"Use WSL 2 based engine"**
4. Docker Desktop → Settings → WSL Integration → включить Ubuntu
5. Все дальнейшие команды выполнять в терминале Ubuntu

---

## Быстрый старт

### 1. Скачать проект

```bash
git clone https://github.com/YOUR_USERNAME/ml-versioning-system.git
cd ml-versioning-system
```

### 2. Создать файл настроек

```bash
cp .env.example .env
```

Для локального запуска ничего менять не нужно — настройки по умолчанию подходят.

### 3. Запустить систему

```bash
docker compose up -d --build
```

Первый запуск занимает 3–5 минут — Docker скачивает образы PostgreSQL, MinIO и собирает backend.  
Последующие запуски занимают 10–15 секунд.

### 4. Проверить что всё работает

```bash
# Подождать ~30 секунд после запуска
curl http://localhost:8000/health
```

Ожидаемый ответ:
```json
{"status": "healthy"}
```

Проверить статус контейнеров:
```bash
docker compose ps
```

Все три должны быть в статусе `running`:
```
NAME              STATUS
mlvcs_postgres    running
mlvcs_minio       running
mlvcs_backend     running
```

### 5. Открыть в браузере

| Адрес | Что там |
|-------|---------|
| http://localhost:8000/docs | API документация, можно тестировать прямо в браузере |
| http://localhost:9001 | MinIO — веб-интерфейс хранилища моделей |

MinIO логин: `minioadmin` / пароль: `minioadmin123`

---

## Настройка CLI

CLI — это командная строка для работы с системой.

### Создать виртуальное окружение

> На Ubuntu 24 нельзя устанавливать пакеты глобально — нужно виртуальное окружение.  
> На macOS и Windows это тоже хорошая практика.

```bash
cd ~/projects/ml-versioning-system

# Создать окружение
python3 -m venv .venv

# Активировать (Linux / macOS / WSL)
source .venv/bin/activate

# В начале строки появится (.venv) — окружение активно
```

### Установить зависимости

```bash
pip install requests
```

### Настроить короткий алиас

Чтобы не печатать `python3 cli/mlvcs.py` каждый раз:

```bash
# Для Zsh
echo 'alias mlvcs="source ~/projects/ml-versioning-system/.venv/bin/activate && python3 ~/projects/ml-versioning-system/cli/mlvcs.py"' >> ~/.zshrc
source ~/.zshrc

# Для Bash
echo 'alias mlvcs="source ~/projects/ml-versioning-system/.venv/bin/activate && python3 ~/projects/ml-versioning-system/cli/mlvcs.py"' >> ~/.bashrc
source ~/.bashrc
```

Теперь можно писать просто `mlvcs` из любой папки.

### Проверить CLI

```bash
mlvcs health
# ✅ API Status: healthy
```

---

## Первый запуск: создать проект и эксперимент

Это полный пример — от нуля до зарегистрированной модели.

```bash
# 1. Создать проект
mlvcs project create my-first-project --description "Мой первый проект"

# 2. Создать эксперимент с параметрами
mlvcs experiment create baseline \
  --params '{"learning_rate": 0.001, "epochs": 10}' \
  --tags "baseline,v1"

# 3. Отметить что эксперимент запущен
mlvcs experiment update --status running

# 4. Зафиксировать код
echo "# my model" > /tmp/model.py
mlvcs commit --message "Add baseline model" --files /tmp/model.py

# 5. Записать результаты после обучения
mlvcs experiment update \
  --status completed \
  --metrics '{"accuracy": 0.91, "loss": 0.24}'

# 6. Зарегистрировать модель
mlvcs model register my-model --version 1.0.0 --framework sklearn

# 7. Загрузить файл модели
echo '{"weights": [1,2,3]}' > /tmp/model.pkl
mlvcs model upload /tmp/model.pkl

# 8. Продвинуть в production
mlvcs model promote
```

---

## Дальнейшая работа — справочник команд

### Проекты

```bash
mlvcs project create <название>          # создать проект
mlvcs project list                       # список всех проектов
mlvcs project use <название>             # переключиться на проект
```

### Эксперименты

```bash
mlvcs experiment create <название>       # создать эксперимент
mlvcs experiment create <название> \
  --params '{"lr": 0.001}' \             # с параметрами
  --tags "tag1,tag2"                     # с тегами

mlvcs experiment list                    # список экспериментов проекта
mlvcs experiment show                    # детали текущего эксперимента

mlvcs experiment update --status running      # обновить статус
mlvcs experiment update --status completed
mlvcs experiment update --status failed
mlvcs experiment update \
  --metrics '{"accuracy": 0.95}'         # записать метрики
```

### Модели

```bash
mlvcs model register <название> \
  --version 1.0.0 \
  --framework pytorch \
  --metrics '{"accuracy": 0.95}' \
  --params '{"layers": 4}'

mlvcs model upload ./model.pt            # загрузить файл модели
mlvcs model list                         # список версий моделей
mlvcs model promote                      # продвинуть в production
```

### Код и Git

```bash
mlvcs commit --message "Описание" \
  --files train.py config.yaml           # зафиксировать файлы

mlvcs log                                # история коммитов
mlvcs log --limit 10                     # последние 10
mlvcs diff a1b2c3d                       # diff коммита
mlvcs branches                           # список веток
```

---

## Управление системой

```bash
# Запустить
docker compose up -d

# Остановить (данные сохраняются)
docker compose stop

# Запустить снова
docker compose start

# Перезапустить после изменений в коде
docker compose up -d --build backend

# Посмотреть логи
docker compose logs -f backend

# Полный сброс с удалением данных (осторожно!)
docker compose down -v
```

---

## Частые проблемы

### `error: externally-managed-environment`
```bash
# Решение: использовать виртуальное окружение
python3 -m venv .venv && source .venv/bin/activate
pip install requests
```

### API не отвечает
```bash
docker compose ps           # проверить статус контейнеров
docker compose logs backend # посмотреть ошибки
docker compose restart backend
```

### Тесты падают после первого
```bash
# Очистить базу от старых тестовых данных
curl -s http://localhost:8000/api/v1/projects/ | python3 -c "
import sys, json
for p in json.load(sys.stdin): print(p['id'])
" | xargs -I{} curl -s -X DELETE http://localhost:8000/api/v1/projects/{}
```

### `permission denied` при запуске Docker
```bash
sudo usermod -aG docker $USER
newgrp docker
```

---

## Запуск тестов

```bash
# Очистить базу
curl -s http://localhost:8000/api/v1/projects/ | python3 -c "
import sys, json
for p in json.load(sys.stdin): print(p['id'])
" | xargs -I{} curl -s -X DELETE http://localhost:8000/api/v1/projects/{}

# Запустить 13 автоматических тестов
bash tests/test_system.sh
```

Ожидаемый результат: `13 passed, 0 failed`

---

## Структура проекта

```
ml-versioning-system/
├── backend/              # FastAPI сервер
│   ├── app/
│   │   ├── main.py       # точка входа
│   │   ├── models.py     # таблицы базы данных
│   │   ├── schemas.py    # валидация запросов
│   │   ├── routers/      # эндпоинты API
│   │   └── services/     # MinIO и Git логика
│   └── Dockerfile
├── cli/
│   └── mlvcs.py          # CLI утилита
├── tests/
│   └── test_system.sh    # автотесты
├── docker-compose.yml    # конфигурация сервисов
├── .env.example          # шаблон настроек
└── README.md

