FROM python:3.9.15-slim-buster

ENV PYTHONUNBUFFERED 1
EXPOSE 8000
WORKDIR /app/
COPY requirements.txt /requirements.txt

RUN apt-get update && apt-get install -y build-essential python-dev git traceroute

RUN apt-get update \
    && apt-get install -y \
    && pip install --upgrade pip setuptools \
    && pip install --no-cache-dir -r /requirements.txt

COPY . /app/
WORKDIR /app/app/

CMD python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001