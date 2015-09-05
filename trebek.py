import redis
import bs4
import re
import difflib
import time
import requests
import json
import entities
from bottle import route, run, template, request
from urllib.parse import urlparse
import os 

# trebek jeopardy: starts a round of Jeopardy! trebekbot will pick a category and score for you.
# trebek what/who is/are [answer]: sends an answer. Remember, responses must be in the form of a question!
# trebek score: shows your current score.
# trebek leaderboard: shows the current top scores.
# trebek loserboard: shows the current bottom scores.
# trebek help: shows this help information.


class Trebek:
    clue_key = "activeClue:{0}"
    hipchat_user_key = "hipchat_user:{0}"
    user_score_key = "user_score:{0}"
    user_score_scan_key = "user_score:*"
    user_score_regex_key = "user_score:"
    board_limit = 5


    def __init__(self, room_message = None):
        # TODO - Make this variable configurable
        self.seconds_to_expire = 30
        uri = urlparse(os.environ.get('REDIS_URL'))
        self.redis = redis.StrictRedis(host = uri.hostname, 
                port = uri.port, password = uri.password)
        self.room_message = room_message
        self.room_id = self.room_message.item.room.room_id

    def get_active_clue(self, key):
        obj = None
        if key.startswith(self.clue_key[:4]):
            o = self.redis.get(key)
            obj = entities.Question(**json.loads(o.decode()))

        return obj

    def parse_message(self):
        cmd = self.room_message.item.message.message
        self.save_hipchat_user()
        if re.match('^jeopardy*', cmd):
            response = self.respond_with_question()
        elif re.match('my score$', cmd):
            response = self.respond_with_user_score()
        elif re.match('^help$', cmd):
            response = self.respond_with_help()
        elif re.match('^show (me\s+)?(the\s+)?leaderboard$', cmd):
            response = self.respond_with_leaderboard()
        elif re.match('^show (me\s+)?(the\s+)?loserboard$', cmd):
            response = self.respond_with_loserboard()
        else:
            response = self.process_answer()

        return response

    def save_hipchat_user(self):
        key = self.hipchat_user_key.format(self.room_message.item.message.user_from.id)
        if not self.redis.exists(key):
            self.redis.set(key, self.room_message.item.message.user_from.name)

    def respond_with_question(self):
        # TODO: Format currency in all places
        message = ""
        key = self.clue_key.format(self.room_id) 
        if self.redis.exists(key):
            print(self.can_start_new_round())
            if self.can_start_new_round():
                message = "The answer was: {0}\n".format(self[key].answer)
                clue = self.start_jeopardy()
                message += "The category is `{0}` for {1}: {2}".format(clue.category.title, clue.value, clue.question)
            else:
                message = "Round in progress, cannot start a new Jeopardy round."
            
        return message

    def process_answer(self):
        """ Command that will parse and process any response from the user.
        """
        key = self.clue_key.format(self.room_id) 
        if key not in self.redis:
            return self.trebek_me()

        response = ""
        clue = self[key]
        correct_answer = self.is_correct_answer(clue.answer, args)
        if clue.expiration < time.time():
            if correct_answer:
                response = "That is correct, however time is up."
            else:
                response = "Time is up! The correct answer was: `{0}`".format(clue.answer)
            self.mark_question_as_answered()
        elif self.response_is_a_question(args) and correct_answer:
            # TODO: Update score calculation here - Positive amount
            response = "That is correct!"
            self.mark_question_as_answered()
        elif correct_answer:
            # TODO: Update score calculation here - negative amount
            response = "That is correct, however responses should be in the form of a question"
            clue.expiration = time.time() + self.seconds_to_expire
            self[key] = clue
        else:
            # TODO: Update Score - negative amount
            response = "That is incorrect."
            clue.expiration = time.time() + self.seconds_to_expire
            self[key] = clue

        return response
        
    def mark_question_as_answered(self):
        del self[self.clue_key.format(self.room_id)]

    def can_start_new_round(self):
        key = self.clue_key.format(self.room_id)
        question = self.get_active_clue(key)
        if question != None and question.expiration > time.time():
            return False

        return True

    def start_jeopardy(self):
        key = self.clue_key.format(self.room_id)
        clue = self.fetch_random_clue()
        clue.expiration = time.time() + self.seconds_to_expire
        json_data = json.dumps(clue, cls=entities.QuestionEncoder)
        self.redis.set(key, json_data)
        return clue

    def fetch_random_clue(self):
        url = "http://jservice.io/api/random?count=1"
        req = requests.get(url)
        print(req.json()[0]['answer'])
        return entities.Question(**req.json()[0])

    def response_is_a_question(self, response):
        return re.match("^(what|whats|where|wheres|who|whos)", response.strip())

    def is_correct_answer(self, expected, actual):
        expected = re.sub(r'[^\w\s]', "", expected, flags=re.I)
        expected = re.sub(r'^(the|a|an) ', "", expected, flags=re.I)
        expected = expected.strip().lower()

        actual = re.sub(r'\s+(&nbsp;|&)\s+', " and ", actual, flags=re.I)
        actual = re.sub(r'[^\w\s]', "", actual, flags=re.I) 
        actual = re.sub(r'^(what|whats|where|wheres|who|whos) ', "", actual, flags=re.I) 
        actual = re.sub(r'^(is|are|was|were) ', "", actual, flags=re.I) 
        actual = re.sub(r'^(the|a|an) ', "", actual, flags=re.I) 
        actual = re.sub(r'\?+$/', "", actual, flags=re.I) 
        actual = actual.strip().lower()

        seq = difflib.SequenceMatcher(a = expected, b = actual)

        # print("Expected: {0} - Actual: {1} - Ratio: {2}".format(expected, actual, seq.ratio()))
        # TODO: Make this ratio confgurable
        return seq.ratio() >= 0.85

    def get_user_name(self, user_id):
        key = self.hipchat_user_key.format(user_id)
        return self.redis.get(key).decode()

    def get_loserboard(self):
        # TODO: Format currency
        losers = {}
        for score_key in self.redis.scan_iter(match=self.user_score_scan_key):
            user_id = re.sub(self.user_score_regex_key, '', score_key.decode())
            losers[user_id] = self.redis.get(score_key).decode()

        loser_board = ""
        sorted_losers = sorted(losers.items(), key=lambda x: int(x[1]))
        return self.get_formatted_board(sorted_losers)

    def get_leaderboard(self):
        # TODO: Format currency
        leaders = {}
        for score_key in self.redis.scan_iter(match=self.user_score_scan_key):
            user_id = re.sub(self.user_score_regex_key, '', score_key.decode())
            leaders[user_id] = self.redis.get(score_key).decode()

        sorted_leaders = sorted(leaders.items(), reverse = True, key=lambda x: int(x[1]))
        return self.get_formatted_board(sorted_leaders)

    def get_formatted_board(self, sorted_board):
        board = ""
        for i, user in enumerate(sorted_board):
            board += '{0}. {1} - {2}\n'.format(i + 1, self.get_user_name(user[0]), user[1])
            if i + 1 >= self.board_limit:
                break

        return board
            

    # Funny quotes from SNL's Celebrity Jeopardy, to speak
    # when someone invokes trebekbot and there's no active round.
    # 
    def trebek_me(self):
        quotes = [ 
            "Welcome back to HipChat Jeopardy. Before we begin this Jeopardy round, I'd like to ask our contestants once again to please refrain from using ethnic slurs.",
            "Okay, Turd Ferguson.",
            "I hate my job.",
            "Let's just get this over with.",
            "Do you have an answer?",
            "I don't believe this. Where did you get that magic marker? We frisked you on the way in here.",
            "What a ride it has been, but boy, oh boy, these HipChat users did not know the right answers to any of the questions.",
            "Back off. I don't have to take that from you.",
            "That is _awful_.",
            "Okay, for the sake of tradition, let's take a look at the answers.",
            "Beautiful. Just beautiful.",
            "Good for you. Well, as always, three perfectly good charities have been deprived of money, here on HipChat Jeopardy. I'm trebekbot, and all of you should be ashamed of yourselves! Good night!",
            "And welcome back to HipChat Jeopardy. Because of what just happened before during the commercial, I'd like to apologize to all blind people and children.",
            "Thank you, thank you. Moving on.",
            "I really thought that was going to work.",
            "Wonderful. Let's take a look at the categories. They are: `Potent Potables`, `Point to your own head`, `Letters or Numbers`, `Will this hurt if you put it in your mouth`, `An album cover`, `Make any noise`, and finally, `Famous Muppet Frogs`. I should add that the answer to every question in that category is `Kermit`.",
            "For the last time, that is not a category.",
            "Unbelievable.",
            "Great. Let's take a look at the final board. And the categories are: `Potent Potables`, `Sharp Things`, `Movies That Start with the Word Jaws`, `A Petit Déjeuner` -- that category is about French phrases, so let's just skip it.",
            "Enough. Let's just get this over with. Here are the categories, they are: `Potent Potables`, `Countries Between Mexico and Canada`, `Members of Simon and Garfunkel`, `I Have a Chardonnay` -- you choose this category, you automatically get the points and I get to have a glass of wine -- `Things You Do With a Pencil Sharpener`, `Tie Your Shoe`, and finally, `Toast`.",
            "Better luck to all of you, in the next round. It's time for HipChat Jeopardy, let's take a look at the board. And the categories are: `Potent Potables`, `Literature` -- which is just a big word for books -- `Therapists`, `Current U.S. Presidents`, `Show and Tell`, `Household Objects`, and finally, `One-Letter Words`.",
            "Uh, I see. Get back to your podium.",
            "You look pretty sure of yourself. Think you've got the right answer?",
            "Welcome back to HipChat Jeopardy. We've got a real barnburner on our hands here.",
            "And welcome back to HipChat Jeopardy. I'd like to once again remind our contestants that there are proper bathroom facilities located in the studio.",
            "Welcome back to HipChat Jeopardy. Once again, I'm going to recommend that our viewers watch something else.",
            "Great. Better luck to all of you in the next round. It's time for HipChat Jeopardy. Let's take a look at the board. And the categories are: `Potent Potables`, `The Vowels`, `Presidents Who Are On the One Dollar Bill`, `Famous Titles`, `Ponies`, `The Number 10`, and finally: `Foods That End In \"Amburger\"`.",
            "Let's take a look at the board. The categories are: `Potent Potables`, `The Pen is Mightier` -- that category is all about quotes from famous authors, so you'll all probably be more comfortable with our next category -- `Shiny Objects`, continuing with `Opposites`, `Things you Shouldn't Put in Your Mouth`, `What Time is It?`, and, finally, `Months That Start With Feb`."
        ]

        import random
        return random.sample(quotes, 1)[0]

    def trebek_help(self, message, args):
        return """
!trebek jeopardy: starts a round of Jeopardy! trebekbot will pick a category and score for you.
!trebek what/who is/are [answer]: sends an answer. Remember, responses must be in the form of a question!
!trebek score: shows your current score.
!trebek leaderboard: shows the current top scores.
!trebek loserboard: shows the current bottom scores.
!trebek help: shows this help information.
"""
    # def activate(self):
    #     """Triggers on plugin activation

    #     You should delete it if you're not using it to override any default behaviour"""
    #     super(Skeleton, self).activate()

    # def deactivate(self):
    #     """Triggers on plugin deactivation

    #     You should delete it if you're not using it to override any default behaviour"""
    #     super(Skeleton, self).deactivate()

    # def get_configuration_template(self):
    #     """Defines the configuration structure this plugin supports

    #     You should delete it if your plugin doesn't use any configuration like this"""
    #     return {'EXAMPLE_KEY_1': "Example value",
    #             'EXAMPLE_KEY_2': ["Example", "Value"]
    #            }

    # def check_configuration(self, configuration):
    #     """Triggers when the configuration is checked, shortly before activation

    #     You should delete it if you're not using it to override any default behaviour"""
    #     super(Skeleton, self).check_configuration()

    # def callback_connect(self):
    #     """Triggers when bot is connected

    #     You should delete it if you're not using it to override any default behaviour"""
    #     pass

    # def callback_message(self, conn, message):
    #     """Triggered for every received message that isn't coming from the bot itself

    #     You should delete it if you're not using it to override any default behaviour"""
    #     pass

    # def callback_botmessage(self, message):
    #     """Triggered for every message that comes from the bot itself

    #     You should delete it if you're not using it to override any default behaviour"""
    #     pass

    # @webhook
    # def example_webhook(self, incoming_request):
    #     """A webhook which simply returns 'Example'"""
    #     return "Example"

    # # Passing split_args_with=None will cause arguments to be split on any kind
    # # of whitespace, just like Python's split() does
    # @botcmd(split_args_with=None)
    # def example(self, mess, args):
    #     """A command which simply returns 'Example'"""
    #     return "Example"

@route ("/", method='POST')
def index():
    msg = entities.HipChatRoomMessage(**request.json)
    trebek = Trebek(msg)
    parameters = {}
    parameters['from'] = 'trebek'
    parameters['room_id'] = msg.item.room.room_id 
    parameters['message'] = trebek.response
    parameters['color'] = 'gray'
    return json.dumps(parameters)

if __name__ == "__main__":
    run (host='localhost', port=8080, reloader=True)
