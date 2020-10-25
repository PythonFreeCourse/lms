LANGUAGE_EXTENSIONS_TO_NAMES = {
    'bat': 'batch',
    'css': 'css',
    'h': 'c',
    'htm': 'html',
    'html': 'html',
    'j2': 'jinja2',
    'js': 'javascript',
    'md': 'markup',
    'ps1': 'powershell',
    'psm1': 'powershell',
    'py': 'python',
    'rb': 'ruby',
    'sh': 'bash',
    'sql': 'sql',
    'tex': 'latex',
    'yml': 'yaml',
}

ALLOWED_EXTENSIONS = set(LANGUAGE_EXTENSIONS_TO_NAMES)

ALLOWED_IMAGES_EXTENSIONS = {'png', 'jpeg', 'jpg', 'svg', 'tiff', 'bmp', 'ico'}

IMAGES_EXTENSIONS_TO_MIME_TYPES = {
    'png': 'image/png',
    'jpeg': 'image/jpeg',
    'jpg': 'image/jpeg',
    'svg': 'image/svg+xml',
    'tiff': 'image/tiff',
    'bmp': 'image/bmp',
    'ico': 'image/x-icon',
}


def get_language_name_by_extension(ext: str) -> str:
    return LANGUAGE_EXTENSIONS_TO_NAMES.get(ext, ext)


def get_mime_type_by_extention(ext: str) -> str:
    return IMAGES_EXTENSIONS_TO_MIME_TYPES.get(ext, 'image/' + ext)
