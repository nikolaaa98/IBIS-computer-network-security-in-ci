# Dockerfile - Python image for all services
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# copy requirements first for better caching
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

# copy source
COPY ./src /app

# default command (can be overridden by docker-compose)
CMD ["python", "modbus_server.py"]
