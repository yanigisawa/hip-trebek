import os
import unittest
from errbot.backends.test import testbot, push_message, pop_message
from errbot import plugin_manager
import json
import trebek
from collections import namedtuple

# Reference this SO post on getting distances between strings:
# http://stackoverflow.com/a/1471603/98562
def _json_object_hook(d): return namedtuple('X', d.keys())(*d.values())
def json2obj(data): return json.loads(data, object_hook=_json_object_hook)

def fake_fetch_random_clue():
    with open('test-json-output.json') as json_data:
        clue = json.load(json_data) #, object_hook=_json_object_hook)
    # clue = json2obj(json_string)
    return trebek.Question(**clue)

class TestMyPlugin(object):
    extra_plugin_dir = '.'
    
    def test_when_value_not_included_default_to_200(self, testbot):
        plugin = plugin_manager.get_plugin_obj_by_name('Trebek')
        plugin.fetch_random_clue = fake_fetch_random_clue
        random_clue = plugin.get_random_clue()
        test_clue = plugin.fetch_random_clue()
        assert test_clue.value == None
        assert random_clue.value == 200

    def test_round_in_progress_cannot_start_new_round(self, testbot):
        plugin = plugin_manager.get_plugin_obj_by_name('Trebek')
        plugin.start_jeopardy()
        push_message('!trebek jeopardy')
            
        assert "Round in progress, cannot start a new Jeopardy round." in pop_message()

    def test_when_answer_includes_html_answer_is_sanitized(self, testbot):
        # example answer: <i>Let\\'s Make a Deal</i>
        plugin = plugin_manager.get_plugin_obj_by_name('Trebek')
        plugin.fetch_random_clue = fake_fetch_random_clue
        random_clue = plugin.get_random_clue()
        test_clue = plugin.fetch_random_clue()
        assert test_clue.answer == "Let's Make a Deal"

    def test_when_response_doesNot_begin_with_question_return_none(self):
        plugin = plugin_manager.get_plugin_obj_by_name('Trebek')
        response = "some test response"
        assert plugin.response_is_a_question(response) == None

    def test_when_response_is_question_return_true(self):
        plugin = plugin_manager.get_plugin_obj_by_name('Trebek')
        response = "what is some test response"
        assert plugin.response_is_a_question(response)

    def test_fuzzy_matching_of_answer(self):
        plugin = plugin_manager.get_plugin_obj_by_name('Trebek')
        test_clue = fake_fetch_random_clue()
        assert plugin.is_correct_answer(test_clue.answer, "what is Let's Make a Deal")
        assert plugin.is_correct_answer(test_clue.answer, "what is let's make a deal")
        assert plugin.is_correct_answer(test_clue.answer, "what is Lets Make a Deal")
        assert plugin.is_correct_answer(test_clue.answer, "what is Let's Make Deal")
        assert plugin.is_correct_answer(test_clue.answer, "what is Let's Make a Dela")
        assert plugin.is_correct_answer(test_clue.answer, "what is Let's Mae a Deal")
        assert plugin.is_correct_answer(test_clue.answer, "what is Let's Make a Deal")
        assert plugin.is_correct_answer(test_clue.answer, "what is elt's Make a Deal")
        assert not plugin.is_correct_answer(test_clue.answer, "Let's a Deal")
        assert not plugin.is_correct_answer(test_clue.answer, "Let's make ")
        assert plugin.is_correct_answer("a ukulele", "a ukelele")
        assert plugin.is_correct_answer("Scrabble", "Scrablle")


        

def main():
    unittest.main()

if __name__ == '__main__':
    main()        
