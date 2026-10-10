from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

Base = declarative_base()
engine = None
db_session = None

def init_db(app):
    global engine, db_session
    engine = create_engine(
        app.config["SQLALCHEMY_DATABASE_URI"],
        pool_pre_ping=True,
        echo=False
    )
    db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    Base.query = db_session.query_property()

    # Import models to register them on Base
    from . import models

    Base.metadata.create_all(bind=engine)
    return db_session

def get_db():
    return db_session
