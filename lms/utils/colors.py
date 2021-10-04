import re
from typing import Optional

from lms.utils.consts import COLORS


HEX_COLOR = re.compile(r'#?(?P<hex>[a-f0-9]{6}|[a-f0-9]{3})')


def get_hex_color(number: str) -> Optional[str]:
    if color := HEX_COLOR.match(number):
        return '#' + color.groupdict()['hex']
    elif color := COLORS.get(number):
        return color
    raise ValueError('This is not a valid hex color')
