import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


def create_session():
    schema = os.getenv('db_url')
    engine = create_engine(schema, echo=False)

    b = GetBase("Utils")
    b.set_base(declarative_base())

    base = b.get_base()
    base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)
    return session()


class GetBase(object):
    __single = None  # the one, true Singleton
    __base = None
    __text = None

    def __new__(cls, *args, **kwargs):
        # Check to see if a __single exists already for this class
        # Compare class types instead of just looking for None so
        # that subclasses will create their own __single objects
        if cls != type(cls.__single):
            cls.__single = object.__new__(cls)
            __base = declarative_base()

        return cls.__single

    def __init__(self, name=None):
        self.name = name

    def get_base(self):
        return self.__base

    def set_base(self, value):
        self.__base = value
