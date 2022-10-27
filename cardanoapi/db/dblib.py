from configparser import ConfigParser
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


def config(config_path: str, section: str) -> dict:
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(config_path)

    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, config_path))

    return db

""" Connect to the PostgreSQL database server using SQLAlchemy method """
# read connection parameters
params = config('./config.ini', section='postgresql')

# connect to the PostgreSQL server
print('Connecting to the PostgreSQL database...')
conn_string = f"postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['database']}"
engine = create_engine(conn_string, connect_args={}, future=True, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()
connection = engine.connect()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()