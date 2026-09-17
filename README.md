<div align="center">

# plexe ✨

[![PyPI version](https://img.shields.io/pypi/v/plexe.svg)](https://pypi.org/project/plexe/)
[![Discord](https://img.shields.io/discord/1300920499886358529?logo=discord&logoColor=white)](https://discord.gg/SefZDepGMv)

<img src="resources/backed-by-yc.png" alt="backed-by-yc" width="20%">


Создавайте модели машинного обучения на естественном языке.

[Быстрый старт](#1-быстрый-старт) |
[Возможности](#2-возможности) |
[Установка](#3-установка) |
[Документация](#4-документация)

*[English](README.en.md) · Русский*

<br>

**plexe** позволяет создавать модели машинного обучения, описывая их обычным языком. Просто объясните, что вам нужно,
предоставьте набор данных — и система на базе ИИ построит полностью работоспособную модель в автоматическом
агентном режиме. Также доступен [управляемый облачный сервис](https://plexe.ai).

<br>

Посмотрите демо на YouTube:
[![Building an ML model with Plexe](resources/demo-thumbnail.png)](https://www.youtube.com/watch?v=bUwCSglhcXY)
</div>

## 1. Быстрый старт

### Установка
```bash
pip install plexe
export OPENAI_API_KEY=<your-key>
export ANTHROPIC_API_KEY=<your-key>
```

### Использование plexe

Укажите табличный набор данных (Parquet, CSV, ORC или Avro) и задачу на естественном языке:

```bash
python -m plexe.main \
    --train-dataset-uri data.parquet \
    --intent "predict whether a passenger was transported" \
    --max-iterations 5
```

```python
from plexe.main import main
from pathlib import Path

best_solution, metrics, report = main(
    intent="predict whether a passenger was transported",
    data_refs=["train.parquet"],
    max_iterations=5,
    work_dir=Path("./workdir"),
)
print(f"Performance: {best_solution.performance:.4f}")
```

## 2. Возможности

### 2.1. 🤖 Мультиагентная архитектура
Система использует 14 специализированных ИИ-агентов, распределённых по 6-фазному рабочему процессу, чтобы:
- проанализировать ваши данные и определить задачу машинного обучения;
- выбрать подходящую метрику оценки;
- найти лучшую модель через итеративный поиск, управляемый гипотезами;
- оценить качество и устойчивость модели;
- упаковать модель для развёртывания.

### 2.2. 🎯 Автоматическое построение моделей
Постройте готовую модель одним вызовом. Для табличных данных plexe поддерживает **XGBoost**, **CatBoost**, **LightGBM**, **Keras** и **PyTorch**:

```python
best_solution, metrics, report = main(
    intent="predict house prices based on property features",
    data_refs=["housing.parquet"],
    max_iterations=10,                    # Итерации поиска
    allowed_model_types=["xgboost"],      # Или пусть plexe выберет сам
    enable_final_evaluation=True,         # Оценка на отложенной тестовой выборке
)
```

Полный список опций CLI: `python -m plexe.main --help`.

Результат — самодостаточный пакет модели в `work_dir/model/` (также архивируется в `model.tar.gz`).
Пакет не зависит от `plexe`: постройте модель с помощью plexe и разверните её где угодно:

```
model/
├── artifacts/          # Обученная модель + пайплайн признаков (pickle)
├── src/                # Предиктор для инференса, код пайплайна, шаблон обучения
├── schemas/            # JSON-схемы входа/выхода
├── config/             # Гиперпараметры
├── evaluation/         # Метрики и подробные аналитические отчёты
├── model.yaml          # Метаданные модели
└── README.md           # Инструкция по использованию с примером кода
```

### 2.3. 🐳 Docker-образы «всё включено»
Запускайте plexe с уже настроенным окружением — PySpark, Java и все зависимости в комплекте.
Для типовых сценариев есть `Makefile`:

```bash
make build          # Собрать Docker-образ
make test-quick     # Быстрая проверка работоспособности (~1 итерация)
make run-titanic    # Запуск на наборе данных Spaceship Titanic
```

Либо запускайте напрямую:

```bash
docker run --rm \
    -e OPENAI_API_KEY=$OPENAI_API_KEY \
    -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
    -v $(pwd)/data:/data -v $(pwd)/workdir:/workdir \
    plexe:py3.12 python -m plexe.main \
        --train-dataset-uri /data/dataset.parquet \
        --intent "predict customer churn" \
        --work-dir /workdir \
        --spark-mode local
```

Файл `config.yaml` из корня проекта монтируется автоматически. Также доступен образ
с Databricks Connect: `docker build --target databricks .`

### 2.4. ⚙️ Конфигурация через YAML
Настраивайте маршрутизацию LLM, параметры поиска, настройки Spark и многое другое через файл конфигурации:

```yaml
# config.yaml
max_search_iterations: 5
allowed_model_types: [xgboost, catboost]
spark_driver_memory: "4g"
hypothesiser_llm: "openai/gpt-5-mini"
feature_processor_llm: "anthropic/claude-sonnet-4-5-20250929"
```

```bash
CONFIG_FILE=config.yaml python -m plexe.main ...
```

Все доступные параметры см. в [`config.yaml.template`](config.yaml.template).

### 2.5. 🌐 Поддержка разных провайдеров LLM
Plexe работает с LLM через [LiteLLM](https://docs.litellm.ai/docs/providers), поэтому вы можете использовать любого поддерживаемого провайдера:

```yaml
# Направляйте разных агентов к разным провайдерам
hypothesiser_llm: "openai/gpt-5-mini"
feature_processor_llm: "anthropic/claude-sonnet-4-5-20250929"
model_definer_llm: "ollama/llama3"
```

> [!NOTE]
> Plexe *должен* работать с большинством провайдеров LiteLLM, но мы активно тестируем только модели
> `openai/*` и `anthropic/*`. Если с другими провайдерами возникнут проблемы, сообщите нам.

### 2.6. 📊 Дашборд экспериментов
Визуализируйте результаты экспериментов, деревья поиска и отчёты об оценке во встроенном дашборде на Streamlit:

```bash
python -m plexe.viz --work-dir ./workdir
```

### 2.7. 🔌 Расширяемость
Подключайте plexe к собственным системам хранения, отслеживания и развёртывания через интерфейс `WorkflowIntegration`:

```python
main(intent="...", data_refs=[...], integration=MyCustomIntegration())
```

Полное описание интерфейса — в [`plexe/integrations/base.py`](plexe/integrations/base.py).

## 3. Установка

### 3.1. Варианты установки
```bash
pip install plexe                    # Базовая версия (XGBoost, Keras, scikit-learn)
```

Дополнительные зависимости можно добавлять либо по фреймворкам, либо по типам задач:
- Экстра-пакеты фреймворков: `catboost`, `lightgbm`, `pytorch`
- Экстра-пакеты задач: `tabular` (CatBoost + LightGBM), `vision` (PyTorch)
- Экстра-пакеты платформ: `pyspark`, `aws`

Примеры:
```bash
pip install "plexe[tabular,pyspark]"   # стек для табличных данных + локальный PySpark
pip install "plexe[pytorch,aws]"       # конкретный фреймворк + поддержка S3
```

Требуется Python >= 3.10, < 3.13.

### 3.2. API-ключи
```bash
export OPENAI_API_KEY=<your-key>
export ANTHROPIC_API_KEY=<your-key>
```
Полный список поддерживаемых провайдеров см. в [документации LiteLLM](https://docs.litellm.ai/docs/providers).

## 4. Документация
Полная документация доступна на [docs.plexe.ai](https://docs.plexe.ai).

## 5. Участие в разработке
Рекомендации приведены в [CONTRIBUTING.ru.md](CONTRIBUTING.ru.md). Присоединяйтесь к нашему [Discord](https://discord.gg/SefZDepGMv), чтобы связаться с командой.

## 6. Лицензия
[Лицензия Apache-2.0](LICENSE)

## 7. Цитирование
Если вы используете Plexe в своих исследованиях, ссылайтесь на него так:

```bibtex
@software{plexe2025,
  author = {De Bernardi, Marcello AND Dubey, Vaibhav},
  title = {Plexe: Build machine learning models using natural language.},
  year = {2025},
  publisher = {GitHub},
  howpublished = {\url{https://github.com/plexe-ai/plexe}},
}
```
