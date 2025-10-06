# Dockerfile - base image for IBIS demo services
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# copy only requirements first for Docker layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt

# create app dir layout (actual code will be mounted by docker-compose)
RUN mkdir -p /app/src /app/logs /app/pids /app/templates

# default workdir - note: docker-compose will set working_dir per service
WORKDIR /app

# default command - not used (overridden by compose)
CMD ["sleep", "infinity"]
