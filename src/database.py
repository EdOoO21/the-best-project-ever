from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import URL, create_engine, text
from bot import config

engine = create_engine(
    url=config.settings.DATABASE_URL_psycopg,
    echo=True
)