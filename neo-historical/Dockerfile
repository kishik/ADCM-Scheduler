# Используйте базовый образ Python
FROM python:3.11

# Создайте рабочую директорию внутри контейнера
WORKDIR /app

# Скопируйте зависимости в контейнер
COPY requirements.txt .

# Установите зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Скопируйте ваш скрипт Python в контейнер
# COPY GESN_graph_creation.py .
# COPY 2022-02-07.xlsx .
COPY din_graph_creation.py .
COPY DIN.xlsx .
COPY Sinara.xlsx .

# Команда для запуска скрипта при запуске контейнера
CMD ["python3", "din_graph_creation.py"]
# CMD ["tail", "-f", "/dev/null"]
