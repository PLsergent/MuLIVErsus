#!/bin/sh
poetry run uvicorn app.main:app --proxy-headers --host 0.0.0.0 --port 8081 --forwarded-allow-ips="163.172.135.27"