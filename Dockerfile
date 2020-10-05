FROM python:3-buster

RUN apt update \
  && apt install -y --no-install-recommends docker.io vim unixodbc-dev \
  && apt clean \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

# Install vnu (html/css validator)
RUN wget https://github.com/validator/validator/releases/download/20.6.30/vnu.linux.zip && \
    unzip vnu.linux.zip -d /opt/vnu/ && \
    chmod +x /opt/vnu/vnu-runtime-image/bin/vnu
ENV PATH=/opt/vnu/vnu-runtime-image/bin:$PATH

RUN adduser --disabled-password --gecos '' app-user

RUN mkdir -p /app_dir/lms
RUN chown -R app-user:app-user /app_dir

# Note: we don't copy the code to container because we mount the code in different ways
# on each setup
WORKDIR /app_dir/lms
ENV LOGURU_LEVEL INFO 
ENV PYTHONPATH /app_dir/:$PYTHONPATH
