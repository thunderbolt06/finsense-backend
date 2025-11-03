"""
Quick script to run migrations if manage.py doesn't work due to virtual env issues.
Run this with: python setup_db.py
"""
import os
import sys

# Add the project directory to Python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finsense.settings")

import django
django.setup()

from django.core.management import execute_from_command_line

if __name__ == "__main__":
    execute_from_command_line(["manage.py", "migrate"])

