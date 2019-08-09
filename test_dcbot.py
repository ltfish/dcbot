
from time import sleep

from dcbot import create_app
from dcbot.db import init_db
from dcbot.slack_logic import SlackLogic, sl
from nose2.tools.decorators import with_teardown

import dcbot.views
import dcbot.logic


main_channel = 'defcon2019'


def teardown():
    sl.channels = {}
    sl.results = []


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
teardown()

def send_response(response_url, r):
    dcbot.slack_logic.sl.results.append("Sent '{}' to '{}'".format(r, response_url))
dcbot.views.send_response = send_response


init_db()
dcbot.logic.populate_db()
app = create_app()
client = app.test_client()

def do_slack_post(command='', text='', user_id='some_user', response_url='some_url', follow_redirects=True):
    command = '/' + command
    route = '/dcbot' + command

    response = client.post(route,
                           data={'command': command,
                                 'text': text,
                                 'user_id': user_id,
                                 'response_url': response_url},
                           follow_redirects=follow_redirects)

    return response

@with_teardown(teardown)
def test_hello():
    response = client.get('/dcbot', follow_redirects=True)
    assert response.data == b'Hello, world!'


@with_teardown(teardown)
def test_echo():
    response = do_slack_post('echo', text='ping')
    print(response)

    sleep(1)
    print(sl.results)

    assert sl.results[0] == "Sent '{'response_type': 'ephemeral', 'text': 'User some_user said: ping'}' to 'some_url'"


@with_teardown(teardown)
def test_listservice_not_dc():
    response = do_slack_post('listservice', user_id='not_dc_user')
    print(response)

    sleep(1)
    print(sl.results)

    assert response.data == b'{"response_type":"ephemeral","text":"_You do not seem to be a Shellphish player at DEFCON CTF 2019. Contact the team lead if you believe this is incorrect._"}\n'


@with_teardown(teardown)
def test_listservice_none():
    response = do_slack_post('listservice', user_id='dc_user1')
    print(response)

    sleep(1)
    print(sl.results)

    assert response.data == b'{"attachments":[{"text":""}],"response_type":"ephemeral","text":"0 services online."}\n'


@with_teardown(teardown)
def test_new_service():
    response = do_slack_post('newservice', text='some_service', user_id='dc_user1')
    print(response)

    response = do_slack_post('listservice', user_id='dc_user1')
    print(response)

    sleep(1)
    print(sl.results)

    assert sl.results[0] == "Created channel 'some_service'"
    assert sl.results[1] == "Added member 'dcbot' to 'some_service'"
    assert sl.results[2] == "Sent '{'response_type': 'ephemeral', 'text': '_Successfully created a private channel for service some_service._'}' to 'some_url'"



@with_teardown(teardown)
def test_floor_add_player_success():
    response = do_slack_post('floor', user_id='dc_user1')
    print(response)

    sleep(1)
    assert response.data == b"_I get it. You want to be on the CTF floor. I'll let Giovanni know and get back to you later when it's your turn._"
    print("Successfully Used /floor")

    response = do_slack_post('floorstatus', user_id='dc_user1')
    print(response)

    assert response.data == b'{"attachments":[{"text":"<@dc_user1> | Wants to go"},{"text":"*0 players are currently on the floor.*"},' \
                            b'{"text":""},{"text":"*0 players are OK either way.*"},{"text":""}],"response_type":"ephemeral","text":' \
                            b'"*There are 1 players who want to go to the CTF floor.*"}\n'

    print("Successfully Added to wait list")


    dcbot.logic.set_member_on_floor('dc_user1')

    response = do_slack_post('floorstatus', user_id='dc_user1')
    print(response)

    assert response.data == b'{"attachments":[{"text":""},{"text":"*1 players are currently on the floor.*"},{"text":"<@dc_user1>"},' \
                            b'{"text":"*0 players are OK either way.*"},{"text":""}],"response_type":"ephemeral","text":' \
                            b'"*There are 0 players who want to go to the CTF floor.*"}\n'

    print("Successfully moved to the Floor")

    dcbot.logic.set_member_off_floor('dc_user1')

    response = do_slack_post('floorstatus', user_id='dc_user1')
    print(response)

    assert response.data == b'{"attachments":[{"text":""},{"text":"*0 players are currently on the floor.*"},{"text":""}' \
                            b',{"text":"*1 players are OK either way.*"},{"text":"<@dc_user1>"}],"response_type":"ephemeral",' \
                            b'"text":"*There are 0 players who want to go to the CTF floor.*"}\n'

    print("Successfully moved player off Floor")



@with_teardown(teardown)
def test_floor_add_player_fail():
    response = do_slack_post('floor')
    print(response)

    sleep(1)

    assert response.data == b'{"response_type":"ephemeral","text":"_You do not seem to be a Shellphish player at DEFCON CTF 2019.' \
                            b' Contact the team lead if you believe this is incorrect._"}\n'
    print("Successfully Denied Use of /floor")

    response = do_slack_post('floorstatus')
    print(response)

    assert response.data == b'{"response_type":"ephemeral","text":"_You do not seem to be a Shellphish player at DEFCON CTF 2019.' \
                            b' Contact the team lead if you believe this is incorrect._"}\n'
    print("Successfully Denied Use of /floorstatus")

    sl.reset()


@with_teardown(teardown)
def test_add_self_to_inexsisting_service():
    response = client.post('/dcbot/workon',
                           data={'command': '/workon',
                                 'text': 'not_an_existing_service_id',
                                 'user_id': 'dc_user1',
                                 'response_url': 'some_url'},
                           follow_redirects=True)
    sleep(1)

    assert response.data == b'{"response_type":"ephemeral","text":"_Channel for service not_an_existing_service_id does not exist. Maybe the channel hasn\'t been created yet. You may create the channel using the /newservice command._"}\n'


@with_teardown(teardown)
def test_add_non_dc_player_to_existing_service():
    client.post('/dcbot/newservice',
                data={'command': '/newservice',
                      'text': 'existing_service_id',
                      'user_id': 'dc_user1',
                      'response_url': 'some_url'},
                follow_redirects=True)
    sleep(1)

    response = client.post('/dcbot/workon',
                           data={'command': '/workon',
                                 'text': 'existing_service_id',
                                 'user_id': 'inexisting_member_id',
                                 'response_url': 'some_url'},
                           follow_redirects=True)
    sleep(1)

    assert response.data == b'{"response_type":"ephemeral","text":"_You do not seem to be a Shellphish player at DEFCON CTF 2019. Contact the team lead if you believe this is incorrect._"}\n'


@with_teardown(teardown)
def test_add_dc_player_to_existing_service():
    client.post('/dcbot/newservice',
                data={'command': '/newservice',
                      'text': 'existing_service_id',
                      'user_id': 'dc_user1',
                      'response_url': 'some_url'},
                follow_redirects=True)
    sleep(1)

    response = client.post('/dcbot/workon',
                           data={'command': '/workon',
                                 'text': 'existing_service_id',
                                 'user_id': 'dc_user1',
                                 'response_url': 'some_url'},
                           follow_redirects=True)
    sleep(1)

    assert response.data == b'_Request received :) Hang on._'
