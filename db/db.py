from tinydb import TinyDB

from db.connection import create_session
from db.entities.Users import Users


def create_and_return_db(name, table_name):
    return TinyDB('dbs/' + name + '.json').table(table_name)


def connect_test():
    session = create_session()

    result = session.query(Users).all()
    for r in result:
        print(r)
