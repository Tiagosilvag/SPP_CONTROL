import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "spp-control-dev-secret-key")
    DATABASE_URL = os.environ.get("DATABASE_URL")
    SISTEMA_NOME = "SPP - Control"
