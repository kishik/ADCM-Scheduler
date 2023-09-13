# Используйте базовый образ Python
FROM python:3

# Создайте рабочую директорию внутри контейнера
WORKDIR /app

# Скопируйте зависимости в контейнер
COPY requirements.txt .

# Установите зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Скопируйте ваш скрипт Python в контейнер
COPY GESN_graph_creation.py .
COPY 2022-02-07.xlsx .

# Команда для запуска скрипта при запуске контейнера
CMD ["python", "GESN_graph_creation.py"]
# CMD ["tail", "-f", "/dev/null"]
