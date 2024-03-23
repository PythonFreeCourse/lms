#!/bin/bash -x

original_dir="$(pwd)"
cd "$(dirname "${BASH_SOURCE[0]}")" || return

if [ "${1}" = "update" ]; then
    echo "Updating translations"
    pybabel extract -F "lms/babel.cfg" -o "lms/lmsweb/translations/messages.pot" "lms"
    pybabel update -i "lms/lmsweb/translations/messages.pot" -d "lms/lmsweb/translations"
fi

echo "Compiling Flask Babel"
pybabel compile -d "lms/lmsweb/translations"

cd "$original_dir" || return
