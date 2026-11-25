#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
echo y | plotly_get_chrome
python manage.py collectstatic --no-input
python manage.py migrate