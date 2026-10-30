#!/usr/bin/env python
import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def main():
    import dotenv  # django-dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bilimkg.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
