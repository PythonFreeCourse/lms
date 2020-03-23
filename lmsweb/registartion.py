import os
import csv
import typing
import logging

import requests

from lms.lmsweb import config
from lms.lmsweb import models

_logger = logging.getLogger(__name__)


class UserToCreate(typing.NamedTuple):
    first_name: str
    last_name: str
    email: str
    password: str

    def to_dict(self):
        return self._asdict()

    @classmethod
    def get_fields(cls):
        return cls._fields


class UserRegistrationCreator(object):
    _session = requests.Session()

    def __init__(self, users_to_create: typing.Sequence[UserToCreate]):
        self._users_to_create = users_to_create
        self._failed_users: typing.List[UserToCreate] = []

    @classmethod
    def from_csv_file(cls, file_path: str) -> 'UserRegistrationCreator':
        """
        CSV file should be with three columns, and in the header: first_name,last_name,email and password[optional]
        """

        if not os.path.exists(file_path):
            raise ValueError

        with open(file_path, 'r') as file_reader:
            csv_records = csv.DictReader(file_reader)

        users = []
        for record in csv_records:
            if 'password' not in record:
                record['password'] = os.urandom(10).hex()
            users.append(UserToCreate(**record))

        return cls(users)

    def dump_failed_users_to_csv(self, file_path: str) -> None:
        with open(file_path, 'w') as file_writer:
            writer = csv.DictWriter(file_writer, UserToCreate.get_fields())
            for failed_user in self._failed_users:
                writer.writerow(failed_user.to_dict())

    def run_registration(self):
        for user in self._users_to_create:
            try:
                self._get_or_create_user_in_model(user)
                self._send_user_email_registration(user)
            except Exception:
                _logger.exception('Failed to create user %s, continue to next user', user.email)
                self._failed_users.append(user)

    @staticmethod
    def _get_or_create_user_in_model(user: UserToCreate) -> None:
        _logger.info('Create user with email: %s', user.email)
        models.User.get_or_create(**{
            models.User.mail_address.name: user.email,
            models.User.username.name: user.email,
        }, defaults={
            models.User.fullname.name: F'{user.first_name} {user.last_name}',
            models.User.role.name: models.Role.get_student_role(),
            models.User.password.name: user.password,
        })

    def _send_user_email_registration(self, user: UserToCreate) -> None:
        response = None
        try:
            response = self._session.post(
                url=F'https://api.mailgun.net/v3/{config.MAILGUN_DOMAIN}/messages',
                data={
                    'from': F'no-reply@{config.MAILGUN_DOMAIN}',
                    'to': user,
                    'subject': 'Learn python - registration email',
                    'text': 'Dear Student.\n A profile for login to the study program created just for you!\n'
                            F'Your initial login details:\n'
                            F'username: {user.email}\npassword: {user.password}\n'  # TODO: change password?
                            'You should change your password as soon as possible. big snakes'
                            F'Out there to get your password!.\n logging address is: {config.SERVER_ADDRESS}'
                },
                auth=('api', config.MAILGUN_API_KEY)
            )
            response.raise_for_status()
        except Exception:
            _logger.exception('Failed to create user %s. response: %s', user.email, response.content)
            raise
