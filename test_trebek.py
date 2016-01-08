import os
import unittest
import json
import trebek
import entities
import fakeredis
import time
import datetime

# Reference this SO post on getting distances between strings:
# http://stackoverflow.com/a/1471603/98562
def get_clue_json():
    with open('test-json-output.json') as json_data:
        clue = json.load(json_data) 
    return clue

def fake_fetch_random_clue():
    return entities.Question(**get_clue_json())

def fake_get_year_month():
    now = datetime.datetime.now()
    year, month = divmod(now.month + 1, 12)
    if month == 0: 
        month = 12
        year = year -1
    next_month = datetime.datetime(now.year + year, month, 1)
    return "{0}-{1}".format(next_month.year, str(next_month.month).zfill(2))

_fetch_count = 0
_invalid_clue = None

def fetch_invalid_clue():
    global _fetch_count, _invalid_clue
    clue = get_clue_json()
    if _fetch_count == 0:
        clue = _invalid_clue
        _fetch_count += 1
    return entities.Question(**clue)

class TestTrebek(unittest.TestCase):
    def setUp(self):
        d = self.get_setup_json()
        self.room_message = entities.HipChatRoomMessage(**d)
        self.trebek_bot = self.create_bot_with_dictionary(d)

    def tearDown(self):
        self.trebek_bot.redis.flushall() 

    def get_setup_json(self):
        with open('test-room-message.json') as data:
            d = json.load(data)
        return d

    def create_bot_with_dictionary(self, room_dictionary):
        bot = trebek.Trebek(entities.HipChatRoomMessage(**room_dictionary))
        bot.redis = fakeredis.FakeStrictRedis()
        bot.fetch_random_clue = fake_fetch_random_clue
        return bot
    
    def create_user_scores(self, bot = None):
        if bot != None:
            r = bot.redis
        else:
            r = self.trebek_bot.redis
            bot = self.trebek_bot
        hipchat = trebek.Trebek.hipchat_user_key
        r.set(hipchat.format(1), 'Aaron')
        r.set(hipchat.format(2), 'Allen')
        r.set(hipchat.format(3), 'Cordarrell')
        r.set(hipchat.format(4), 'Melvin')
        r.set(hipchat.format(5), 'Mark')
        r.set(hipchat.format(6), 'Richard')
        r.set(hipchat.format(7), 'Darren S')
        r.set(hipchat.format(8), 'Arian')
        r.set(hipchat.format(9), 'Zach')
        r.set(hipchat.format(10), 'Darren M')
        r.set(hipchat.format(11), 'Alex')
        r.set(hipchat.format(12), 'Michael')
        r.set(hipchat.format(13), 'Reggie')
        r.set(hipchat.format(14), 'Legacy Score')
        user = bot.user_score_prefix + ":{0}"
        r.set(user.format(1), 100)
        r.set(user.format(2), 20)
        r.set(user.format(3), 70)
        r.set(user.format(4), 50)
        r.set(user.format(5), 30)
        r.set(user.format(6), 200)
        r.set(user.format(7), 500)
        r.set(user.format(8), 5430)
        r.set(user.format(9), 412)
        r.set(user.format(10), 123)
        r.set(user.format(11), 225) 
        r.set(user.format(12), 94)
        r.set(user.format(13), 87)
        # Regression test old score keys will still appear in lifetime loserboard
        r.set("user_score:{0}".format(14), 5)
        bot.get_year_month = fake_get_year_month
        user = bot.user_score_prefix + ":{0}"
        r.set(user.format(1), 100)
        r.set(user.format(2), 20)
        r.set(user.format(3), 70)
        r.set(user.format(4), 50)
        r.set(user.format(5), 30)
        r.set(user.format(6), 200)
        r.set(user.format(7), 500)
        r.set(user.format(8), 5430)
        r.set(user.format(9), 412)
        r.set(user.format(10), 123)
        r.set(user.format(11), 225) 
        r.set(user.format(12), 94)
        r.set(user.format(13), 87)

    def test_when_value_not_included_default_to_200(self):
        test_clue = self.trebek_bot.fetch_random_clue()
        self.assertEqual(test_clue.value, 200)

    def test_when_answer_includes_html_answer_is_sanitized(self):
        # example answer: <i>Let\\'s Make a Deal</i>
        self.trebek_bot.fetch_random_clue = fake_fetch_random_clue
        test_clue = self.trebek_bot.fetch_random_clue()
        self.assertEqual(test_clue.answer, "Let's Make a Deal")

    def test_when_response_doesNot_begin_with_question_return_none(self):
        response = "some test response"
        assert self.trebek_bot.response_is_a_question(response) == None

    def test_when_response_is_question_return_true(self):
        response = "what is some test response"
        assert self.trebek_bot.response_is_a_question(response)

    def test_fuzzy_matching_of_answer(self):
        test_clue = fake_fetch_random_clue()
        self.assertFalse(self.trebek_bot.is_correct_answer("polygamist", "polyamourus"))
        self.assertTrue(self.trebek_bot.is_correct_answer(test_clue.answer, "what is Let's Make a Deal"))
        self.assertTrue(self.trebek_bot.is_correct_answer(test_clue.answer, "what is let's make a deal"))
        self.assertTrue(self.trebek_bot.is_correct_answer(test_clue.answer, "what is Lets Make a Deal"))
        self.assertTrue(self.trebek_bot.is_correct_answer(test_clue.answer, "what is Let's Make Deal"))
        self.assertTrue(self.trebek_bot.is_correct_answer(test_clue.answer, "what is Let's Make a Dela"))
        self.assertTrue(self.trebek_bot.is_correct_answer(test_clue.answer, "what is Let's Mae a Deal"))
        self.assertTrue(self.trebek_bot.is_correct_answer(test_clue.answer, "what is Let's Make a Deal"))
        self.assertTrue(self.trebek_bot.is_correct_answer(test_clue.answer, "what is elt's Make a Deal"))
        self.assertTrue(self.trebek_bot.is_correct_answer("a ukulele", "a ukelele"))
        self.assertTrue(self.trebek_bot.is_correct_answer("Scrabble", "Scrablle"))
        self.assertTrue(self.trebek_bot.is_correct_answer("(Aristotle) Onassis", "Onassis"))
        self.assertTrue(self.trebek_bot.is_correct_answer("(William) Blake", "blake"))
        self.assertTrue(self.trebek_bot.is_correct_answer("wings (or feathers)", "feathers"))
        self.assertTrue(self.trebek_bot.is_correct_answer("A.D. (Anno Domini)", "AD"))
        self.assertTrue(self.trebek_bot.is_correct_answer("(Little Orphan) Annie", "annie"))
        self.assertTrue(self.trebek_bot.is_correct_answer("a turtle (or a tortoise)", "turtle"))
        self.assertTrue(self.trebek_bot.is_correct_answer("a turtle (or a tortoise)", "tortoise"))
        # self.assertTrue(self.trebek_bot.is_correct_answer("ben affleck and matt damon", "Matt Damon & Ben Affleck"))

    def test_given_json_dictionary_hipchat_object_is_parsed(self):
        with open ('test-room-message.json') as data:
            d = json.load(data)
        t = entities.HipChatRoomMessage(**d)
        self.assertEqual(t.item.message.message, "jeopardy") 
        self.assertEqual(t.item.message.user_from.name, "James A")

    def test_message_object_trims_leading_slash_command(self):
        p = {}
        p['from'] = { 'id':None, 'links': None, 'mention_name':None, 'name': None, 'version': None}
        p['message'] = '/trebek jeopardy me'
        msg = entities.HipChatMessage(p)
        self.assertEqual(msg.message, "jeopardy me")

    def test_when_get_response_message_is_called_user_name_is_saved(self):
        self.trebek_bot.get_response_message()
        key = trebek.Trebek.hipchat_user_key.format('582174')
        self.assertTrue(self.trebek_bot.redis.exists(key))

        user_name = self.trebek_bot.redis.get(trebek.Trebek.hipchat_user_key.format('582174')).decode()
        self.assertEqual("James A", user_name)

    def test_number_is_formatted_as_currency(self):
        currency = self.trebek_bot.format_currency("100")
        self.assertEqual("$100", currency)

        currency = self.trebek_bot.format_currency("1000")
        self.assertEqual("$1,000", currency)

        currency = self.trebek_bot.format_currency("1000000000")
        self.assertEqual("$1,000,000,000", currency)

        currency = self.trebek_bot.format_currency("-100")
        self.assertEqual("<span style='color: red;'>-$100</span>", currency)

        currency = self.trebek_bot.format_currency("-1000000000")
        self.assertEqual("<span style='color: red;'>-$1,000,000,000</span>", currency)

    def test_user_requests_score_value_returned(self):
        d = self.get_setup_json()
        d['item']['message']['message'] = "/trebek score"
        bot = self.create_bot_with_dictionary(d)
        key = "{0}:{1}".format(bot.user_score_prefix,
                bot.room_message.item.message.user_from.id)
        bot.redis.set(key, 500)
        response = bot.get_response_message()
        self.assertEqual("$500", response)

    def test_user_leaderboard_value_returned(self):
        d = self.get_setup_json()
        d['item']['message']['message'] = "/trebek leaderboard"
        bot = self.create_bot_with_dictionary(d)
        self.create_user_scores(bot)
        response = bot.get_response_message()

        year, month = [int(x) for x in bot.get_year_month().split('-')]
        dt = datetime.datetime(year, month, 1)
        expected = "<p>Leaderboard for {0} {1}:</p>".format(dt.strftime("%B"), dt.year)
        expected += "<ol><li>Arian: $5,430</li>"
        expected += "<li>Darren S: $500</li>"
        expected += "<li>Zach: $412</li>"
        expected += "<li>Alex: $225</li>"
        expected += "<li>Richard: $200</li></ol>"
        self.assertEqual(expected, response)

    def test_user_loserboard_value_returned(self):
        d = self.get_setup_json()
        d['item']['message']['message'] = "/trebek show me the loserboard"
        bot = self.create_bot_with_dictionary(d)
        self.create_user_scores(bot)
        response = bot.get_response_message()

        year, month = [int(x) for x in bot.get_year_month().split('-')]
        dt = datetime.datetime(year, month, 1)
        expected = "<p>Loserboard for {0} {1}:</p>".format(dt.strftime("%B"), dt.year)
        expected +=  "<ol><li>Allen: $20</li>"
        expected += "<li>Mark: $30</li>"
        expected += "<li>Melvin: $50</li>"
        expected += "<li>Cordarrell: $70</li>"
        expected += "<li>Reggie: $87</li></ol>"
        self.assertEqual(expected, response)
        
    def test_jeopardy_round_can_start_from_nothing(self):
        response = self.trebek_bot.get_response_message()
        expected = "The category is <b>CLASSIC GAME SHOW TAGLINES</b> for $200: "
        expected += "<b>\"CAVEAT EMPTOR.  LET THE BUYER BEWARE\"</b> (Air Date: 18-Oct-2001)"
                
        self.assertEqual(expected, response)

    def test_user_cannot_answer_same_question_twice(self):
        # Arrange 
        clue = self.trebek_bot.get_jeopardy_clue()
        d = self.get_setup_json()
        user_answer_key = trebek.Trebek.user_answer_key.format(
                self.trebek_bot.room_id, clue.id, d['item']['message']['from']['id'])
        self.trebek_bot.redis.set(user_answer_key, 'true')
        self.trebek_bot.get_question()
        d['item']['message']['message'] = '/trebek this is an answer'

        bot = self.create_bot_with_dictionary(d)
        bot.redis = self.trebek_bot.redis

        # Act
        response = bot.get_response_message()

        # Assert
        self.assertEqual("You have already answered James A. Let someone else respond.", response)

    def test_given_incorrect_answer_user_score_decreased(self):
        # Arrange 
        d = self.get_setup_json()
        d['item']['message']['message'] = '/trebek some test answer'
        bot = self.create_bot_with_dictionary(d)
        bot.redis = fakeredis.FakeStrictRedis()
        bot.get_question()
        response = bot.get_response_message()
        user_score_key = "{0}:{1}".format(bot.user_score_prefix,
                self.trebek_bot.room_message.item.message.user_from.id)

        # Act
        score = bot.redis.get(user_score_key)
        bot.redis.flushdb()

        # Assert
        score_string = "<span style='color: red;'>-$200</span>"
        self.assertEqual(score_string, bot.format_currency(score))
        self.assertEqual("That is incorrect, James A. Your score is now {0}".format(score_string), response)

    def test_given_correct_answer_user_score_increased(self):
        # Arrange 
        d = self.get_setup_json()
        d['item']['message']['message'] = "/trebek what is Let's Make a deal"
        bot = self.create_bot_with_dictionary(d)
        bot.redis = fakeredis.FakeStrictRedis()
        bot.get_question()
        response = bot.get_response_message()
        user_score_key = "{0}:{1}".format(bot.user_score_prefix,
                self.trebek_bot.room_message.item.message.user_from.id)

        # Act
        score = bot.redis.get(user_score_key)
        bot.redis.flushdb()

        # Assert
        self.assertEqual("$200", bot.format_currency(score))
        self.assertEqual("That is correct, James A. Your score is now $200 (Expected Answer: Let's Make a Deal)", response)

    def test_given_correct_answer_nonQuestion_form_user_score_decreased(self):
        # Arrange 
        d = self.get_setup_json()
        d['item']['message']['message'] = "/trebek Let's Make a deal"
        bot = self.create_bot_with_dictionary(d)
        bot.redis = fakeredis.FakeStrictRedis()
        bot.get_question()
        response = bot.get_response_message()
        user_score_key = "{0}:{1}".format(bot.user_score_prefix,
                self.trebek_bot.room_message.item.message.user_from.id)

        # Act
        score = bot.redis.get(user_score_key)
        bot.redis.flushdb()

        # Assert
        score_string = "<span style='color: red;'>-$200</span>"
        self.assertEqual(score_string, bot.format_currency(score))
        self.assertEqual("That is correct James A, however responses should be in the form of a question. Your score is now {0}".format(score_string), response)
    
    def test_given_incorrect_answer_time_is_up_response(self):
        # Arrange 
        d = self.get_setup_json()
        d['item']['message']['message'] = "/trebek foobar"
        bot = self.create_bot_with_dictionary(d)
        bot.redis = fakeredis.FakeStrictRedis()
        bot.get_question()
        clue = bot.get_active_clue()
        clue.expiration = time.time() - (bot.seconds_to_expire + 1)
        key = bot.clue_key.format(bot.room_id)
        bot.redis.set(key, json.dumps(clue, cls = entities.QuestionEncoder))
        response = bot.get_response_message()
        user_score_key = "{0}:{1}".format(bot.user_score_prefix,
                self.trebek_bot.room_message.item.message.user_from.id)

        # Act
        score = bot.redis.get(user_score_key)
        bot.redis.flushdb()

        # Assert
        self.assertFalse(score)
        self.assertEqual(response, "Time is up! The correct answer was: <b>Let's Make a Deal</b>")

    def test_given_correct_answer_time_is_up_response(self):
        # Arrange 
        d = self.get_setup_json()
        d['item']['message']['message'] = "/trebek what is Let's Make a deal"
        bot = self.create_bot_with_dictionary(d)
        bot.redis = fakeredis.FakeStrictRedis()
        bot.get_question()
        clue = bot.get_active_clue()
        clue.expiration = time.time() - (bot.seconds_to_expire + 1)
        key = bot.clue_key.format(bot.room_id)
        bot.redis.set(key, json.dumps(clue, cls = entities.QuestionEncoder))
        response = bot.get_response_message()
        user_score_key = "{0}:{1}".format(bot.user_score_prefix,
                self.trebek_bot.room_message.item.message.user_from.id)

        # Act
        score = bot.redis.get(user_score_key)
        bot.redis.flushdb()

        # Assert
        self.assertFalse(score)
        self.assertEqual(response, "That is correct James A, however time is up. (Expected Answer: Let's Make a Deal)")

    def test_when_asked_for_answer_bot_responds_with_answer(self):
        d = self.get_setup_json()
        bot = self.create_bot_with_dictionary(d)
        bot.get_question()
        d['item']['message']['message'] = "/trebek answer"
        bot = self.create_bot_with_dictionary(d)
        response = bot.get_response_message()

        self.assertEqual("The answer was: Let's Make a Deal", response)

    def test_when_no_question_exists_answer_returns_no_active_clue(self):
        d = self.get_setup_json()
        d['item']['message']['message'] = "/trebek answer"
        bot = self.create_bot_with_dictionary(d)
        bot.redis.flushdb()
        response = bot.get_response_message()

        self.assertEqual("No active clue. Type '/trebek jeopardy' to start a round", response)

    def test_when_answer_contains_HTML_word_is_filtered(self):
        # e.g.: ANSWER: the <i>Stegosaurus</i>
        c = {'id':1, 'title': 'foo', 'created_at': 'bar', 'updated_at': 'foobar', 'clues_count':1}
        q = entities.Question(1, answer= "the <i>Stegosaurus</i>", category = c)
        self.assertEqual("the Stegosaurus", q.answer)

        # e.g.: ANSWER: <i>the Seagull</i>
        q = entities.Question(1, answer= "<i>the Seagull</i>", category = c)
        self.assertEqual("the Seagull", q.answer)

        q = entities.Question(1, answer= "Theodore Roosevelt", category = c)
        self.assertEqual("Theodore Roosevelt", q.answer)

    def test_when_fetched_clue_is_invalid_get_new_clue(self):
        global _invalid_clue, _fetch_count
        _fetch_count = 0
        clue = get_clue_json()
        clue['invalid_count'] = 1
        _invalid_clue = clue
        self.trebek_bot.fetch_random_clue = fetch_invalid_clue
        clue = self.trebek_bot.get_jeopardy_clue()
        self.assertEqual(clue.invalid_count, None)

    def test_when_fetched_clue_is_missing_question_get_new_clue(self):
        global _fetch_count, _invalid_clue
        _fetch_count = 0
        clue = get_clue_json()
        clue['question'] = ""
        _invalid_clue = clue

        self.trebek_bot.fetch_random_clue = fetch_invalid_clue
        clue = self.trebek_bot.get_jeopardy_clue()
        self.assertNotEqual(clue.question.strip(), "")

    def test_when_fetched_clue_contains_visual_clue_request_new_clue(self):
        global _fetch_count, _invalid_clue
        _fetch_count = 0
        clue = get_clue_json()
        clue['question'] = "the picture seen here, contains some test data"
        _invalid_clue = clue

        self.trebek_bot.fetch_random_clue = fetch_invalid_clue
        clue = self.trebek_bot.get_jeopardy_clue()
        self.assertFalse("seen here" in clue.question)

    def test_when_fetched_clue_contains_audio_clue_request_new_clue(self):
        global _fetch_count, _invalid_clue
        _fetch_count = 0
        clue = get_clue_json()
        clue['question'] = "the audio heard here, contains some test data"
        _invalid_clue = clue

        self.trebek_bot.fetch_random_clue = fetch_invalid_clue
        clue = self.trebek_bot.get_jeopardy_clue()
        self.assertFalse("heard here" in clue.question)

    def test_when_new_month_arrives_score_resets_to_zero(self):
        self.trebek_bot.update_score(200)

        self.trebek_bot.get_year_month = fake_get_year_month
        self.assertEqual("$0", self.trebek_bot.get_user_score())

    def test_lifetimescore_includes_multiple_months(self):
        # Seed other user's data (to reproduce bug)
        self.create_user_scores() 
        self.trebek_bot.update_score(200)

        self.trebek_bot.get_year_month = fake_get_year_month
        self.trebek_bot.update_score(200)
        self.assertEqual("$400", self.trebek_bot.get_user_score(True))

    def test_user_lifetime_loserboard_value_includes_multiple_months(self):
        d = self.get_setup_json()
        d['item']['message']['message'] = "/trebek show me the lifetime loserboard"
        bot = self.create_bot_with_dictionary(d)
        self.create_user_scores(bot)
        response = bot.get_response_message()

        expected =  "<ol><li>Legacy Score: $5</li>"
        expected += "<li>Allen: $40</li>"
        expected += "<li>Mark: $60</li>"
        expected += "<li>Melvin: $100</li>"
        expected += "<li>Cordarrell: $140</li></ol>"
        self.assertEqual(expected, response)

    def test_user_lifetime_leaderboard_value_returned(self):
        d = self.get_setup_json()
        d['item']['message']['message'] = "/trebek lifetime leaderboard"
        bot = self.create_bot_with_dictionary(d)
        self.create_user_scores(bot)
        response = bot.get_response_message()

        expected =  "<ol><li>Arian: $10,860</li>"
        expected += "<li>Darren S: $1,000</li>"
        expected += "<li>Zach: $824</li>"
        expected += "<li>Alex: $450</li>"
        expected += "<li>Richard: $400</li></ol>"
        self.assertEqual(expected, response)

def main():
    unittest.main()

if __name__ == '__main__':
    main()        
