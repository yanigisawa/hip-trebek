class HipChatFile(object):
    def __init__(self, name = None, size = None, thumb_url = None, url = None):
        self.name = name
        self.size = size
        self.thumb_url = thumb_url
        self.url = url

class HipChatMessage(object):
    def __init__(self, date = None, file = None, id = None, mentions = None, message = None, message_links = None, type = none):
        self.date = date
        self.file = HipChatFile(**file)
        self.id = id
        self.mentions = mentions
        self.message = message
        self.message_links = message_links
        self.type = type

class HipChatLinks(object):
    def __init__(self, members = None, participants = None, self = None, webhooks = None):
        pass

class HipChatRoom(object):
    def __init__(self, id = None, links = None):
        self.id = id
        self.links = links

class HipChatMessageItem(object):
    def __init__(self, message = None, room = None):
        self.message = HipChatMessage(**message)
        self.room = HipChatRoom(**room)

class HipChatRoomMessage(object):
    def __init__(self, event = None, item = None, oauth_client_id = None, webhook_id = None):
        self.event = event
        self.item = HipChatMessageItem(**item)
        self.oauth_client_id = oauth_client_id
        self.webhook_id = webhook_id



