#!/bin/bash

SCRIPT_FILE_PATH=$(readlink -f "${0}")
SCRIPT_FOLDER=$(dirname "${SCRIPT_FILE_PATH}")
MAIN_FOLDER="${SCRIPT_FOLDER}/../lms"

docker exec -i lms_rabbitmq_1 rabbitmqctl add_vhost lmstests-public
docker exec -i lms_rabbitmq_1 rabbitmqctl add_vhost lmstests-sandbox
docker exec -i lms_rabbitmq_1 rabbitmqctl set_permissions -p lmstests-public rabbit-user  ".*" ".*" ".*"
docker exec -i lms_rabbitmq_1 rabbitmqctl set_permissions -p lmstests-sandbox rabbit-user  ".*" ".*" ".*"
docker exec -i lms_http_1 python lmsdb/bootstrap.py

# build the image for docker inside a docker!
docker exec lms_checks-docker-engine_1 mkdir /home/lms
docker cp "${MAIN_FOLDER}"/lmstests/public/unittests/image/requirements.txt lms_checks-docker-engine_1:/home/lms/.
docker cp "${MAIN_FOLDER}"/lmstests/public/unittests/image/Dockerfile lms_checks-docker-engine_1:/home/lms/.
docker exec lms_checks-docker-engine_1  sh -c "cd /home/lms && docker build -t lms ."
