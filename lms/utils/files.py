LANGUAGE_EXTENSIONS_TO_NAMES = {
    'bat': 'batch',
    'h': 'c',
    'htm': 'html',
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


def get_language_name_by_extension(ext: str) -> str:
    return LANGUAGE_EXTENSIONS_TO_NAMES.get(ext, ext)
