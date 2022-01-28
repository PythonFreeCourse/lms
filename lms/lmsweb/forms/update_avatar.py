from flask_babel import gettext as _  # type: ignore
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired, FileSize

from lms.lmsweb.config import MAX_UPLOAD_SIZE
from lms.utils.consts import MB_CONVERSION
from lms.utils.files import ALLOWED_IMAGES_EXTENSIONS


class UpdateAvatarForm(FlaskForm):
    avatar = FileField(
        'Avatar', validators=[
            FileAllowed(ALLOWED_IMAGES_EXTENSIONS),
            FileRequired(message=_('No file added')),
            FileSize(
                max_size=MAX_UPLOAD_SIZE, message=_(
                    'File size is too big - %(size)dMB allowed',
                    size=MAX_UPLOAD_SIZE // MB_CONVERSION,
                ),
            ),
        ],
    )
