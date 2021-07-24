from tinydb import TinyDB


def create_and_return_db(name, table_name):
    return TinyDB('dbs/' + name + '.json').table(table_name)
