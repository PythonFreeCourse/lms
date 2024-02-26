FROM python:3.12

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    wget \
    unzip \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

RUN wget https://github.com/validator/validator/releases/download/20.6.30/vnu.linux.zip -O /tmp/vnu.linux.zip \
    && unzip /tmp/vnu.linux.zip -d /opt/vnu/ \
    && chmod +x /opt/vnu/vnu-runtime-image/bin/vnu \
    && rm /tmp/vnu.linux.zip

ENV PATH=/opt/vnu/vnu-runtime-image/bin:$PATH

RUN adduser --disabled-password --gecos '' app-user \
    && mkdir -p /app_dir/lms \
    && chown -R app-user:app-user /app_dir

WORKDIR /app_dir/lms
ENV LOGURU_LEVEL=INFO 
ENV PYTHONPATH=/app_dir/:$PYTHONPATH
# Note: Code is mounted at runtime, hence not copied.
