from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from bot.config import settings


engine = create_engine(url=settings.DATABASE_URL_psycopg, echo=True)

session = scoped_session(sessionmaker(engine))
