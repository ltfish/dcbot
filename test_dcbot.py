
from time import sleep

from dcbot import create_app
from dcbot.logic import populate_db
from dcbot.db import init_db
from dcbot.slack_logic import SlackLogic, sl

import dcbot.views


main_channel = 'defcon2019'

class TestSlackLogic:
    def __init__(self):
        self.reset()

    def reset(self):
        self.channels = {}
        self.results = []

    def hello_world(self, channel="#random"):
        self.results.append("Posted 'Hello World!' to '{}'".format(channel))

    def yell(self, channel, message, resiliency=True):
        self.results.append("Posted '{}' to '{}'".format(message, channel))

    def create_group_for_service(self, service_name):
        self.channels[service_name] = (None, [])
        self.results.append("Created channel '{}'".format(service_name))

    def get_group_id_for_service(self, service_name):
        return service_name if service_name in self.channels else None

    def get_group_id(self, group_name):
        if group_name == main_channel:
            return main_channel
        return group_name if group_name in self.channels else None

    def get_members_for_service(self, service_name):
        group_id = self.get_group_id_for_service(service_name)
        return self.get_members_for_channel(group_id)

    def get_members_for_channel(self, channel_id):
        if channel_id == main_channel:
            yield from ['dcbot', 'dc_user1', 'dc_user2', 'dc_user3']
        elif channel_id in self.channels:
            yield from self.channels[channel_id][1]

    def get_member_info(self, member_id):
        return {
            'id': member_id,
            'name': member_id,
            'display_name': member_id,
            'real_name': member_id,
        }

    def add_member_to_service(self, member_id, service_name):
        if service_name in self.channels:
            self.channels[service_name][1].append(member_id)
            self.results.append("Added member '{}' to '{}'".format(member_id, service_name))

    def get_service_list(self):
        yield from self.channels

for attr in dir(TestSlackLogic):
    if not attr.startswith('_'):
        setattr(SlackLogic, attr, getattr(TestSlackLogic, attr))
sl.reset()

def send_response(response_url, r):
    dcbot.slack_logic.sl.results.append("Sent '{}' to '{}'".format(r, response_url))
dcbot.views.send_response = send_response


init_db()
populate_db()
app = create_app()
client = app.test_client()


def test_hello():
    response = client.get('/dcbot', follow_redirects=True)
    assert response.data == b'Hello, world!'


def test_echo():
    response = client.post('/dcbot/echo',
                           data={'command': '/echo',
                                 'text': 'ping',
                                 'user_id': 'some_user',
                                 'response_url': 'some_url'},
                           follow_redirects=True)
    print(response)

    sleep(1)
    print(sl.results)

    assert sl.results[0] == "Sent '{'response_type': 'ephemeral', 'text': 'User some_user said: ping'}' to 'some_url'"

    sl.reset()


def test_listservice_not_dc():
    response = client.post('/dcbot/listservice',
                           data={'command': '/listservice',
                                 'text': '',
                                 'user_id': 'not_dc_user',
                                 'response_url': 'some_url'},
                           follow_redirects=True)
    print(response)

    sleep(1)
    print(sl.results)

    assert response.data == b'{"response_type":"ephemeral","text":"_You do not seem to be a Shellphish player at DEFCON CTF 2019. Contact the team lead if you believe this is incorrect._"}\n'

    sl.reset()


def test_listservice_none():
    response = client.post('/dcbot/listservice',
                           data={'command': '/listservice',
                                 'text': '',
                                 'user_id': 'dc_user1',
                                 'response_url': 'some_url'},
                           follow_redirects=True)
    print(response)

    sleep(1)
    print(sl.results)

    assert response.data == b'{"attachments":[{"text":""}],"response_type":"ephemeral","text":"0 services online."}\n'

    sl.reset()


def test_single_service():
    response = client.post('/dcbot/newservice',
                           data={'command': '/newservice',
                                 'text': 'some_service',
                                 'user_id': 'dc_user1',
                                 'response_url': 'some_url'},
                           follow_redirects=True)
    print(response)

    response = client.post('/dcbot/listservice',
                           data={'command': '/listservice',
                                 'text': '',
                                 'user_id': 'dc_user1',
                                 'response_url': 'some_url'},
                           follow_redirects=True)
    print(response)

    sleep(1)
    print(sl.results)

    sl.reset()
