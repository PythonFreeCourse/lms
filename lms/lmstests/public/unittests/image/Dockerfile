FROM python:3.8.0-slim-buster

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

RUN adduser --disabled-password --gecos '' app-user

RUN mkdir -p /app_dir/lms
RUN chown -R app-user:app-user /app_dir

WORKDIR /app_dir/lms
ENV PYTHONPATH /app_dir/:$PYTHONPATH
