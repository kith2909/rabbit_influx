# Используйте базовый образ Python
FROM python:3.10
WORKDIR /app

COPY requirements.txt /app
COPY consumer.py /app

RUN pip install -r /app/requirements.txt

# Запускаем скрипт wait-for-it.sh, ожидая доступности RabbitMQ
CMD ["python", "consumer.py"]

