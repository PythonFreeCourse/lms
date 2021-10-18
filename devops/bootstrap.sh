#!/bin/bash

SCRIPT_FILE_PATH=$(readlink -f "${0}")
SCRIPT_FOLDER=$(dirname "${SCRIPT_FILE_PATH}")
MAIN_FOLDER="${SCRIPT_FOLDER}/../lms"

# Starting from docker-compose 2,
# names are network-image-id instead of network_image_id
if docker-compose --version | grep -q 'version 2'; then
  SEP="-"
else
  SEP="_"
fi

docker exec -i lms${SEP}rabbitmq${SEP}1 rabbitmqctl add_vhost lmstests-public
docker exec -i lms${SEP}rabbitmq${SEP}1 rabbitmqctl add_vhost lmstests-sandbox
docker exec -i lms${SEP}rabbitmq${SEP}1 rabbitmqctl set_permissions -p lmstests-public rabbit-user  ".*" ".*" ".*"
docker exec -i lms${SEP}rabbitmq${SEP}1 rabbitmqctl set_permissions -p lmstests-sandbox rabbit-user  ".*" ".*" ".*"
docker exec -i lms${SEP}http${SEP}1 python lmsdb/bootstrap.py

# build the image for docker inside a docker!
docker exec lms${SEP}checks-docker-engine${SEP}1 mkdir -p /home/lms
docker cp "${MAIN_FOLDER}"/lmstests/public/unittests/image/requirements.txt lms${SEP}checks-docker-engine${SEP}1:/home/lms/.
docker cp "${MAIN_FOLDER}"/lmstests/public/unittests/image/Dockerfile lms${SEP}checks-docker-engine${SEP}1:/home/lms/.
docker exec lms${SEP}checks-docker-engine${SEP}1 sh -c "cd /home/lms && docker build -t lms ."
