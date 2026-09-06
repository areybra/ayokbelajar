"""Vercel serverless entrypoint — import Django WSGI app.

Vercel Python runtime mencari variabel `app` di `api/index.py`.
VPS/shared hosting tetap pakai `ayokbelajar_proj/wsgi.py:application`.
"""
from ayokbelajar_proj.wsgi import application

app = application
