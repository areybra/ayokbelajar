"""
WSGI config for ayokbelajar_proj project.

It exposes the WSGI callable as a module-level variable named ``application``.

For VPS / shared hosting (cPanel Passenger / uWSGI) dan Vercel, cukup import `application`.
Universal — tidak ada kode khusus Vercel di sini.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ayokbelajar_proj.settings')

application = get_wsgi_application()

# Alias untuk server yang mencari `app` bukan `application` (mis. beberapa PaaS)
app = application
