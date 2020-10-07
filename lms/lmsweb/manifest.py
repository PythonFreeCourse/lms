from lms.lmsweb.config import SERVER_ADDRESS


MANIFEST = {
    'name': "Python's Course LMS",
    'short_name': 'LMS',
    'theme_color': '#1290f4',
    'background_color': '#2196f3',
    'display': 'standalone',
    'scope': SERVER_ADDRESS,
    'start_url': SERVER_ADDRESS,
    'icons': [
        {
            'src': '/static/avatar.jpg',
            'type': 'image/jpeg',
            'sizes': '512x512',
        },
        {
            'src': '/static/icons/android-icon-36x36.png',
            'sizes': '36x36',
            'type': 'image/png',
            'density': '0.75',
        },
        {
            'src': '/static/icons/android-icon-48x48.png',
            'sizes': '48x48',
            'type': 'image/png',
            'density': '1.0',
        },
        {
            'src': '/static/icons/android-icon-72x72.png',
            'sizes': '72x72',
            'type': 'image/png',
            'density': '1.5',
        },
        {
            'src': '/static/icons/android-icon-96x96.png',
            'sizes': '96x96',
            'type': 'image/png',
            'density': '2.0',
        },
        {
            'src': '/static/icons/android-icon-144x144.png',
            'sizes': '144x144',
            'type': 'image/png',
            'density': '3.0',
        },
        {
            'src': '/static/icons/android-icon-192x192.png',
            'sizes': '192x192',
            'type': 'image/png',
            'density': '4.0',
        },
    ],
}
