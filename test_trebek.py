import os
import unittest
import json
import trebek
import entities
import fakeredis

# Reference this SO post on getting distances between strings:
# http://stackoverflow.com/a/1471603/98562

def fake_fetch_random_clue():
    with open('test-json-output.json') as json_data:
        clue = json.load(json_data) #, object_hook=_json_object_hook)
    return entities.Question(**clue)

class TestTrebek(unittest.TestCase):
    def setUp(self):
        with open ('test-room-message.json') as data:
            d = json.load(data)
        room_message = entities.HipChatRoomMessage(**d)
        self.trebek_bot = trebek.Trebek(room_message)
        self.trebek_bot.redis = fakeredis.FakeStrictRedis()
        self.trebek_bot.fetch_random_clue = fake_fetch_random_clue
    
    def create_user_scores(self):
        r = self.trebek_bot.redis
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
        user = trebek.Trebek.user_score_key
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

    def test_round_in_progress_cannot_start_new_round(self):
        self.trebek_bot.start_jeopardy()
        response = self.trebek_bot.parse_message()
            
        self.assertEqual("Round in progress, cannot start a new Jeopardy round.", response) 

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
        assert self.trebek_bot.is_correct_answer(test_clue.answer, "what is Let's Make a Deal")
        assert self.trebek_bot.is_correct_answer(test_clue.answer, "what is let's make a deal")
        assert self.trebek_bot.is_correct_answer(test_clue.answer, "what is Lets Make a Deal")
        assert self.trebek_bot.is_correct_answer(test_clue.answer, "what is Let's Make Deal")
        assert self.trebek_bot.is_correct_answer(test_clue.answer, "what is Let's Make a Dela")
        assert self.trebek_bot.is_correct_answer(test_clue.answer, "what is Let's Mae a Deal")
        assert self.trebek_bot.is_correct_answer(test_clue.answer, "what is Let's Make a Deal")
        assert self.trebek_bot.is_correct_answer(test_clue.answer, "what is elt's Make a Deal")
        assert not self.trebek_bot.is_correct_answer(test_clue.answer, "Let's a Deal")
        assert not self.trebek_bot.is_correct_answer(test_clue.answer, "Let's make ")
        assert self.trebek_bot.is_correct_answer("a ukulele", "a ukelele")
        assert self.trebek_bot.is_correct_answer("Scrabble", "Scrablle")

    def test_given_json_dictionary_hipchat_object_is_parsed(self):
        with open ('test-room-message.json') as data:
            d = json.load(data)
        t = entities.HipChatRoomMessage(**d)
        self.assertEqual(t.item.message.message, "jeopardy is some additional text for the command")
        self.assertEqual(t.item.message.user_from.name, "James A")

    def test_message_object_trims_leading_slash_command(self):
        p = {}
        p['from'] = { 'id':None, 'links': None, 'mention_name':None, 'name': None, 'version': None}
        p['message'] = '/trebek jeopardy me'
        msg = entities.HipChatMessage(p)
        self.assertEqual(msg.message, "jeopardy me")

    def test_when_parse_message_is_called_user_name_is_saved(self):
        self.trebek_bot.parse_message()
        key = trebek.Trebek.hipchat_user_key.format('582174')
        self.assertTrue(self.trebek_bot.redis.exists(key))

        user_name = self.trebek_bot.redis.get(trebek.Trebek.hipchat_user_key.format('582174')).decode()
        self.assertEqual("James A", user_name)


    def test_leaderboard_returns_scores_in_order(self):
        self.create_user_scores()
        expected = "1. Arian - 5430\n"
        expected += "2. Darren S - 500\n"
        expected += "3. Zach - 412\n"
        expected += "4. Alex - 225\n"
        expected += "5. Richard - 200\n"

        actual = self.trebek_bot.get_leaderboard()
        self.assertEqual(expected, actual)

    def test_loserboard_returns_scores_in_reverse_order(self):
        self.create_user_scores()
        expected = "1. Allen - 20\n"
        expected += "2. Mark - 30\n"
        expected += "3. Melvin - 50\n"
        expected += "4. Cordarrell - 70\n"
        expected += "5. Reggie - 87\n"

        actual = self.trebek_bot.get_loserboard()
        self.assertEqual(expected, actual)








        

def main():
    unittest.main()

if __name__ == '__main__':
    main()        
