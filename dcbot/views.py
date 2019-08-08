
import string
import threading

import requests

from flask import (Blueprint, flash, g, redirect, request, session, url_for, jsonify)

from .logic import (is_player, get_service_for_group_id, get_service_for_service_host, get_user_id, set_intent,
    get_members_intents)
from .slack_logic import sl, get_group_name, get_service_name
from .logic import populate_groups, get_group_id_for_service, set_host, get_host
from .errors import BotGroupError

bp = Blueprint('dcbot', __name__, url_prefix="/dcbot")


MAIN_CHANNEL = "defcon2019"

# Messages

NOT_A_PLAYER = '_You do not seem to be a Shellphish player at DEFCON CTF 2019. Contact the team lead if you believe ' \
               'this is incorrect._'
REQUEST_RECEIVED = "_Request received :) Hang on_"
CHANNEL_DOES_NOT_EXIST = '_Channel for service %s does not exist. Maybe the channel hasn\'t been created yet. ' \
                         'You may create the channel using the /newservice command._'

#
# Util methods
#

def send_response(response_url, r):
    requests.post(response_url,
                  json=r
                  )


#
# Views
#

@bp.route("/", methods=('GET',))
def index():
    return "Hello, world!"


@bp.route("/echo", methods=('POST',))
def echo():
    """
    Echo back the message that the user has sent, together with user ID.

    text: The message that user has sent.
    """
    form = request.form
    cmd = form['command']
    assert cmd == "/echo"

    message = form['text']
    echo_message = "User %s said: %s" % (form['user_id'], message)

    # start a new thread to send response message back
    th = threading.Thread(target=echo_worker, args=(form['response_url'], echo_message, ), daemon=True)
    th.start()

    return REQUEST_RECEIVED


@bp.route("/listservice", methods=('POST',))
def listservice():
    """
    List all currently available services.
    """

    form = request.form
    cmd = form['command']
    assert cmd == "/listservice"

    # is this guy a player?
    user_id = form['user_id']
    if not is_player(user_id):
        return {
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        }

    if form['text'] == "in_channel":
        response_type = "in_channel"
    else:
        response_type = "ephemeral"

    services = sl.get_service_list()
    txt = [ ]
    n = 0
    for service in services:
        n += 1
        # who's the host?
        host = get_host(get_group_id_for_service(service))
        if host:
            line = "_%s_ in channel #%s | Hosting by <@%s>" % (service, get_group_name(service), host)
        else:
            line = "_%s_ in channel #%s | *Host wanted!*" % (service, get_group_name(service))
        txt.append(line)
    attachment = "\n".join(txt)
    return jsonify({
        'response_type': response_type,
        'text': "%d services online." % n,
        'attachments': [
            {
                "text": attachment,
            },
        ]
    })


@bp.route("/newservice", methods=('POST',))
def newservice():
    """
    Create a new channel for service.

    text: Name of the service.
    """
    form = request.form
    cmd = form['command']
    assert cmd == "/newservice"

    # is this guy a player?
    user_id = form['user_id']
    if not is_player(user_id):
        return {
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        }

    # sanitize service name
    service = form['text']
    charset = string.ascii_letters + string.digits + "-_"
    if any([ch not in charset for ch in service]):
        return jsonify({
            'response_type': 'ephemeral',
            'text': 'Invalid service name "%s". Service name can only include letters, digits, dashes and underscores.' % service
        })

    # start a new thread to create the channel
    th = threading.Thread(target=newservice_worker, args=(form['response_url'], service), daemon=True)
    th.start()

    return REQUEST_RECEIVED


@bp.route("/workon", methods=('POST',))
def workon():
    """
    User @user_id wants to work on a service specified in the text.

    text: Name of the service that the user wants to work on.
    """

    form = request.form
    cmd = form['command']
    assert cmd == '/workon'

    user_id = form['user_id']
    # is this user one of the players?
    if not is_player(user_id):
        return {
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        }

    # does this service exist?
    service = form['text']
    group_id = get_group_id_for_service(service)

    if group_id is None:
        return {
            'response_type': 'ephemeral',
            'text': CHANNEL_DOES_NOT_EXIST % service
        }

    # add the user to that group
    th = threading.Thread(target=workon_worker, args=(form['response_url'], form['user_id'], service), daemon=True)
    th.start()
    return REQUEST_RECEIVED


@bp.route("/host", methods=('POST',))
def host():
    """
    User @user_id wants to be a host of a service specified in the text.

    text: Name of the service that the user wants to host.
    """

    form = request.form
    cmd = form['command']
    assert cmd == "/host"

    user_id = form['user_id']
    # is this user one of the players?
    if not is_player(user_id):
        return {
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        }

    # TODO: Check if this user is one of the allowed service hosts
    # TODO: If not, show a warning, but still allow them to proceed

    service = form['text']
    if not service:
        # take the current channel name
        group_id = form['channel_id']
        service = get_service_for_group_id(group_id)

    if not service:
        return {
            'response_type': 'ephemeral',
            'text': '_Please specify the name of the service that you want to host._'
        }

    group_id = get_group_id_for_service(service)
    if group_id is None:
        return {
            'response_type': 'ephemeral',
            'text': CHANNEL_DOES_NOT_EXIST % service
        }

    # set the user as the host of thar service
    th = threading.Thread(target=host_worker, args=(form['response_url'], form['user_id'], group_id), daemon=True)
    th.start()
    return REQUEST_RECEIVED


@bp.route("/unhost", methods=("POST",))
def unhost():
    """
    User @user_id wants to remove himself from the service host position that he is currently taking.

    text: None
    """

    form = request.form
    cmd = form['command']
    assert cmd == "/unhost"

    user_id = form["user_id"]
    # is this user one of the players?
    if not is_player(user_id):
        return {
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        }

    th = threading.Thread(target=unhost_worker, args=(form['response_url'], form['user_id']), daemon=True)
    th.start()
    return REQUEST_RECEIVED


@bp.route("/floor", methods=("POST",))
def floor():
    """
    User @user_id wants to be on the CTF floor.

    text: None
    """

    form = request.form
    cmd = form['command']
    assert cmd == "/floor"

    user_id = form["user_id"]
    if not is_player(user_id):
        return {
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        }

    set_intent(form['user_id'])

    return "_I get it. You want to be on the CTF floor. I'll let Giovanni know and " \
           "get back to you later when it's your turn._"


@bp.route("/floorrequests", methods=("POST", ))
def floorrequests():
    """
    List everyone who has requested to be on the floor.

    text: None
    """

    form = request.form
    cmd = form['command']
    assert cmd == "/floorrequests"

    user_id = form["user_id"]
    if not is_player(user_id):
        return {
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        }

    attachment = [ ]
    for member_id, wants_to_go in get_members_intents():
        attachment.append("<@%s> %s" % (member_id, wants_to_go))

    return {
        "response_type": "ephemeral",
        "text": "%d requests." % len(attachment),
        "attachments": [
            {
                "text": "\n".join(attachment),
            }
        ]
    }


@bp.route("/iamonthefloor")
def iamonthefloor():
    """
    Player specifies that he is on the floor.

    text: None
    """

    return "Not implemented. Do we really need this?"


@bp.route("/slackers")
def slackers():
    """
    Get a list of "slackers".

    text: None
    """

    return "Not implemented. Do we really need this?"


#
# Worker routines
#


def echo_worker(response_url, echo_message):
    send_response(response_url, {
        'response_type': 'ephemeral',
        'text': echo_message,
    })


def workon_worker(response_url, user_id, service):
    try:
        sl.add_member_to_service(user_id, service)
    except BotGroupError:
        send_response(response_url, {
            'response_type': 'ephemeral',
            'text': 'Cannot add you to the channel for service %s. Maybe the channel has been archived.' % service
        })
        return

    send_response(response_url, {
        'response_type': 'ephemeral',
        'text': 'Success!',
    })


def host_worker(response_url, user_id, group_id):

    service_name = get_service_for_group_id(group_id)
    if not service_name:
        # what? why?
        service_name = "<Unknown>"
    group_name = get_group_name(service_name)

    # is the current user already a service host for another service?
    current_hosting = get_service_for_service_host(user_id)
    if current_hosting is not None and current_hosting != service_name:
        # you can repeat the "/host" command to announce to everyone multiple times that you are the great host ;)
        send_response(response_url, {
            'response_type': 'ephemeral',
            'text': '_You are currently hosting service %s. You cannot be a host for more than one service. You can, '
                    'however, unhost it first using the /unhost command._' % current_hosting
        })
        return

    # is the current user in the group?
    members = sl.get_members_for_service(service_name)
    if members and user_id not in members:
        sl.add_member_to_service(user_id, service_name)

    old_host = get_host(group_id)

    try:
        set_host(user_id, group_id)
    except BotGroupError as ex:
        send_response(response_url, {
            'response_type': 'ephemeral',
            'text': str(ex),
        })
        return

    send_response(response_url, {
        'response_type': 'ephemeral',
        'text': 'Success!'
    })

    if old_host is None:
        sl.yell(MAIN_CHANNEL, "<@%s> becomes the service host of challenge %s." % (
            user_id, service_name), resiliency=True)
        sl.yell(group_name, "<@%s> becomes the service host of challenge %s." % (
            user_id, service_name), resiliency=True)
    elif old_host == user_id:
        sl.yell(MAIN_CHANNEL, "<@%s> is the service host of challenge %s." % (
            user_id, service_name), resiliency=True)
        sl.yell(group_name, "<@%s> is the service host of challenge %s." % (
            user_id, service_name), resiliency=True)
    else:
        sl.yell(MAIN_CHANNEL, "<@%s> becomes the service host of challenge %s replacing <@%s>." % (
            user_id, service_name, old_host
        ), resiliency=True)
        sl.yell(group_name, "<@%s> becomes the service host of challenge %s replacing <@%s>." % (
            user_id, service_name, old_host
        ), resiliency=True)


def unhost_worker(response_url, user_id):

    # is the current user already a service host for a service?
    current_hosting = get_service_for_service_host(user_id)
    if current_hosting is None:
        send_response(response_url, {
            'response_type': 'ephemeral',
            'text': '_You are not hosting any service._'
        })
        return

    group_id = get_group_id_for_service(current_hosting)
    set_host(None, group_id)
    send_response(response_url, {
        'response_type': 'ephemeral',
        'text': '_Successfully unhosted yourself from service %s._' % current_hosting
    })

    sl.yell(MAIN_CHANNEL, "<@%s> is no longer the service host of challenge %s." % (
        user_id, current_hosting,
    ))
    sl.yell(get_group_name(current_hosting), "<@%s> is no longer the service host of challenge %s." % (
        user_id, current_hosting,
    ))


def newservice_worker(response_url, service):
    try:
        sl.create_group_for_service(service)
    except BotGroupError as ex:
        send_response(response_url, {
            'response_type': 'ephemeral',
            'text': '_Cannot create group for service %s: %s_' % (service, ex),
        })
        return

    # invite @dcbot
    bot_id = get_user_id("dcbot")
    if bot_id is None:
        # huh @dcbot does not exist
        print("Hang on, @dcbot does not exist.")
    else:
        sl.add_member_to_service(bot_id, service)

    # repopulate the channel
    populate_groups()
    send_response(response_url, {
        'response_type': 'ephemeral',
        'text': '_Successfully created a private channel for service %s._' % service,
    })
