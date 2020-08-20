FROM python:3.8.0-buster

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

RUN apt-get update
RUN apt-get install -y docker.io
RUN adduser --disabled-password --gecos '' app-user

RUN mkdir -p /app_dir/lms
RUN chown -R app-user:app-user /app_dir

# Note: we don't copy the code to container because we mount the code in different ways
# on each setup
WORKDIR /app_dir/lms
ENV LOGURU_LEVEL INFO 
ENV PYTHONPATH /app_dir/:$PYTHONPATH
