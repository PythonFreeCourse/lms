FROM python:3.12-slim

COPY requirements.txt /tmp/requirements.txt
RUN pip config --user set global.progress_bar off && \
    pip3 install -r /tmp/requirements.txt

RUN adduser --disabled-password --gecos '' app-user

RUN mkdir -p /app_dir/lms
RUN chown -R app-user:app-user /app_dir

WORKDIR /app_dir/lms
ENV PYTHONPATH /app_dir/:$PYTHONPATH
