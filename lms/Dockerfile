FROM python:3.8.0-slim-buster

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN adduser --disabled-password --gecos '' app-user

RUN mkdir -p /app_dir/lms
RUN chown -R app-user:app-user /app_dir

USER app-user
# Note: we don't copy the code to container because we mount the code in different ways
# on each setup
WORKDIR /app_dir/lms
ENV PYTHONPATH /app_dir/:$PYTHONPATH
