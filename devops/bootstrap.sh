#!/bin/bash

SCRIPT_FILE_PATH=$(readlink -f "${0}")
SCRIPT_FOLDER=$(dirname "${SCRIPT_FILE_PATH}")
MAIN_FOLDER="${SCRIPT_FOLDER}/../lms"

docker exec -i lms-rabbitmq-1 rabbitmqctl add_vhost lmstests-public
docker exec -i lms-rabbitmq-1 rabbitmqctl add_vhost lmstests-sandbox
docker exec -i lms-rabbitmq-1 rabbitmqctl set_permissions -p lmstests-public rabbit-user  ".*" ".*" ".*"
docker exec -i lms-rabbitmq-1 rabbitmqctl set_permissions -p lmstests-sandbox rabbit-user  ".*" ".*" ".*"
docker exec -i lms-http-1 python lmsdb/bootstrap.py

# build the image for docker inside a docker!
docker exec lms-checks-docker-engine-1 mkdir -p /home/lms
docker cp "${MAIN_FOLDER}"/lmstests/public/unittests/image/requirements.txt lms-checks-docker-engine-1:/home/lms/.
docker cp "${MAIN_FOLDER}"/lmstests/public/unittests/image/Dockerfile lms-checks-docker-engine-1:/home/lms/.
docker exec lms-checks-docker-engine-1  sh -c "cd /home/lms && docker build -t lms ."
