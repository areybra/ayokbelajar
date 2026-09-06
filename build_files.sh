#!/bin/bash
# Vercel build: install deps + collectstatic
pip install -r requirements.txt
python manage.py collectstatic --noinput
