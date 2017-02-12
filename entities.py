import re 
import bs4
import json
from datetime import datetime
from dateutil import parser

class HipChatUser(object):
    def __init__(self, id = None, name = None, created = None,
            email = None, group = None, is_deleted = None, is_group_admin = None,
            is_guest = None, last_active = None, links = None, mention_name = None,
            photo_url = None, presence = None, timezone = None, title = None, 
            version = None, xmpp_jid = None):
        self.id = id
        self.name = name

class Category(object):
    def __init__(self, id, title, created_at, updated_at, clues_count):
        self.id = id
        self.title = title
        self.created_at = created_at
        self.updated_at = updated_at
        self.clues_count = clues_count

class Question(object):
    def __init__(self, id, answer = None, question = None, airdate = None, created_at = None, 
        updated_at = None, category_id = None, game_id = None, invalid_count = None, category = None,
        value = 200, expiration = None):
        self.id = id
        soup = bs4.BeautifulSoup(answer, "html.parser")
        self.answer = soup.get_text().replace('\\', '')
        self.question = question
        if value is None or value == "":
            value = 200
        self.value = value
        if airdate == None:
            airdate = "9/10/1984" # First airdate of Jeopardy!
        self.airdate = parser.parse(airdate)
        self.created_at = created_at
        self.updated_at = updated_at
        self.category_id = category_id
        self.game_id = game_id
        self.invalid_count = invalid_count
        self.category = Category(**category)
        self.expiration = expiration

class QuestionEncoder(json.JSONEncoder):
    def default(self, obj):
        # if not isinstance(obj, Question):
        #     return super(QuestionEncoder, self).default(obj)
        # elif not isinstance(obj, Category):
        #     return super(QuestionEncoder, self).default(obj)

        if isinstance(obj, datetime):
            return obj.isoformat()

        return obj.__dict__

class HipChatFromUser(object):
    def __init__(self, from_user):
        self.id = from_user["id"]
        self.name = from_user["name"]

class HipChatMessage(object):
    def __init__(self, jsonDict):
        self.user_from = HipChatFromUser(jsonDict["from"])
        self.message = re.sub('/trebek ', '', jsonDict["message"])

class HipChatRoom(object):
    def __init__(self, roomDict):
        self.room_id = roomDict["id"]
        self.links = roomDict["links"]

class HipChatMessageItem(object):
    def __init__(self, message = None, room = None):
        self.message = HipChatMessage(message)
        self.room = HipChatRoom(room)

class HipChatRoomMessage(object):
    def __init__(self, event = None, item = None, oauth_client_id = None, webhook_id = None):
        self.event = event
        self.item = HipChatMessageItem(**item)
        self.oauth_client_id = oauth_client_id
        self.webhook_id = webhook_id

    def __repr__(self):
        return self.item.message.message

class SlackMessage(object):
    """ Example Json passed to Class:
    token=gIkuvaNzQIHg97ATvDxqgjtO
    team_id=T0001
    team_domain=example
    channel_id=C2147483705
    channel_name=test
    user_id=U2147483697
    user_name=Steve
    command=/weather
    text=94070
    response_url=https://hooks.slack.com/commands/1234/5678
    """

    def __init__(self, *slack_json, **kwargs):
        for dictionary in slack_json:
            for key in dictionary.keys():
                setattr(self, key, dictionary[key])

        for key in kwargs:
            setattr(self, key, kwargs[key])

class TrebekMessage(object):
    # message = None
    # user_id = None
    # room_id = None
    # user_name = None

    def __init__(self, *slack_json, **kwargs):
        """
        Accept arbitrary dictionary to support either Slack or HipChat
        Call an "assign" method below to set the above properties
        for use in the actual Trebek bot
        """
        for dictionary in slack_json:
            for key in dictionary.keys():
                setattr(self, key, dictionary[key])

        for key in kwargs:
            setattr(self, key, kwargs[key])

    def assign_from_slack(self):
        """ Example Json passed to Class:
        token=gIkuvaNzQIHg97ATvDxqgjtO
        team_id=T0001
        team_domain=example
        channel_id=C2147483705
        channel_name=test
        user_id=U2147483697
        user_name=Steve
        command=/weather
        text=94070
        response_url=https://hooks.slack.com/commands/1234/5678
        """
        self.room_id = self.channel_id
        self.message = self.text

