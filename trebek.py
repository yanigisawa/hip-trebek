import redis
import bs4
import re
import difflib
import time
import requests
import json
import entities
from bottle import route, run, template, request, response
from urllib.parse import urlparse
import os 
from threading import Timer

# trebek jeopardy: starts a round of Jeopardy! trebekbot will pick a category and score for you.
# trebek what/who is/are [answer]: sends an answer. Remember, responses must be in the form of a question!
# trebek score: shows your current score.
# trebek leaderboard: shows the current top scores.
# trebek loserboard: shows the current bottom scores.
# trebek help: shows this help information.

# Environment Variable Keys
_auth_header = "AUTH_HEADER"
_board_limit = "BOARD_LIMIT"
_answer_match_ratio = "ANSWER_MATCH_RATIO"
_secods_to_expire = "SECONDS_TO_EXPIRE"
_redis_url = "REDIS_URL"
_hipchat_auth_token = "HIPCHAT_AUTH_TOKEN"
_timer = None
_unit_test = "UNIT_TEST"

def notify_answer(room_id, clue_id):
    global _timer
    _timer.cancel()
    url = "https://api.hipchat.com/v1/rooms/message?auth_token={1}".format(
            room_id, os.environ.get(_hipchat_auth_token))

    key = Trebek.clue_key.format(room_id)

    uri = urlparse(os.environ.get(_redis_url))
    r = redis.StrictRedis(host = uri.hostname, 
            port = uri.port, password = uri.password)
    if r.exists(key):
        o = r.get(key)
        obj = entities.Question(**json.loads(o.decode()))
        if obj.id == clue_id:
            r.delete(key)
            parameters = {}
            parameters['message'] = "The answer was: {0}".format(obj.answer)
            parameters['room_id'] = room_id
            parameters['color'] = 'gray'
            parameters['from'] = 'Trebek'
            resp = requests.post(url, data = parameters, timeout=5)
            if resp.status_code != 200:
                print('failed to post message to hipchat')
    else:
        print('no redis key exists, do not notify')

class Trebek:
    clue_key = "activeClue:{0}"
    hipchat_user_key = "hipchat_user:{0}"
    user_score_key = "user_score:{0}"
    user_score_scan_key = "user_score:*"
    user_score_regex_key = "user_score:"
    shush_key = "shush:{0}"
    shush_answer_key = "shush:answer:{0}"
    user_answer_key = "user_answer:{0}:{1}:{2}"
    board_limit = int(os.environ.get(_board_limit))
    answer_match_ratio = float(os.environ.get(_answer_match_ratio))
    seconds_to_expire = int(os.environ.get(_secods_to_expire))

    def __init__(self, room_message = None):
        uri = urlparse(os.environ.get(_redis_url))
        self.redis = redis.StrictRedis(host = uri.hostname, 
                port = uri.port, password = uri.password)
        self.room_message = room_message
        self.room_id = self.room_message.item.room.room_id

    def get_active_clue(self):
        key = self.clue_key.format(self.room_id)
        obj = None
        if self.redis.exists(key):
            o = self.redis.get(key)
            obj = entities.Question(**json.loads(o.decode()))

        return obj

    def get_response_message(self):
        cmd = self.room_message.item.message.message
        self.save_hipchat_user()
        if re.match('^jeopardy*', cmd):
            response = self.get_question()
        elif re.match('^score$', cmd):
            response = self.get_user_score()
        elif re.match('^help$', cmd):
            response = self.get_help()
        elif re.match('^answer$', cmd):
            response = self.get_answer()
        elif re.match('^(show\s+)?(me\s+)?(the\s+)?leaderboard$', cmd):
            response = self.get_leaderboard()
        elif re.match('^(show\s+)?(me\s+)?(the\s+)?loserboard$', cmd):
            response = self.get_loserboard()
        elif re.match('^invalid', cmd):
            response = self.post_clue_invalid()
        else:
            response = self.process_answer()

        return response

    def post_clue_invalid(self):
        clue = self.get_active_clue()
        url = "http://jservice.io/api/invalid?id={0}".format(clue.id)
        resp = requests.post(url)
        response = "Failed to Post Invalid Question"
        if resp.status_code == 200:
            response = "Submitted question as invalid. Invalid Count: {0}".format(resp.json()['invalid_count']) 

        return response

    def get_user_score(self):
        key = self.user_score_key.format(self.room_message.item.message.user_from.id)
        if self.redis.exists(key):
            score = int(self.redis.get(key).decode())
        else:
            score = 0
        return self.format_currency(score)

    def save_hipchat_user(self):
        key = self.hipchat_user_key.format(self.room_message.item.message.user_from.id)
        if not self.redis.exists(key):
            self.redis.set(key, self.room_message.item.message.user_from.name)

    def get_question(self):
        message = ""
        key = self.clue_key.format(self.room_id) 
        shush_key = self.shush_key.format(self.room_id)
        if not self.redis.exists(shush_key):
            if self.redis.exists(key):
                active_clue = self.get_active_clue()
                message = "The answer was: <b>{0}</b><br/>".format(active_clue.answer)
            clue = self.get_jeopardy_clue()
            message += "The category is <b>{0}</b> for {1}: <b>{2}</b>".format(clue.category.title.upper(), 
                    self.format_currency(clue.value), clue.question.upper())
            
            pipe = self.redis.pipeline()
            pipe.set(key, json.dumps(clue, cls=entities.QuestionEncoder))
            pipe.setex(shush_key, 5, 'true')
            pipe.execute()
            if not os.environ.get(_unit_test):
                global _timer
                _timer = Timer(self.seconds_to_expire, notify_answer, args = [self.room_id, clue.id])
                _timer.start()
             
        return message

    def get_answer(self):
        clue = self.get_active_clue()
        if clue == None:
            response = "No active clue. Type '/trebek jeopardy' to start a round"
        else:
            response = 'The answer was: {0}'.format(clue.answer)
            self.mark_question_as_answered()
        return response

    def process_answer(self):
        """ Command that will parse and process any response from the user.
        """
        key = self.clue_key.format(self.room_id) 
        shush_answer = self.shush_answer_key.format(self.room_id)
        clue = self.get_active_clue()
        if clue == None and not self.redis.exists(shush_answer):
            return self.trebek_me()
        elif clue == None:
            return None

        response = ""
        user_answer = self.room_message.item.message.message
        correct_answer = self.is_correct_answer(clue.answer, user_answer)
        user_answer_key = self.user_answer_key.format(self.room_id,
                clue.id, self.room_message.item.message.user_from.id)

        hipchat_user_name = self.room_message.item.message.user_from.name
        if self.redis.exists(user_answer_key):
            response = "You have already answered {0}. Let someone else respond.".format(hipchat_user_name)
        elif clue.expiration < time.time():
            if correct_answer:
                response = "That is correct {0}, however time is up. (Expected Answer: {1})".format(hipchat_user_name, clue.answer)
            else:
                response = "Time is up! The correct answer was: <b>{0}</b>".format(clue.answer)
            self.mark_question_as_answered()
        elif self.response_is_a_question(user_answer) and correct_answer:
            score = self.update_score(clue.value)
            response = "That is correct, {0}. Your score is now {1} (Expected Answer: {2})".format(
                    hipchat_user_name, self.format_currency(score), clue.answer)
            self.mark_question_as_answered()
        elif correct_answer:
            score = self.update_score(-clue.value)
            response = "That is correct {0}, however responses should be in the form of a question.".format(hipchat_user_name)
            response += " Your score is now {0}".format(self.format_currency(score))
            clue.expiration = time.time() + self.seconds_to_expire
            self.redis.setex(user_answer_key, self.seconds_to_expire, 'true')
        else:
            score = self.update_score(-clue.value)
            response = "That is incorrect, {0}. Your score is now {1}".format(hipchat_user_name, self.format_currency(score))
            clue.expiration = time.time() + self.seconds_to_expire
            self.redis.setex(user_answer_key, self.seconds_to_expire, 'true')

        return response
        
    def mark_question_as_answered(self):
        pipe = self.redis.pipeline()
        pipe.delete(self.clue_key.format(self.room_id))
        pipe.delete(self.shush_key.format(self.room_id))
        pipe.setex(self.shush_answer_key.format(self.room_id), 5, 'true')
        pipe.execute()

    def update_score(self, score = 0):
        key = self.user_score_key.format(self.room_message.item.message.user_from.id)
        old_score = 0
        if self.redis.exists(key):
            old_score = int(self.redis.get(key))

        new_score = old_score + score
        self.redis.set(key, new_score)
        return new_score

    def get_jeopardy_clue(self):
        key = self.clue_key.format(self.room_id)
        clue = self.fetch_random_clue()
        while not self.is_valid_clue(clue):
            clue = self.fetch_random_clue()
        clue.expiration = time.time() + self.seconds_to_expire
        return clue

    def is_valid_clue(self, clue):
        valid = clue.invalid_count == None and clue.question.strip() != ""
        if valid:
            valid = "seen here" not in clue.question.lower()

        if valid:
            valid = "heard here" not in clue.question.lower()

        return valid

    def fetch_random_clue(self):
        url = "http://jservice.io/api/random?count=1"
        req = requests.get(url)
        # print(req.json())
        print("ANSWER: {0}".format(req.json()[0]['answer']))
        return entities.Question(**req.json()[0])

    def response_is_a_question(self, response):
        return re.match("^(what|whats|where|wheres|who|whos)", response.lower().strip())

    def clean_expected_answer(self, expected):
        expected = re.sub(r'[^\w\s]', "", expected, flags=re.I)
        expected = re.sub(r'^(the|a|an|or) ', "", expected, flags=re.I)
        return expected.strip().lower()

    def compare_answers(self, expected, actual):
        seq = difflib.SequenceMatcher(a = expected, b = actual)
        print("Expected: {0} - Actual: {1} - Ratio: {2}".format(expected, actual, seq.ratio()))
        return seq.ratio() >= self.answer_match_ratio

    def is_correct_answer(self, expected, actual):
        expected_orig = expected
        expected = self.clean_expected_answer(expected)
        expected = expected.strip().lower()

        actual = re.sub(r'\s+(&nbsp;|&)\s+', " and ", actual, flags=re.I)
        actual = re.sub(r'[^\w\s]', "", actual, flags=re.I) 
        actual = re.sub(r'^(what|whats|where|wheres|who|whos) ', "", actual, flags=re.I) 
        actual = re.sub(r'^(is|are|was|were) ', "", actual, flags=re.I) 
        actual = re.sub(r'^(the|a|an) ', "", actual, flags=re.I) 
        actual = re.sub(r'\?+$/', "", actual, flags=re.I) 
        actual = actual.strip().lower()

        is_correct = self.compare_answers(expected, actual)
        if not is_correct:
            # see unit tests for examples. Handles answers with "this (or that)" structure
            parens_group = re.match(r"(.*)(\(.+\))(.*)", expected_orig)
            if parens_group:
                # if there is an alternate, compare alternate answer
                if "or" in parens_group.group(2):
                    expected = self.clean_expected_answer(parens_group.group(2))
                    is_correct = self.compare_answers(expected, actual)

                if not is_correct:
                    expected = self.clean_expected_answer(expected_orig.replace(parens_group.group(2), ""))
                    is_correct = self.compare_answers(expected, actual)

        return is_correct

    def get_user_name(self, user_id):
        key = self.hipchat_user_key.format(user_id)
        return self.redis.get(key).decode()

    def get_loserboard(self):
        losers = {}
        for score_key in self.redis.scan_iter(match=self.user_score_scan_key):
            user_id = re.sub(self.user_score_regex_key, '', score_key.decode())
            losers[user_id] = self.redis.get(score_key).decode()

        loser_board = ""
        sorted_losers = sorted(losers.items(), key=lambda x: int(x[1]))
        return self.get_formatted_board(sorted_losers)

    def get_leaderboard(self):
        leaders = {}
        for score_key in self.redis.scan_iter(match=self.user_score_scan_key):
            user_id = re.sub(self.user_score_regex_key, '', score_key.decode())
            leaders[user_id] = self.redis.get(score_key).decode()

        sorted_leaders = sorted(leaders.items(), reverse = True, key=lambda x: int(x[1]))
        return self.get_formatted_board(sorted_leaders)

    def get_formatted_board(self, sorted_board):
        board = "<ol>"
        for i, user in enumerate(sorted_board):
            board += '<li>{0}: {1}</li>'.format(self.get_user_name(user[0]), self.format_currency(user[1]))
            if i + 1 >= self.board_limit: break

        board += "</ol>"
        return board
            
    def format_currency(self, string_value):
        prefix = "$"
        score = int(string_value)
        score_string = ""
        if score < 0:
            score_string = "<span style='color: red;'>-${0}</span>".format(
                    format(abs(score), ','))
        else:
            score_string = "${0}".format(format(score, ','))
        return score_string # prefix + format(abs(int(string_value)), ',')


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
            "Uh, I see that. Get back to your podium. What is going on?",
            "You look pretty sure of yourself. Think you've got the right answer?",
            "Welcome back to HipChat Jeopardy. We've got a real barnburner on our hands here.",
            "And welcome back to HipChat Jeopardy. I'd like to once again remind our contestants that there are proper bathroom facilities located in the studio.",
            "Welcome back to HipChat Jeopardy. Once again, I'm going to recommend that our viewers watch something else.",
            "Great. Better luck to all of you in the next round. It's time for HipChat Jeopardy. Let's take a look at the board. And the categories are: `Potent Potables`, `The Vowels`, `Presidents Who Are On the One Dollar Bill`, `Famous Titles`, `Ponies`, `The Number 10`, and finally: `Foods That End In \"Amburger\"`.",
            "Let's take a look at the board. The categories are: `Potent Potables`, `The Pen is Mightier` -- that category is all about quotes from famous authors, so you'll all probably be more comfortable with our next category -- `Shiny Objects`, continuing with `Opposites`, `Things you Shouldn't Put in Your Mouth`, `What Time is It?`, and, finally, `Months That Start With Feb`.",
            "I don't know how anyone can get $8, but better luck to you all in the next round",
            "Let's move onto final Jeopardy! Where the category is `Horsies",
            "We haven't started playing yet...",
            "Let's skip therapists and move onto house-hold objects...",
            "...And the show has reached, a new low.",
            "...and, you're an idiot",
            "As usual, three perfectly good charities have been deprived of money here on HipChat jeopardy.",
            "I feel like I want to punch you",
            "Apparently Mr. Reynolds has changed his name to Turd Ferguson",
            "Welcome back to HipChat Jeopardy! You may notice that I'm wearing a different suit. Apparently, Mr. Connery thought my leg was closer than the urinal",
            "Welcome back to HipChat Jeopardy! I want to apologize to everyone watching before the break, and want to assure you that all three contestants are wearing pants.",
            "Let's take a look at the board. The categories are: Continents, Theatre, Potpourri, Potent Potables, Numbers, Words that Rhyme with Dog, and finally, the Renaissance. And you know what, let's just change that last category, to Shapes."
            "Now let's take a look at the categories for final Jeopardy! `Potent Potables, `Drummers Named Ringo`, `States that begin with 'Californ'`, `Richard Nixon`, `The number after 2`, `Famous Kareem Abdul-Jabbars`, and finally: `Don't Do Anything`"
        ]

        import random
        return random.sample(quotes, 1)[0]

    def get_help(self):
        return """<ul>
<li>/trebek jeopardy: starts a round of Jeopardy! trebekbot will pick a category and score for you.</li>
<li>/trebek what/who is/are [answer]: sends an answer. Remember, responses must be in the form of a question!</li>
<li>/trebek score: shows your current score.</li>
<li>/trebek leaderboard: shows the current top scores.</li>
<li>/trebek loserboard: shows the current bottom scores.</li>
<li>/trebek answer: shows the answer to the previous round.</li>
<li>/trebek invalid: submits the active question as invalid to the underlying jservice. See http://jservice.io for more information</li>
<li>/trebek help: shows this help information.</li>
</ul>
"""

@route ("/", method='POST')
def index():
    # print("REQUEST: {0}".format(request.json))
    # if _auth_header.lower() not in request.query:
    #     response.status = 401
    #     return "auth_header query parameter required"
    # auth_header = request.query[_auth_header.lower()]
    # if auth_header == None or auth_header != os.environ.get(_auth_header):
    #     response.status = 401
    #     return "Not Authorized"

    msg = entities.HipChatRoomMessage(**request.json)
    trebek = Trebek(msg)
    response_message = trebek.get_response_message()
    if response_message != None:
        parameters = {}
        parameters['from'] = 'trebek'
        parameters['room_id'] = msg.item.room.room_id 
        parameters['message'] = response_message
        parameters['color'] = 'gray'

        return json.dumps(parameters)

if __name__ == "__main__":
    run (host='localhost', port=8080, reloader=True, server='paste')
