from sqlalchemy import Column, Integer, String, Sequence, Boolean
from db.entities import Base


class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    twitter_handle = Column(String(255))
    is_verified_user = Column(Boolean)
    unique_id = Column(String(50))
    discord_user_id = Column(String(50))
    users_guild_id = Column(String(50))

    def __repr__(self):
        return "<User(twitter_handle='%s', " \
               "is_verified_user='%s', " \
               "unique_id='%s', " \
               "discord_user_id='%s', " \
               "users_guild_id='%s')>" % (
                                self.twitter_handle, self.is_verified_user, self.unique_id, self.discord_user_id,
                                self.users_guild_id)
