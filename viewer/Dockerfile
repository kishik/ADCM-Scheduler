# Используйте базовый образ Python
FROM python:3.11
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Создайте рабочую директорию внутри контейнера
RUN mkdir /app
COPY ./ /app

WORKDIR /app
RUN apt update
RUN pip install -r requirements.txt
RUN apt install -y nodejs
RUN apt install -y npm
# Команда для запуска скрипта при запуске контейнера
RUN bash creation_script.sh

EXPOSE 8070
EXPOSE 3000
CMD python3 -m http.server 3000 & uvicorn main:app --host 0.0.0.0 --port 8070
RUN ls
# CMD ["python", "GESN_graph_creation.py"]
