#!/bin/bash

set -x

SCRIPT_FILE_PATH=$(readlink -f "${0}")
SCRIPT_FOLDER=$(dirname "${SCRIPT_FILE_PATH}")
MAIN_FOLDER="${SCRIPT_FOLDER}/.."
VENV_DIR="${MAIN_FOLDER}/venv"
LMSAPP_FOLDER="${MAIN_FOLDER}/lms"
LMSWEB_FOLDER="${LMSAPP_FOLDER}/lmsweb"
CONFIG_FILE_PATH="${LMSWEB_FOLDER}/config.py"
CONFIG_EXAMPLE_FILE_PATH="${LMSWEB_FOLDER}/config.py.example"
DB_BOOTSTRAP_FILE_PATH="${LMSAPP_FOLDER}/lmsdb/bootstrap.py"

if (command -v pip); then
  pip_exec=pip
else
  pip_exec=pip3
fi

if (command -v python); then
  python_exec=python
else
  python_exec=python3
fi

if ! (test -f "${CONFIG_FILE_PATH}"); then
  echo "Creating config from template"
  cp "${CONFIG_EXAMPLE_FILE_PATH}" "${CONFIG_FILE_PATH}"
  echo "Writing secret key to config"
  secret_key=$($python_exec -c "import os;print(os.urandom(32).hex())")
  echo "SECRET_KEY = \"${secret_key}\"" >>"${CONFIG_FILE_PATH}"
else
  echo "Config already exists"
fi

echo "Creating venv"
$python_exec -m venv "${VENV_DIR}"
echo "Activating venv"
source "${VENV_DIR}/bin/activate"

echo "Installing prod requirements"
$pip_exec install -r "${MAIN_FOLDER}/requirements.txt"
echo "Installing dev requirements"
$pip_exec install -r "${MAIN_FOLDER}/dev_requirements.txt"

echo "Compiling Flask Babel"
pybabel compile -d "${MAIN_FOLDER}/lms/lmsweb/translations"

echo "Creating local SQLite DB"
$python_exec "${DB_BOOTSTRAP_FILE_PATH}"

set +x
