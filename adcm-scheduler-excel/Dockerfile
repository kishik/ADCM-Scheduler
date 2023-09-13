# syntax=docker/dockerfile:1
FROM python:3.9
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN mkdir /app
COPY ./ /app

WORKDIR /app
RUN ls
RUN pip install -r requirements.txt
RUN ls
RUN python3 manage.py makemigrations && python3 manage.py migrate

EXPOSE 8000

