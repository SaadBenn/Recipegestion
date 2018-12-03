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

    def post_to_slack(self, response, channel):
        """
        :param response: the response by the bot
        :param channel: the channel to which the response will be posted to
        """
        self.slack_client.api_call("chat.postMessage", channel=channel, text=response, as_user=True)

    def make_formatted_steps(self, recipe_info, recipe_steps):
        response = "Ok, it takes *" + str(recipe_info['readyInMinutes']) + \
                   "* minutes to make *" + str(recipe_info['servings']) + "* servings of *" + \
                   recipe_info['title'] + "*. Here are the steps:\n\n"

        if recipe_steps and recipe_steps[0]['steps']:
            for i, r_step in enumerate(recipe_steps[0]['steps']):
                equip_str = ''
                for e in r_step['equipment']:
                    equip_str += e['name'] + ", "
                    if not equip_str:
                        equip_str = 'None'
                    else:
                        equip_str = equip_str[:-2]

                    response += '*Step ' + str(i + 1) + '*:\n' + '_Equipment_: ' + equip_str + '\n' + '_Action_: ' + \
                                r_step['step'] + '\n\n'

        else:
            response += '_No instructions available for this recipe._\n\n'

        response += '*Say anything to me to start over...*'
        return response

    def handle_ingredients_message(self, message):
        """
        param message: the user message
        :return: the corresponding ingredients for the recipe
        """
        if self.context['get_recipes']:
            self.context['recipes'] = self.recipe_client.find_by_ingredients(message)

        response = 'Let\'s see here... \n' + 'I\'ve found these recipes: \n'

        for i, recipe in enumerate(self.context['recipes']):
            response += str(i + 1) + '. ' + recipe['title'] + '\n'
        response += '\nPlease enter the corresponding number of your choice.'

        return response

    def handle_cuisine_message(self, cuisine):
        if self.context['get_recipes']:
            self.context['recipes'] = self.recipe_client.find_by_cuisine(cuisine)

        response = 'Let\s see here.. \n' + 'I\'ve found these recipes: \n'

        for i, recipe in enumerate(self.context['recipes']):
            response += str(i+1) + '. ' + recipe['title'] + '\n'
        response += '\nPlease enter the corresponding number of your choice.'

        return response

    def handle_selection_message(self, selection):
        """
        :param selection: the number selected
        :return: the formatted response
        """
        recipe_id = self.context['recipes'][selection-1]['id']
        recipe_info = self.recipe_client.get_info_by_id(recipe_id)
        recipe_steps = self.recipe_client.get_steps_by_id(recipe_id)

        return self.make_formatted_steps(recipe_info, recipe_steps)

    def handle_message(self, message, channel):
        watson_response = self.conversation_client.message(
            workspace_id= self.workspace_id,
            message_input={'text': message},
            context=self.context
        )

        self.context = watson_response['context']

        if 'is_ingredients' in self.context.keys() and self.context['is_ingredients']:
            response = self.handle_ingredients_message(message)
        elif 'is_selection' in self.context.keys() and self.context['is_selection']:
            self.context['selection_valid'] = False
            response = 'Invalid selection ' + 'Say something to see your choices again...'

            if self.context['selection'].isdigit():
                selection = int(self.context['selection'])
                if 1 <= selection <= 5:
                    self.context['selection_valid'] = True
                    response = self.handle_selection_message(selection)
        elif watson_response['entities'] and watson_response['entities'][0]['entity'] == 'cuisine':
            cuisine = watson_response['entities'][0]['value']
            response = self.handle_cuisine_message(cuisine)

        else:
            response = ''
            for text in watson_response['output']['text']:
                response += text + '\n'

        self.post_to_slack(response, channel)

        