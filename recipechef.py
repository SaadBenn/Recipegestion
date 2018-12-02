import json
import os
import time
from slackclient import SlackClient
from recipe import RecipeClient
from pprint import pprint


class RecipeChef:
    def __init__(self, bot_id, slack_client, conversation_client, recipe_client):
        self.bot_id = bot_id
        self.slack_client = slack_client
        self.conversation_client = conversation_client
        self.recipe_client = recipe_client

        self.at_bot = "<@" + bot_id + ">:"
        self.delay = 0.5  # second
        self.workspace_id = '93054028-2b0b-4b21-9bc1-ec8c48970dbb'

        self.context = {}

    def parse_slack_output(self, slack_rtm_output):
        output_list = slack_rtm_output

        if output_list and len(output_list) > 0:
            for output in output_list:
                if output and 'text' in output and 'user_profile' not in output and self.at_bot in output['text']:
                    return output['text'].split(self.at_bot)[1].strip().lower(), \
                           output['channel']
        return None, None

