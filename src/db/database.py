from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from bot.config import settings

engine = create_engine(url=settings.DATABASE_URL_psycopg, echo=True)

session = scoped_session(sessionmaker(engine))
