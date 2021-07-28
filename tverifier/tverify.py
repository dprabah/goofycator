import os

import tweepy
from tweepy import OAuthHandler

auth = OAuthHandler(os.getenv('consumer_key'), os.getenv('consumer_secret'))
auth.set_access_token(os.getenv('access_key'), os.getenv('access_secret'))
api = tweepy.API(auth)


def verify_twitter_handle(handle=""):
    print("verify_twitter_handle: {}".format(handle))
    try:
        api.get_user(handle)
        return True
    except tweepy.TweepError as e:
        print(e)
        return False


def get_twitter_dms():
    dms = api.list_direct_messages()
    print("get_twitter_dms: {}".format(len(dms)))
    return dms


def get_screen_name_by_id(twitter_id: int):
    return "@" + str(api.get_user(twitter_id).screen_name).lower()


def delete_message_by_id(message_id):
    api.destroy_direct_message(message_id)


def get_own_screen_name():
    return '@' + api.verify_credentials().screen_name


def get_own_screen_id():
    return str(api.verify_credentials().id)
