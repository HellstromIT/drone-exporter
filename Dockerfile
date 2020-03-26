FROM python:3.7-alpine

MAINTAINER Martin Hellstrom <martin@hellstrom.it>

WORKDIR /app

COPY requirements.txt ./

RUN apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev &&\
    pip install --no-cache-dir -r requirements.txt

COPY drone_exporter.py /drone_exporter.py

RUN chmod +x /drone_exporter.py

EXPOSE 9698

ENTRYPOINT ["/drone_exporter.py"]
