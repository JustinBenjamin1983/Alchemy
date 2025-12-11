import os
import logging
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

engine = create_engine(os.environ["DB_CONNECTION_STRING"], echo=True)
SessionLocal = sessionmaker(bind=engine)

@contextmanager
def transactional_session():    
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logging.error("SQLAlchemy error during transaction")
        logging.exception("SQLAlchemy error during transaction")
        raise
    except Exception as e:
        session.rollback()
        logging.error("Unexpected error during transaction")
        logging.exception("Unexpected error during transaction")
        raise
    finally:
        session.close()