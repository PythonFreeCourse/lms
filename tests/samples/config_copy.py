# flake8: noqa

import os

WTF_CSRF_ENABLED = False  # On production, delete this line!

SECRET_KEY = ''
SERVER_ADDRESS = os.getenv('SERVER_ADDRESS', '127.0.0.1:80')

FEATURE_FLAG_CHECK_IDENTICAL_CODE_ON = os.getenv(
    'FEATURE_FLAG_CHECK_IDENTICAL_CODE_ON', False,
)



USERS_CSV = 'users.csv'


# Babel config
LANGUAGES = {
    'en': 'English',
    'he': 'Hebrew',
}
