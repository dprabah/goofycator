from sqlalchemy.orm import declarative_base

from db.connection import GetBase

b = GetBase("Users")
b.set_base(declarative_base())
Base = b.get_base()
