# MLVCS — ML Versioning Control System

> Инфокоммуникационная система управления версиями кода и состояний ML-моделей, обеспечивающая удобное управление экспериментами и воспроизводимость ML-исследований.

---

## Содержание

1. [Что такое MLVCS и зачем он нужен](#что-такое-mlvcs)
2. [Архитектура системы](#архитектура-системы)
3. [Требования](#требования)
4. [Установка и развёртывание](#установка-и-развёртывание)
   - [Ubuntu / Debian](#ubuntu--debian)
   - [macOS](#macos)
   - [Windows (WSL2)](#windows-wsl2)
5. [Настройка окружения для CLI](#настройка-виртуального-окружения-для-cli)
6. [Структура проекта](#структура-проекта)
7. [Полный справочник команд CLI](#полный-справочник-команд-cli)
8. [REST API — список эндпоинтов](#rest-api--список-эндпоинтов)
9. [Типичный рабочий процесс MLOps-инженера](#типичный-рабочий-процесс-mlops-инженера)
10. [Управление данными и обслуживание](#управление-данными-и-обслуживание)
11. [Загрузка на GitHub и перенос на другой компьютер](#загрузка-на-github-и-перенос-на-другой-компьютер)
12. [Частые проблемы и их решения](#частые-проблемы-и-их-решения)

---

## Что такое MLVCS

MLVCS решает ключевую проблему ML-разработки: **воспроизводимость экспериментов**. Когда вы обучаете модели, со временем становится невозможно вспомнить, какой код, какие гиперпараметры и какие данные дали конкретный результат.

MLVCS позволяет:

- **Версионировать код** — каждое изменение фиксируется в Git с историей, ветками и diff
- **Отслеживать эксперименты** — параметры, метрики, статус каждого запуска
- **Хранить артефакты моделей** — файлы `.pkl`, `.pt`, `.h5` и любые другие в объектном хранилище MinIO
- **Сравнивать результаты** — несколько экспериментов в рамках одного проекта
- **Продвигать модели в production** — явное управление production-версией
- **Воспроизводить любой эксперимент** — по commit hash восстановить точное состояние кода

---

## Архитектура системы

```
┌─────────────────────────────────────────────────────────┐
│                     Клиентский уровень                   │
│   CLI (mlvcs.py)          Swagger UI / браузер           │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP REST API
┌──────────────────────────▼──────────────────────────────┐
│              Backend: FastAPI + Uvicorn                   │
│  /projects  /experiments  /models  /commits              │
└──────┬──────────────┬───────────────┬───────────────────┘
       │              │               │
┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│ PostgreSQL  │ │   MinIO    │ │    Git     │
│  метаданные │ │ артефакты  │ │   репо     │
│  проектов   │ │  моделей   │ │  (внутри   │
│ экспериментов│ │ .pkl .pt   │ │ контейнера)│
└─────────────┘ └────────────┘ └────────────┘
```

**Стек технологий:**

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| Backend | Python 3.11 + FastAPI | REST API сервер |
| Сервер | Uvicorn | ASGI сервер |
| База данных | PostgreSQL 15 | Хранение метаданных |
| Хранилище | MinIO | Хранение файлов моделей |
| VCS | GitPython | Встроенный git внутри системы |
| CLI | Python + requests | Командная строка |
| Инфраструктура | Docker + docker-compose | Контейнеризация |

---

## Требования

### Для всех платформ
- **Docker** версии 20.10 или новее
- **Docker Compose** версии 2.0 или новее (команда `docker compose`, не `docker-compose`)
- **Git** версии 2.30 или новее
- **Python** версии 3.10 или новее
- 2 ГБ свободного места на диске
- 1 ГБ оперативной памяти

### Проверка перед установкой
```bash
docker --version          # Docker version 24.x.x
docker compose version    # Docker Compose version v2.x.x
git --version             # git version 2.x.x
python3 --version         # Python 3.10+
```

---

## Установка и развёртывание

### Ubuntu / Debian

#### 1. Установка Docker

```bash
# Обновить пакеты
sudo apt update && sudo apt upgrade -y

# Установить зависимости
sudo apt install -y ca-certificates curl gnupg lsb-release

# Добавить официальный репозиторий Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установить Docker и Compose
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Добавить себя в группу docker (чтобы не писать sudo каждый раз)
sudo usermod -aG docker $USER

# ВАЖНО: применить изменения группы без перезагрузки
newgrp docker

# Проверить
docker run hello-world
```

#### 2. Установка Python и pip

```bash
sudo apt install -y python3 python3-pip python3-venv git
```

#### 3. Клонировать проект

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/YOUR_USERNAME/ml-versioning-system.git
cd ml-versioning-system
```

#### 4. Создать файл окружения

```bash
cp .env.example .env
# При необходимости отредактировать
nano .env
```

#### 5. Запустить систему

```bash
docker compose up -d --build
```

#### 6. Проверить что всё запустилось

```bash
# Подождать ~30 секунд и проверить
sleep 30
curl http://localhost:8000/health
# Ожидаемый ответ: {"status":"healthy"}

# Проверить статус контейнеров
docker compose ps
# Все три должны быть в статусе "running"
```

---

### macOS

#### 1. Установить Docker Desktop

Скачай с официального сайта: https://docs.docker.com/desktop/install/mac-install/

Выбери версию под свою архитектуру:
- **Apple Silicon (M1/M2/M3):** Docker Desktop for Mac with Apple Silicon
- **Intel:** Docker Desktop for Mac with Intel chip

После установки запусти Docker Desktop и дождись когда статус станет "Running" (иконка в меню баре).

#### 2. Установить Homebrew и Python

```bash
# Homebrew (если не установлен)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python и Git
brew install python3 git
```

#### 3. Клонировать и запустить

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/YOUR_USERNAME/ml-versioning-system.git
cd ml-versioning-system
cp .env.example .env
docker compose up -d --build
sleep 30
curl http://localhost:8000/health
```

---

### Windows (WSL2)

#### 1. Включить WSL2

Открой **PowerShell от имени администратора:**

```powershell
# Установить WSL2 с Ubuntu
wsl --install -d Ubuntu-24.04

# Перезагрузить компьютер
Restart-Computer
```

После перезагрузки откроется терминал Ubuntu — создай пользователя и пароль.

#### 2. Установить Docker Desktop для Windows

Скачай с: https://docs.docker.com/desktop/install/windows-install/

При установке убедись что включена опция **"Use WSL 2 based engine"**.

После установки: Docker Desktop → Settings → Resources → WSL Integration → включи свой дистрибутив Ubuntu.

#### 3. Дальнейшие шаги — выполнять в терминале Ubuntu (WSL2)

```bash
# Открыть Ubuntu терминал (из меню Пуск или через Windows Terminal)
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

mkdir -p ~/projects
cd ~/projects
git clone https://github.com/YOUR_USERNAME/ml-versioning-system.git
cd ml-versioning-system
cp .env.example .env
docker compose up -d --build
sleep 30
curl http://localhost:8000/health
```

> **Примечание для Windows:** API будет доступен на `http://localhost:8000` в браузере Windows.

---

## Настройка виртуального окружения для CLI

На Ubuntu 24 и современных системах **нельзя** устанавливать Python-пакеты глобально — система защищена. Нужно виртуальное окружение.

### Создать и активировать окружение

```bash
cd ~/projects/ml-versioning-system

# Создать окружение (.venv — скрытая папка в корне проекта)
python3 -m venv .venv

# Активировать:
# Linux / macOS / WSL2:
source .venv/bin/activate

# В терминале появится префикс (.venv) — окружение активно
```

### Установить зависимости CLI

```bash
# Убедиться что окружение активно (должен быть префикс (.venv))
pip install requests
```

### Настроить алиас для удобства (Linux/macOS/WSL2 с Zsh)

```bash
# Добавить алиас в ~/.zshrc
echo 'alias mlvcs="source ~/projects/ml-versioning-system/.venv/bin/activate && python3 ~/projects/ml-versioning-system/cli/mlvcs.py"' >> ~/.zshrc
source ~/.zshrc

# Теперь из любой папки можно писать просто:
mlvcs health
mlvcs project list
```

Для Bash (`~/.bashrc`):
```bash
echo 'alias mlvcs="source ~/projects/ml-versioning-system/.venv/bin/activate && python3 ~/projects/ml-versioning-system/cli/mlvcs.py"' >> ~/.bashrc
source ~/.bashrc
```

### Деактивировать окружение

```bash
deactivate
```

### Важно: активировать при каждом новом терминале

```bash
# Каждый раз при открытии нового терминала:
source ~/projects/ml-versioning-system/.venv/bin/activate
```

---

## Структура проекта

```
ml-versioning-system/
│
├── backend/                        # FastAPI приложение
│   ├── Dockerfile                  # Образ для backend
│   ├── requirements.txt            # Python зависимости backend
│   └── app/
│       ├── __init__.py
│       ├── main.py                 # Точка входа FastAPI, подключение роутеров
│       ├── config.py               # Настройки из переменных окружения
│       ├── database.py             # Подключение к PostgreSQL (async SQLAlchemy)
│       ├── models.py               # ORM модели таблиц БД
│       ├── schemas.py              # Pydantic схемы для валидации запросов/ответов
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── projects.py         # CRUD для проектов
│       │   ├── experiments.py      # CRUD для экспериментов
│       │   ├── models.py           # Версии моделей + загрузка/скачивание
│       │   └── commits.py          # Git операции: коммиты, история, diff
│       └── services/
│           ├── __init__.py
│           ├── minio_service.py    # Работа с MinIO: upload/download артефактов
│           └── git_service.py      # Git операции через GitPython
│
├── cli/
│   ├── mlvcs.py                    # CLI утилита (все команды)
│   └── requirements.txt            # requests
│
├── tests/
│   └── test_system.sh              # Автоматический тест всей системы (13 тестов)
│
├── docker-compose.yml              # Описание всех сервисов
├── .env.example                    # Шаблон переменных окружения
├── .env                            # Реальные переменные (НЕ в git!)
├── .gitignore                      # Исключения для git
└── README.md                       # Этот файл
```

---

## Полный справочник команд CLI

### Предварительные условия

```bash
# Перейти в папку проекта
cd ~/projects/ml-versioning-system

# Активировать виртуальное окружение
source .venv/bin/activate
```

Все примеры ниже предполагают что алиас `mlvcs` настроен. Если нет — заменяй `mlvcs` на `python3 cli/mlvcs.py`.

---

### config — настройка CLI

```bash
# Посмотреть текущий URL API
mlvcs config

# Изменить URL API (например для удалённого сервера)
mlvcs config --api-url http://192.168.1.100:8000
```

---

### health — проверка соединения

```bash
mlvcs health
# Ответ: ✅ API Status: healthy
```

---

### project — управление проектами

```bash
# Создать новый проект
mlvcs project create <название>
mlvcs project create sentiment-analysis
mlvcs project create bert-classifier --description "Классификация текстов BERT"

# Список всех проектов
mlvcs project list

# Переключиться на другой проект (сделать его текущим)
mlvcs project use <название-или-id>
mlvcs project use sentiment-analysis
mlvcs project use 47ac300a-316b-47d2-95f0-848eb0691b92
```

> Текущий проект сохраняется в `~/.mlvcs_config.json` и используется всеми последующими командами.

---

### experiment — управление экспериментами

```bash
# Создать новый эксперимент в текущем проекте
mlvcs experiment create <название>
mlvcs experiment create baseline-model
mlvcs experiment create bert-v2 --description "Улучшенный BERT с dropout"

# С параметрами (JSON строка)
mlvcs experiment create cnn-experiment \
  --params '{"learning_rate": 0.001, "epochs": 10, "batch_size": 32}'

# С тегами (через запятую)
mlvcs experiment create resnet-50 \
  --tags "resnet,imagenet,production-candidate"

# С привязкой к git commit
mlvcs experiment create model-v3 \
  --commit a1b2c3d4e5f6

# Полный вариант
mlvcs experiment create bert-large \
  --description "BERT Large с fine-tuning" \
  --params '{"lr": 0.00002, "epochs": 5, "warmup_steps": 500}' \
  --tags "bert,large,nlp" \
  --commit abc123

# Список экспериментов текущего проекта
mlvcs experiment list

# Обновить статус эксперимента
mlvcs experiment update --status running
mlvcs experiment update --status completed
mlvcs experiment update --status failed

# Обновить метрики
mlvcs experiment update --metrics '{"accuracy": 0.934, "f1": 0.931, "loss": 0.198}'

# Обновить сразу статус и метрики
mlvcs experiment update \
  --status completed \
  --metrics '{"accuracy": 0.982, "precision": 0.971, "recall": 0.988, "f1": 0.979}'

# Посмотреть детали текущего эксперимента
mlvcs experiment show
```

**Возможные статусы:** `created` → `running` → `completed` / `failed`

---

### model — управление версиями моделей

```bash
# Зарегистрировать версию модели (привязывается к текущему эксперименту)
mlvcs model register <название>
mlvcs model register my-classifier

# С указанием версии и фреймворка
mlvcs model register bert-sentiment \
  --version 1.0.0 \
  --framework pytorch

# С метриками и параметрами
mlvcs model register resnet-50 \
  --version 2.1.0 \
  --framework tensorflow \
  --metrics '{"accuracy": 0.956, "val_accuracy": 0.941}' \
  --params '{"depth": 50, "input_size": 224}' \
  --tags "resnet,cv,imagenet"

# С привязкой к git commit
mlvcs model register final-model \
  --version 3.0.0 \
  --framework sklearn \
  --commit abc123def456

# Загрузить файл модели в MinIO
mlvcs model upload ./model.pkl
mlvcs model upload ./weights.pt
mlvcs model upload ./saved_model.h5
mlvcs model upload ./model.onnx

# Список версий моделей текущего эксперимента
mlvcs model list

# Продвинуть модель в production
# (снимает флаг production со всех остальных версий)
mlvcs model promote
```

---

### commit — управление версиями кода

```bash
# Зафиксировать файлы в git
mlvcs commit --message "Описание изменений"

# С указанием автора и ветки
mlvcs commit \
  --message "Add transformer architecture" \
  --author "Ivan Petrov" \
  --branch "feature/transformer"

# С прикреплением файлов (файлы сохраняются в git репо проекта)
mlvcs commit \
  --message "Initial model architecture" \
  --files train.py model.py config.yaml

# Несколько файлов из разных мест
mlvcs commit \
  --message "Update preprocessing pipeline" \
  --author "Maria Ivanova" \
  --files ./src/preprocess.py ./configs/data.yaml ./requirements.txt

# История коммитов текущего проекта
mlvcs log
mlvcs log --limit 5
mlvcs log --limit 50

# Показать diff конкретного коммита
mlvcs diff a1b2c3d
mlvcs diff a1b2c3d4e5f6789012345678901234567890abcd

# Список веток проекта
mlvcs branches
```

---

## REST API — список эндпоинтов

Полная интерактивная документация: **http://localhost:8000/docs**

### Проекты

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/v1/projects/` | Создать проект |
| GET | `/api/v1/projects/` | Список всех проектов |
| GET | `/api/v1/projects/{id}` | Получить проект по ID |
| PATCH | `/api/v1/projects/{id}` | Обновить описание |
| DELETE | `/api/v1/projects/{id}` | Удалить проект |

### Эксперименты

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/v1/projects/{id}/experiments` | Создать эксперимент |
| GET | `/api/v1/projects/{id}/experiments` | Список экспериментов |
| GET | `/api/v1/projects/{id}/experiments/{eid}` | Получить эксперимент |
| PATCH | `/api/v1/projects/{id}/experiments/{eid}` | Обновить метрики/статус |
| DELETE | `/api/v1/projects/{id}/experiments/{eid}` | Удалить эксперимент |

### Модели

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/v1/experiments/{id}/models` | Зарегистрировать версию |
| GET | `/api/v1/experiments/{id}/models` | Список версий |
| POST | `/api/v1/experiments/{id}/models/{mid}/upload` | Загрузить артефакт |
| GET | `/api/v1/experiments/{id}/models/{mid}/download` | Скачать артефакт |
| GET | `/api/v1/experiments/{id}/models/{mid}/url` | Получить ссылку (1 час) |
| PATCH | `/api/v1/experiments/{id}/models/{mid}/promote` | Продвинуть в production |
| DELETE | `/api/v1/experiments/{id}/models/{mid}` | Удалить версию |

### Git / Коммиты

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/v1/projects/{id}/commits` | Создать коммит с файлами |
| GET | `/api/v1/projects/{id}/commits` | Список коммитов из БД |
| GET | `/api/v1/projects/{id}/history` | Git история (из репо) |
| GET | `/api/v1/projects/{id}/commits/{hash}/diff` | Diff коммита |
| GET | `/api/v1/projects/{id}/branches` | Список веток |
| GET | `/api/v1/projects/{id}/file?file_path=X` | Содержимое файла |

---

## Типичный рабочий процесс MLOps-инженера

Ниже — полный сценарий от создания проекта до продвижения модели в production. Это именно та последовательность действий, которую выполняет инженер в реальной работе.

---

### Этап 0 — Подготовка (один раз)

```bash
# Перейти в папку и активировать окружение
cd ~/projects/ml-versioning-system
source .venv/bin/activate

# Убедиться что система запущена
mlvcs health
# ✅ API Status: healthy

# Если не запущена:
docker compose up -d
sleep 20
mlvcs health
```

---

### Этап 1 — Начало нового ML-проекта

```bash
# Создать проект под новую задачу
mlvcs project create fraud-detection \
  --description "Обнаружение мошеннических транзакций"

# Вывод: ✅ Project created: fraud-detection (id: abc-123...)
#         📌 Set as current project

# Убедиться что проект создан
mlvcs project list
```

---

### Этап 2 — Первый эксперимент (baseline)

```bash
# Создать эксперимент — всегда начинаем с baseline
mlvcs experiment create logistic-regression-baseline \
  --description "Простая логистическая регрессия как точка отсчёта" \
  --params '{
    "model": "LogisticRegression",
    "C": 1.0,
    "max_iter": 100,
    "solver": "lbfgs",
    "train_size": 0.8
  }' \
  --tags "baseline,sklearn,lr"

# Отметить что эксперимент начат
mlvcs experiment update --status running

# Написать код и зафиксировать его
cat > /tmp/baseline.py << 'EOF'
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

def build_model():
    return Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', LogisticRegression(C=1.0, max_iter=100))
    ])

def train(X_train, y_train):
    model = build_model()
    model.fit(X_train, y_train)
    return model
EOF

cat > /tmp/config_baseline.yaml << 'EOF'
model: LogisticRegression
C: 1.0
max_iter: 100
train_size: 0.8
random_state: 42
EOF

mlvcs commit \
  --message "Add logistic regression baseline" \
  --author "Ivan Petrov" \
  --branch "main" \
  --files /tmp/baseline.py /tmp/config_baseline.yaml

# После обучения — записать метрики
mlvcs experiment update \
  --status completed \
  --metrics '{
    "accuracy": 0.823,
    "precision": 0.801,
    "recall": 0.756,
    "f1": 0.778,
    "roc_auc": 0.871,
    "train_time_sec": 12
  }'

# Зарегистрировать модель
mlvcs model register fraud-lr-baseline \
  --version 1.0.0 \
  --framework sklearn \
  --metrics '{"accuracy": 0.823, "f1": 0.778, "roc_auc": 0.871}' \
  --params '{"C": 1.0, "max_iter": 100}'

# Сохранить файл модели
# (в реальности: import joblib; joblib.dump(model, 'model.pkl'))
echo '{"model": "LogisticRegression", "accuracy": 0.823}' > /tmp/lr_baseline.pkl
mlvcs model upload /tmp/lr_baseline.pkl

# Проверить что всё записалось
mlvcs experiment show
```

---

### Этап 3 — Второй эксперимент (улучшение)

```bash
# Создать второй эксперимент на основе анализа baseline
mlvcs experiment create gradient-boosting-v1 \
  --description "XGBoost с feature engineering" \
  --params '{
    "model": "XGBClassifier",
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "train_size": 0.8
  }' \
  --tags "xgboost,boosting,feature-engineering"

mlvcs experiment update --status running

cat > /tmp/xgb_model.py << 'EOF'
import xgboost as xgb
from sklearn.pipeline import Pipeline
from feature_engineering import build_features

def build_model(params):
    return xgb.XGBClassifier(
        n_estimators=params['n_estimators'],
        max_depth=params['max_depth'],
        learning_rate=params['learning_rate'],
        subsample=params['subsample'],
        use_label_encoder=False,
        eval_metric='logloss'
    )

def train(X_train, y_train, params):
    X_features = build_features(X_train)
    model = build_model(params)
    model.fit(X_features, y_train,
              eval_set=[(X_features, y_train)],
              verbose=50)
    return model
EOF

mlvcs commit \
  --message "Add XGBoost model with feature engineering" \
  --author "Ivan Petrov" \
  --branch "feature/xgboost" \
  --files /tmp/xgb_model.py

mlvcs experiment update \
  --status completed \
  --metrics '{
    "accuracy": 0.941,
    "precision": 0.938,
    "recall": 0.921,
    "f1": 0.929,
    "roc_auc": 0.974,
    "train_time_sec": 87
  }'

mlvcs model register fraud-xgb-v1 \
  --version 2.0.0 \
  --framework xgboost \
  --metrics '{"accuracy": 0.941, "f1": 0.929, "roc_auc": 0.974}' \
  --params '{"n_estimators": 300, "max_depth": 6, "lr": 0.05}'

echo '{"model": "XGBClassifier", "accuracy": 0.941}' > /tmp/xgb_v1.pkl
mlvcs model upload /tmp/xgb_v1.pkl
```

---

### Этап 4 — Третий эксперимент (тонкая настройка)

```bash
mlvcs experiment create gradient-boosting-tuned \
  --description "XGBoost после grid search по гиперпараметрам" \
  --params '{
    "model": "XGBClassifier",
    "n_estimators": 500,
    "max_depth": 5,
    "learning_rate": 0.02,
    "subsample": 0.85,
    "colsample_bytree": 0.75,
    "min_child_weight": 3
  }' \
  --tags "xgboost,tuned,grid-search"

mlvcs experiment update --status running

mlvcs commit \
  --message "Add hyperparameter tuning results" \
  --author "Ivan Petrov" \
  --branch "feature/xgboost"

mlvcs experiment update \
  --status completed \
  --metrics '{
    "accuracy": 0.958,
    "precision": 0.954,
    "recall": 0.947,
    "f1": 0.950,
    "roc_auc": 0.981,
    "train_time_sec": 213
  }'

mlvcs model register fraud-xgb-tuned \
  --version 2.1.0 \
  --framework xgboost \
  --metrics '{"accuracy": 0.958, "f1": 0.950, "roc_auc": 0.981}' \
  --params '{"n_estimators": 500, "max_depth": 5, "lr": 0.02}'

echo '{"model": "XGBClassifier_tuned", "accuracy": 0.958}' > /tmp/xgb_tuned.pkl
mlvcs model upload /tmp/xgb_tuned.pkl
```

---

### Этап 5 — Сравнение экспериментов и выбор лучшей модели

```bash
# Посмотреть все эксперименты проекта
mlvcs experiment list

# Вывод будет примерно таким:
# ID                                   NAME                           STATUS       CREATED
# abc-111...                           logistic-regression-baseline   completed    2026-03-11
# abc-222...                           gradient-boosting-v1           completed    2026-03-11
# abc-333...                           gradient-boosting-tuned        completed    2026-03-11

# Посмотреть историю коммитов
mlvcs log --limit 10

# Посмотреть ветки
mlvcs branches
```

Для сравнения метрик удобно использовать API напрямую:

```bash
# Получить ID проекта
PROJ_ID=$(curl -s http://localhost:8000/api/v1/projects/ | \
  python3 -c "
import sys, json
projects = json.load(sys.stdin)
for p in projects:
    if p['name'] == 'fraud-detection':
        print(p['id'])
")

# Вывести все эксперименты с метриками
curl -s http://localhost:8000/api/v1/projects/$PROJ_ID/experiments | \
  python3 -c "
import sys, json
exps = json.load(sys.stdin)
print(f'{'Название':<35} {'Accuracy':>10} {'F1':>8} {'ROC-AUC':>10}')
print('-' * 65)
for e in exps:
    m = e.get('metrics') or {}
    print(f'{e[\"name\"]:<35} {m.get(\"accuracy\", \"-\"):>10} {m.get(\"f1\", \"-\"):>8} {m.get(\"roc_auc\", \"-\"):>10}')
"
```

---

### Этап 6 — Продвижение лучшей модели в production

```bash
# Переключиться на эксперимент с лучшей моделью
# (mlvcs автоматически переключается при создании — используй project use если нужно)

# Посмотреть модели текущего эксперимента
mlvcs model list

# Продвинуть в production
mlvcs model promote

# Вывод: ✅ Model fraud-xgb-tuned v2.1.0 promoted to production
```

---

### Этап 7 — Просмотр истории и воспроизводимость

```bash
# Посмотреть историю коммитов
mlvcs log

# Пример вывода:
# a1b2c3d  2026-03-11  Ivan Petrov
#          Add hyperparameter tuning results
#          Files: xgb_model.py
#
# d4e5f6g  2026-03-11  Ivan Petrov
#          Add XGBoost model with feature engineering
#          Files: xgb_model.py

# Посмотреть что изменилось в конкретном коммите
mlvcs diff a1b2c3d

# Скачать артефакт конкретной модели через API
EXP_ID="id-вашего-эксперимента"
MODEL_ID="id-вашей-модели"
curl -O http://localhost:8000/api/v1/experiments/$EXP_ID/models/$MODEL_ID/download
```

---

### Этап 8 — Повседневные задачи

```bash
# Утром — убедиться что система работает
mlvcs health

# Переключиться на нужный проект
mlvcs project use fraud-detection

# Создать новый эксперимент для A/B теста
mlvcs experiment create ab-test-new-features \
  --params '{"new_features": ["amount_velocity", "merchant_category"]}' \
  --tags "ab-test,new-features"

# ... работа ...

# В конце дня — зафиксировать всё
mlvcs commit \
  --message "End of day: add new feature experiments" \
  --files ./notebooks/eda.py ./src/features.py
```

---

## Управление данными и обслуживание

### Полезные команды Docker

```bash
# Запустить систему
docker compose up -d

# Запустить и пересобрать образы (после изменений кода)
docker compose up -d --build

# Остановить систему (данные сохраняются)
docker compose stop

# Запустить снова после остановки
docker compose start

# Перезапустить один сервис
docker compose restart backend
docker compose restart postgres
docker compose restart minio

# Посмотреть статус всех контейнеров
docker compose ps

# Посмотреть логи
docker compose logs                    # все сервисы
docker compose logs backend            # только backend
docker compose logs backend --tail=50  # последние 50 строк
docker compose logs -f                 # в реальном времени

# Зайти внутрь контейнера
docker exec -it mlvcs_backend bash
docker exec -it mlvcs_postgres bash

# Полный сброс (УДАЛЯЕТ ВСЕ ДАННЫЕ)
docker compose down -v
```

### Работа с PostgreSQL напрямую

```bash
# Зайти в psql
docker exec -it mlvcs_postgres psql -U mlvcs -d mlvcs_db

# Полезные SQL запросы:

# Статистика по таблицам
SELECT
  (SELECT COUNT(*) FROM projects)      as projects,
  (SELECT COUNT(*) FROM experiments)   as experiments,
  (SELECT COUNT(*) FROM model_versions) as models,
  (SELECT COUNT(*) FROM code_commits)  as commits;

# Все эксперименты с метриками
SELECT name, status, metrics, created_at
FROM experiments
ORDER BY created_at DESC;

# Production модели
SELECT model_name, version, metrics, created_at
FROM model_versions
WHERE is_production = true;

# Выйти из psql
\q
```

### Бэкап и восстановление

```bash
# Создать бэкап базы данных
docker exec mlvcs_postgres pg_dump -U mlvcs mlvcs_db > backup_$(date +%Y%m%d).sql

# Восстановить из бэкапа
docker exec -i mlvcs_postgres psql -U mlvcs mlvcs_db < backup_20260311.sql
```

---

## Загрузка на GitHub и перенос на другой компьютер

### Первая загрузка на GitHub

```bash
cd ~/projects/ml-versioning-system

# 1. Настроить git (если не настроен)
git config --global user.name "Твоё Имя"
git config --global user.email "твой@email.com"

# 2. Инициализировать репозиторий
git init
git add .

# Убедиться что .env НЕ добавлен
git status | grep "\.env"   # должно быть пусто

git commit -m "feat: initial MLVCS system"

# 3. Создать репо на github.com (без README и .gitignore!)
# 4. Подключить и отправить
git remote add origin https://github.com/YOUR_USERNAME/ml-versioning-system.git
git branch -M main
git push -u origin main
# При запросе пароля — вставить Personal Access Token (не пароль!)
```

### Создание Personal Access Token

1. GitHub → аватар → **Settings**
2. **Developer settings** → **Personal access tokens** → **Tokens (classic)**
3. **Generate new token (classic)**
4. Выбрать scope **`repo`**
5. Скопировать токен (показывается один раз!)

```bash
# Сохранить чтобы не вводить каждый раз
git config --global credential.helper store
```

### Обновление репозитория после изменений

```bash
git add .
git commit -m "fix: описание изменений"
git push
```

### Развернуть на другом компьютере

Требования на второй машине: **только Docker и Git**.

```bash
# 1. Клонировать
git clone https://github.com/YOUR_USERNAME/ml-versioning-system.git
cd ml-versioning-system

# 2. Создать .env (на новой машине его нет — он в .gitignore)
cp .env.example .env

# 3. Запустить
docker compose up -d --build

# 4. Подождать и проверить
sleep 30
curl http://localhost:8000/health
# {"status":"healthy"}

# 5. Запустить тесты
bash tests/test_system.sh
```

---

## Частые проблемы и их решения

### ❌ `error: externally-managed-environment` при pip install

**Причина:** Ubuntu 24 защищает системный Python.

**Решение:** Использовать виртуальное окружение.
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests
```

---

### ❌ `Cannot connect to API at http://localhost:8000`

**Причина:** Система не запущена или ещё не стартовала.

**Решение:**
```bash
docker compose up -d
sleep 30
curl http://localhost:8000/health
```

---

### ❌ Тесты проходят только тест 1 и останавливаются

**Причина:** `(( PASS++ ))` в bash возвращает код ошибки при нулевом значении, и `set -e` останавливает скрипт.

**Решение:** Убедиться что в `tests/test_system.sh` используется `PASS=$((PASS+1))` вместо `((PASS++))` и отсутствует строка `set -e` в начале файла.

---

### ❌ `Project 'test-mnist-project' already exists` при повторном запуске тестов

**Причина:** Тестовые данные остались от предыдущего запуска.

**Решение:**
```bash
# Удалить тестовые проекты
curl -s http://localhost:8000/api/v1/projects/ | python3 -c "
import sys, json
for p in json.load(sys.stdin): print(p['id'])
" | xargs -I{} curl -s -X DELETE http://localhost:8000/api/v1/projects/{}

# Или полный сброс базы
docker compose down -v
docker compose up -d
sleep 30
```

---

### ❌ `docker: command not found` или `permission denied`

**Решение:**
```bash
# Добавить себя в группу docker
sudo usermod -aG docker $USER

# Применить без перезагрузки
newgrp docker

# Проверить
docker run hello-world
```

---

### ❌ `WARN: version is obsolete` в docker compose

**Это предупреждение, не ошибка.** Система работает нормально. Можно убрать строку `version: "3.9"` из `docker-compose.yml` — она устарела в новых версиях Docker Compose.

---

### ❌ Контейнер `mlvcs_backend` в статусе `exited`

**Диагностика:**
```bash
docker compose logs backend --tail=100
```

Частые причины и решения:

| Ошибка в логах | Решение |
|----------------|---------|
| `could not connect to server` | PostgreSQL ещё не готов — `docker compose restart backend` |
| `No module named 'app'` | Проверить что все `__init__.py` файлы на месте |
| `Address already in use` | Порт 8000 занят — `sudo lsof -i :8000` и завершить процесс |

---

### ❌ MinIO недоступен (порт 9001)

```bash
docker compose logs minio
docker compose restart minio
```

---

## Веб-интерфейсы

| Сервис | URL | Логин | Пароль |
|--------|-----|-------|--------|
| API документация (Swagger) | http://localhost:8000/docs | — | — |
| API документация (ReDoc) | http://localhost:8000/redoc | — | — |
| MinIO консоль | http://localhost:9001 | minioadmin | minioadmin123 |

---

## Лицензия

MIT License — свободное использование, модификация и распространение.
