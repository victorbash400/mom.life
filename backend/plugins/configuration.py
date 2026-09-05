import os
from pathlib import Path

from dotenv import dotenv_values


def setting(name):
    value = os.getenv(name)
    if value is not None:
        return value
    return dotenv_values(Path(__file__).resolve().parents[1]/'.env').get(name)
