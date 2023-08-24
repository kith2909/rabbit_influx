# Base installation Python
FROM python:3.10
WORKDIR /app

COPY requirements.txt ./
COPY producer.py /app/producer.py
COPY . /app


RUN pip install --trusted-host pypi.python.org -r requirements.txt 

# Запускаем скрипт wait-for-it.sh, ожидая доступности RabbitMQ
CMD ["python", "producer.py"]

