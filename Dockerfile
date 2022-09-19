FROM python:3.9-slim-buster 

RUN apt-get update && \
    apt-get install -y python3-pip && \
    pip3 install --upgrade pip && \
    pip3 install poetry

COPY . /app
WORKDIR /app

RUN poetry install

ENTRYPOINT ["./entrypoint.sh"]