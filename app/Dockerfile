FROM --platform=$BUILDPLATFORM python:3.10-alpine AS builder

WORKDIR /app
COPY Pipfile /app/
COPY Pipfile.lock /app/

RUN ["pip3", "install", "pipenv"]
RUN ["pipenv", "install"]
COPY /app /app/

ENTRYPOINT ["pipenv", "run", "flask", "--app", "main", "run", "--host", "0.0.0.0" ]