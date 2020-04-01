#!/bin/bash

docker exec -i lms_rabbitmq_1 rabbitmqctl add_vhost lmstests-public
docker exec -i lms_rabbitmq_1 rabbitmqctl add_vhost lmstests-sandbox
docker exec -i lms_rabbitmq_1 rabbitmqctl set_permissions -p lmstests-public rabbit-user  ".*" ".*" ".*"
docker exec -i lms_rabbitmq_1 rabbitmqctl set_permissions -p lmstests-sandbox rabbit-user  ".*" ".*" ".*"
docker exec -i lms_http_1 python lmsdb/bootstrap.py
