from errbot import BotPlugin, botcmd
from errbot.builtins.webserver import webhook
import redis
import bs4
import re
import difflib
import time
import requests


# trebekbot jeopardy: starts a round of Jeopardy! trebekbot will pick a category and score for you.
# trebekbot what/who is/are [answer]: sends an answer. Remember, responses must be in the form of a question!
# trebekbot score: shows your current score.
# trebekbot leaderboard: shows the current top scores.
# trebekbot loserboard: shows the current bottom scores.
# trebekbot help: shows this help information.

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
        value = 200):
        self.id = id
        soup = bs4.BeautifulSoup(answer, "html.parser")
        self.answer = soup.findAll(text=True)[0].replace('\\', '')
        self.question = question
        self.value = value
        self.airdate = airdate
        self.created_at = created_at
        self.updated_at = updated_at
        self.category_id = category_id
        self.game_id = game_id
        self.invalid_count = invalid_count
        self.category = Category(**category)

class Trebek(BotPlugin):
    """An Err plugin skeleton"""
    min_err_version = '2.2.1' # Optional, but recommended
    max_err_version = '2.2.1' # Optional, but recommended

    def __init__(self):
        # TODO - Make this variable configurable
        self.seconds_to_expire = 30
        super(Trebek, self).__init__()

    @botcmd
    def trebek_jeopardy(self, message, args):

        message = ""
        if 'activeClue' in self:
            if self.can_start_new_round():
                message = "The answer was: {0}\n".format(self['activeClue'].answer)
            else:
                return "Round in progress, cannot start a new Jeopardy round."


        clue = self.start_jeopardy()
        message += "The category is `{0}` for {1}: {2}".format(clue.category.title, clue.value, clue.question)
            
        return message

    @botcmd
    def trebek(self, message, args):
        """ Command that will parse and process any response from the user.
        """
        if 'activeClue' not in self:
            return self.trebek_me()

        response = ""
        clue = self['activeClue']
        correct_answer = self.is_correct_answer(clue.answer, args)
        if clue.expiration < time.time():
            if correct_answer:
                response = "That is correct, however time is up."
            else:
                response = "Time is up! The correct answer was: `{0}`".format(clue.answer)
        elif self.response_is_a_question(args) and correct_answer:
            # TODO: Update score calculation here - Positive amount
            response = "That is correct!"
            self.mark_question_as_answered()
        elif correct_answer:
            # TODO: Update score calculation here - negative amount
            response = "That is correct, however responses should be in the form of a question"
            clue.expiration = time.time() + self.seconds_to_expire
            self['activeClue'] = clue
        else:
            # TODO: Update Score - negative amount
            response = "That is incorrect."
            clue.expiration = time.time() + self.seconds_to_expire
            self['activeClue'] = clue

        return response
        
    def mark_question_as_answered(self):
        del self['activeClue']

    def can_start_new_round(self):
        key = 'activeClue'
        if key in self and self[key].expiration > time.time():
            return False

        return True

    def get_channel_id(self):
        # TODO - Actually get the channel ID from HipChat
        return "1"
        

    def start_jeopardy(self):
        key = "activeRound:{0}".format(self.get_channel_id())
        self[key] = True
        clue = self.get_random_clue()
        clue.expiration = time.time() + self.seconds_to_expire
        self['activeClue'] = clue
        return clue

    def fetch_random_clue(self):
        url = "http://jservice.io/api/random?count=1"
        req = requests.get(url)
        print(req.json()[0]['answer'])
        return Question(**req.json()[0])

    def get_random_clue(self):
        clue = self.fetch_random_clue()
        if clue.value == None:
            clue.value = 200

        return clue

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

    def clear_storage(self):
        for key in list(self.keys()):
            del self[key]


    # Funny quotes from SNL's Celebrity Jeopardy, to speak
    # when someone invokes trebekbot and there's no active round.
    # 
    def trebek_me(self):
        quotes = quotes = [ "Welcome back to HipChat Jeopardy. Before we begin this Jeopardy round, I'd like to ask our contestants once again to please refrain from using ethnic slurs.",
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
            "Good for you. Well, as always, three perfectly good charities have been deprived of money, here on HipChat Jeopardy. I'm trebekBot, and all of you should be ashamed of yourselves! Good night!",
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

    @botcmd
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

