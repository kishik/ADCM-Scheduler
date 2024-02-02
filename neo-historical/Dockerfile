# Используйте базовый образ Python
FROM python:3.11

# Создайте рабочую директорию внутри контейнера
WORKDIR /app

# Скопируйте зависимости в контейнер
COPY requirements.txt .

# Установите зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Скопируйте ваш скрипт Python в контейнер
COPY GESN_graph_creation.py .
COPY 2022-02-07.xlsx .
COPY create_group_graph.py .
COPY solution.xls .

# Команда для запуска скрипта при запуске контейнера
CMD ["bash", "creation_script.sh"]
# CMD ["tail", "-f", "/dev/null"]
