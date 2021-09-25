import secrets
import string


def generate_invite_code(length: int = 10) -> str:
    return ''.join(
        secrets.SystemRandom().choices(
            string.ascii_letters + string.digits, k=length,
        ),
    )
