
import string
import threading

import requests

from flask import (Blueprint, flash, g, redirect, request, session, url_for, jsonify)

from .enums import CTFFloorStatusEnum
from .logic import (is_player, get_service_for_group_id, get_service_for_service_host, get_user_id, set_intent,
    get_members_intents)
from .messages import *
from .slack_logic import sl
from .utils import get_group_name, user_text_to_user_id
from .logic import (populate_groups, get_group_id_for_service, set_host, get_host, set_member_on_floor,
                    set_member_off_floor)
from .errors import BotGroupError

bp = Blueprint('dcbot', __name__, url_prefix="/dcbot")


# Admin UIDs

ADMIN_UIDS = {
    'U03REJMH6', # massimo zanardi
    'U03RQ5CJN', # fish wang on Shellphish Slack
    'ULQ3YEH5G', # fish wang on ShellphishTest Slack
}


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
        return jsonify({
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        })

    if form['text'] == "in_channel":
        response_type = "in_channel"
    else:
        response_type = "ephemeral"

    services = sorted(list(sl.get_service_list()))
    txt = [ ]
    n = 0
    for service, archived in services:
        if archived:
            continue
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
        return jsonify({
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        })

    # sanitize service name
    service = form['text']
    charset = string.ascii_letters + string.digits + "-_"
    if any([ch not in charset for ch in service]):
        return jsonify({
            'response_type': 'ephemeral',
            'text': INVALID_SERVICE_NAME % service
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
        return jsonify({
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        })

    # does this service exist?
    service = form['text']
    group_id = get_group_id_for_service(service)

    if group_id is None:
        return jsonify({
            'response_type': 'ephemeral',
            'text': CHANNEL_DOES_NOT_EXIST % service
        })

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
        return jsonify({
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        })

    # TODO: Check if this user is one of the allowed service hosts
    # TODO: If not, show a warning, but still allow them to proceed

    service = form['text']
    if not service:
        # take the current channel name
        group_id = form['channel_id']
        service = get_service_for_group_id(group_id)

    if not service:
        return jsonify({
            'response_type': 'ephemeral',
            'text': MISSING_SERVICE_NAME
        })

    group_id = get_group_id_for_service(service)
    if group_id is None:
        return jsonify({
            'response_type': 'ephemeral',
            'text': CHANNEL_DOES_NOT_EXIST % service
        })

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
        return jsonify({
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        })

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
        return jsonify({
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        })

    set_intent(form['user_id'])

    return FLOOR_REQUEST_RECEIVED


@bp.route("/floorstatus", methods=("POST", ))
def floorstatus():
    """
    List everyone who has requested to be on the floor.

    text: None
    """

    form = request.form
    cmd = form['command']
    assert cmd == "/floorstatus"

    user_id = form["user_id"]
    if not is_player(user_id):
        return jsonify({
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        })

    wantstogo = [ ]
    onthefloor = [ ]
    neutral = [ ]
    for member_id, (intent, last_on_floor) in get_members_intents():
        if intent == CTFFloorStatusEnum.WantsToGo:
            wantstogo.append("<@%s> | %s" % (member_id, CTFFloorStatusEnum.to_string(intent)))
        elif intent == CTFFloorStatusEnum.OnTheFloor:
            onthefloor.append("<@%s>" % member_id)
        elif intent == CTFFloorStatusEnum.Neutral:
            neutral.append("<@%s>" % member_id)

    return jsonify({
        "response_type": "ephemeral",
        "text": "*There are %d players who want to go to the CTF floor.*" % len(wantstogo),
        "attachments": [
            {
                "text": "\n".join(wantstogo),
            },
            {
                "text": "*%d players are currently on the floor.*" % len(onthefloor),
            },
            {
                "text": "\n".join(onthefloor),
            },
            {
                "text": "*%d players are OK either way.*" % len(neutral),
            },
            {
                "text": "\n".join(neutral),
            }
        ]
    })


@bp.route("/iamonthefloor")
def iamonthefloor():
    """
    Player specifies that he is on the floor.

    text: None
    """

    return NOT_IMPLEMENTED


@bp.route("/slackers")
def slackers():
    """
    Get a list of "slackers".

    text: None
    """

    return NOT_IMPLEMENTED


@bp.route("/approve", methods=("POST",))
def approve():
    """
    Approve a player's request of going on to the CTF floor.

    text: Name of the player or the ID of the player.
    """

    form = request.form
    cmd = form['command']
    assert cmd == "/approve"

    # Only certain people can do this. Let's hard code a list of allowed user IDs
    if form['user_id'] not in ADMIN_UIDS:
        return PERMISSION_DENIED

    member_text = form['text']
    member_id = user_text_to_user_id(member_text)
    set_member_on_floor(member_id)

    th = threading.Thread(target=approve_worker, args=(member_id,), daemon=True)
    th.start()
    return REQUEST_RECEIVED + " Player <@%s> is set to be on the floor." % member_id


@bp.route("/leavefloor", methods=("POST",))
def leavefloor():
    """
    Leave the CTF floor.

    text: Name of the player to leave the floor (only admins can do this), or empty to mean that the current user is
    leaving the floor.
    """

    form = request.form
    cmd = form['command']
    assert cmd == "/leavefloor"

    # is this a player?
    if not is_player(form['user_id']):
        return jsonify({
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        })

    member_text = form['text']
    if not member_text:
        member_id = form['user_id']
    else:
        # convert the text to member ID
        member_id = user_text_to_user_id(member_text)
    if member_id != form['user_id']:
        # are we an admin?
        if form['user_id'] not in ADMIN_UIDS:
            return PERMISSION_DENIED

    set_member_off_floor(member_id)
    return REQUEST_RECEIVED + " Player <@%s> is not on the floor any more." % member_id


@bp.route("/bothelp", methods=("POST",))
def bothelp():
    """
    Return the help message.

    text: None
    """

    form = request.form
    cmd = form['command']
    assert cmd == "/bothelp"

    if not is_player(form['user_id']):
        return jsonify({
            'response_type': 'ephemeral',
            'text': NOT_A_PLAYER,
        })

    help_text = """List of commands supported by dcbot:
- Services
`/listservice`  List available services that are currently online
`/workon <service>`  Join a service channel
`/newservice <service>`  Create a channel for a service

- Service hosts
`/host <service>`  Become a host of a service
`/unhost`  No longer be a host for the serivce you are hosting

- Trips to the CTF floor
`/floorstatus`  List the status of the CTF floor
`/floor`  Express my intent to go to the CTF floor
`/leavefloor`  Leave the CTF floor

- Administration
`/approve <user>`  Approve a CTF floor request
Detailed descriptions of each command can be found at https://github.com/ltfish/dcbot/blob/master/README.md.
"""

    return jsonify({
        'response_type': 'ephemeral',
        'attachments': [
            {
                'text': help_text,
            },
        ]
    })

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
            'text': CANNOT_JOIN_CHANNEL % service
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
            'text': ALREADY_HOSTING % current_hosting
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
        sl.yell(MAIN_CHANNEL, "_<@%s> becomes the service host of challenge %s._" % (
            user_id, service_name), resiliency=True)
        sl.yell(group_name, "_<@%s> becomes the service host of challenge %s._" % (
            user_id, service_name), resiliency=True)
    elif old_host == user_id:
        sl.yell(MAIN_CHANNEL, "_<@%s> is the service host of challenge %s._" % (
            user_id, service_name), resiliency=True)
        sl.yell(group_name, "_<@%s> is the service host of challenge %s._" % (
            user_id, service_name), resiliency=True)
    else:
        sl.yell(MAIN_CHANNEL, "_<@%s> becomes the service host of challenge %s replacing <@%s>._" % (
            user_id, service_name, old_host
        ), resiliency=True)
        sl.yell(group_name, "_<@%s> becomes the service host of challenge %s replacing <@%s>._" % (
            user_id, service_name, old_host
        ), resiliency=True)


def unhost_worker(response_url, user_id):

    # is the current user already a service host for a service?
    current_hosting = get_service_for_service_host(user_id)
    if current_hosting is None:
        send_response(response_url, {
            'response_type': 'ephemeral',
            'text': NOT_HOSTING
        })
        return

    group_id = get_group_id_for_service(current_hosting)
    set_host(None, group_id)
    send_response(response_url, {
        'response_type': 'ephemeral',
        'text': '_Successfully unhosted yourself from service %s._' % current_hosting
    })

    sl.yell(MAIN_CHANNEL, "_<@%s> is no longer the service host of challenge %s._" % (
        user_id, current_hosting,
    ))
    sl.yell(get_group_name(current_hosting), "_<@%s> is no longer the service host of challenge %s._" % (
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
        'text': CHANNEL_SUCCESSFULLY_CREATED % service,
    })


def approve_worker(member_id):
    sl.yell(member_id, INVITED_ON_FLOOR)
