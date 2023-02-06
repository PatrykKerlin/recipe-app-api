FROM python:3.11.1-alpine3.17
LABEL maintainer="patrykkerlin.netlify.app"

ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /tmp/requirements.txt
