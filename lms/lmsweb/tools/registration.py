import csv
import os
import typing

from flask_babel import gettext as _  # type: ignore

from lms.lmsdb import models
from lms.lmsweb import config
from lms.utils.log import log

import requests


class UserToCreate(typing.NamedTuple):
    name: str
    email: str
    password: str

    def to_dict(self):
        return self._asdict()

    @classmethod
    def get_fields(cls):
        return cls._fields


class UserRegistrationCreator:
    _session = requests.Session()

    def __init__(self, users_to_create: typing.Sequence[UserToCreate]):
        self._users_to_create = users_to_create
        self._failed_users: typing.List[UserToCreate] = []

    @property
    def users_to_create(self):
        return self._users_to_create

    @property
    def failed_users(self):
        return self._failed_users

    @classmethod
    def from_csv_file(cls, file_path: str) -> 'UserRegistrationCreator':
        """
        CSV file should be with three columns,
        and in the header: first_name,last_name,email and password[optional]
        """

        if not os.path.exists(file_path):
            raise ValueError

        with open(file_path, 'r') as file_reader:
            csv_records = csv.DictReader(file_reader)

            users = []
            for record in csv_records:
                if 'password' not in record:
                    record['password'] = models.User.random_password()
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
                log.exception(
                    'Failed to create user %s, continue to next user',
                    user.email,
                )
                self._failed_users.append(user)

    @staticmethod
    def _get_or_create_user_in_model(user: UserToCreate) -> None:
        log.info('Create user with email: %s', user.email)
        models.User.get_or_create(**{
            models.User.mail_address.name: user.email,
            models.User.username.name: user.email,
        }, defaults={
            models.User.fullname.name: f'{user.name}',
            models.User.role.name: models.Role.get_student_role(),
            models.User.password.name: user.password,
        })

    def _send_user_email_registration(self, user: UserToCreate) -> None:
        response = None
        text = self._build_user_text(user)
        url = f'https://api.eu.mailgun.net/v3/{config.MAILGUN_DOMAIN}/messages'
        try:
            response = self._session.post(
                url=url,
                data={
                    'from': f'lms@{config.MAILGUN_DOMAIN}',
                    'to': user,
                    'subject': (
                        'Learn Python - ',
                        _('מערכת הגשת התרגילים'),
                    ),
                    'html': text,
                },
                auth=('api', config.MAILGUN_API_KEY))
            response.raise_for_status()
        except Exception:
            log.exception(
                'Failed to create user %s. response: %s',
                user.email,
                response.content,
            )
            raise

    @staticmethod
    def _build_user_text(user: UserToCreate) -> str:
        details = {
            'username': user.email,
            'password': user.password,
            'url': config.SERVER_ADDRESS,
        }
        msg = config.MAIL_WELCOME_MESSAGE
        for k, v in details.items():
            msg = msg.replace(f'@@{k}@@', v)
        return msg


if __name__ == '__main__':
    registration = UserRegistrationCreator.from_csv_file(config.USERS_CSV)
    print(registration.users_to_create)  # noqa: T001
    registration.run_registration()
    registration.dump_failed_users_to_csv(config.ERRORS_CSV)
