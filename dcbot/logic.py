"""
Non-slack-related logic layer for dcbot.
"""
import datetime

from sqlalchemy.orm.exc import NoResultFound

from .enums import CTFFloorStatusEnum
from .db import db_session
from .models import Member, Group, RecentMemberMessage, CTFFloorStatus
from .slack_logic import sl, get_group_name, get_service_name
from .errors import BotGroupError

#
# Basic stuff
#


def populate_db(main_channel="defcon2019"):
    """
    Populate the database: Pull members information from the channel specified by @main_channel.
    """
    channel_id = sl.get_group_id(main_channel)
    populate_members(channel_id)
    populate_groups()


def populate_members(channel_id):
    """
    Populate the members table with members from channel
    """

    for member_id in sl.get_members_for_channel(channel_id):
        member_info = sl.get_member_info(member_id)
        # does this member ID exist?
        try:
            m = db_session.query(Member).\
                filter(Member.id == member_id).one()
            # update it
            m.name = member_info['name']
            m.real_name = member_info['real_name']
            m.display_name = member_info['display_name']
        except NoResultFound:
            # let's create a new one
            m = Member(member_info['id'], member_info['name'], member_info['real_name'], member_info['display_name'])
            db_session.add(m)
    db_session.commit()


def populate_groups():
    """
    Populate the groups table for service-specific groups.
    """
    service_names = sl.get_service_list()
    for service_name in service_names:
        group_id = sl.get_group_id_for_service(service_name)
        # does this group ID exist?
        try:
            g = db_session.query(Group).\
                filter(Group.id == group_id).one()
            # update it
            g.name = get_group_name(service_name)
        except NoResultFound:
            # create a new one
            g = Group(group_id, get_group_name(service_name))
            db_session.add(g)
    db_session.commit()


def get_group_id_for_service(service_name):
    """
    Get the channel ID from database for service specified by @service_name.

    :param str service_name:    Name of the service.
    :return:                    ID of the channel or None.
    """
    try:
        g = db_session.query(Group).\
            filter(Group.name == get_group_name(service_name)).one()
        return g.id
    except NoResultFound:
        return None


def get_service_for_group_id(group_id):
    """
    Get the service name from database for channel specified by @group_id.

    :param str group_id:    ID of the channel.
    :return:                Name of the service or None.
    """

    try:
        g = db_session.query(Group).\
            filter(Group.id == group_id).one()
    except NoResultFound:
        return None

    return get_service_name(g.name)


def get_service_for_service_host(user_id):
    """
    Get the service name where user specified by @user_id is a host.

    :param str user_id: Slack ID of the user.
    :return:            Service name or None.
    :rtype:             str
    """

    try:
        g = db_session.query(Group).\
            filter(Group.service_host_member_id == user_id).first()
    except NoResultFound:
        return None

    if g is None:
        return None
    return get_service_name(g.name)


def get_user_name(user_id):
    """
    Get the user name for user specified by @user_id.

    :param str user_id:     The Slack ID of the user.
    :return:                The user name or None if the user does not exist.
    """

    try:
        g = db_session.query(Member).\
            filter(Member.id == user_id).one()
        return g.name
    except NoResultFound:
        return None


def get_user_id(user_name):
    """
    Get the user ID for user specified by @user_name.

    :param str user_name:   The Slack name of the user.
    :return:                The user ID or None if the user does not exist.
    """

    try:
        g = db_session.query(Member). \
            filter(Member.name == user_name).first()
        if g is None:
            return None
        return g.id
    except NoResultFound:
        return None


def is_player(user_id):
    """
    Test if the user specified by @user_id is a player for the current CTF.

    :param str user_id: Slack ID of the user.
    :return:            True if the user is a player for the current CTF, False otherwise.
    :rtype:             bool
    """

    try:
        _ = db_session.query(Member).\
            filter(Member.id == user_id).one()
        return True
    except NoResultFound:
        return False

#
# Service hosts
#


def set_host(member_id, channel_id):
    """
    Set member specified by @member_id as the service host for service channel specified by @channel_id.

    :param str or None member_id:   Slack ID of the user.
    :param str channel_id:  Slack ID of the channel.
    :return:                None
    """

    try:
        g = db_session.query(Group).\
            filter(Group.id == channel_id).one()
    except NoResultFound:
        raise BotGroupError("Channel with ID %s is not found. Is the groups table populated?" % channel_id)

    g.service_host_member_id = member_id
    db_session.commit()


def get_host(channel_id):
    """
    Get the member ID of the service host for service channel specified by @channel_id.

    :param str channel_id:  Slack ID of the channel.
    :return:                Slack ID of the user, or None if the channel does not exist or the channel does not have a
                            service host yet.
    """

    try:
        g = db_session.query(Group).\
            filter(Group.id == channel_id).one()
    except NoResultFound:
        return None

    return g.service_host_member_id


#
# Activity monitoring
#

def set_member_recent_post(member_id, channel_id, timestamp=None):
    """
    Record the most recent post of member specified by @member_id in channel specified by @channel_id.
    """

    if timestamp is None:
        timestamp = datetime.datetime.now()

    try:
        r = db_session.query(RecentMemberMessage).\
            filter(RecentMemberMessage.group_id == channel_id).\
            filter(RecentMemberMessage.member_id == member_id).one()
        # update it
        r.recent_post_at = timestamp
    except NoResultFound:
        # create a new one
        r = RecentMemberMessage(member_id, channel_id, recent_post_at=timestamp)
        db_session.add(r)
    db_session.commit()


def get_recent_posts(channel_id):
    """
    Get a list of members' activities (recent posts) in channel specified by @channel_id.
    """
    raise NotImplementedError()


def get_slackers():
    """
    Get a list of members who haven't been active for a while.
    """
    raise NotImplementedError()


#
# CTF floor decisions
#


def set_intent(member_id):
    """
    Member specified by @member_id wants to be on the CTF floor.

    :param str member_id:
    :return:
    """
    try:
        s = db_session.query(CTFFloorStatus).\
            filter(CTFFloorStatus.member_id == member_id).one()
        s.status = CTFFloorStatusEnum.WantsToGo
    except NoResultFound:
        # create a new one
        s = CTFFloorStatus(member_id, CTFFloorStatusEnum.WantsToGo)
        db_session.add(s)
    db_session.commit()


def get_members_intents():
    """
    Get all members and their intents.

    :return:    A dict of member IDs and whether each member wants to get onto the CTF floor or not.
    """

    r = db_session.query(CTFFloorStatus).all()
    for s in r:
        yield s.member_id, s.status == CTFFloorStatusEnum.WantsToGo


def set_member_on_floor(member_id):
    """
    Set a member specified by @member_id to be on the floor.

    :return: None
    """

    try:
        s = db_session.query(CTFFloorStatus).\
            filter(CTFFloorStatus.member_id == member_id).one()
        s.status = CTFFloorStatusEnum.OnTheFloor
    except NoResultFound:
        # create a new one
        s = CTFFloorStatus(member_id, CTFFloorStatusEnum.OnTheFloor)
        db_session.add(s)
    db_session.commit()


def get_members_on_floor():
    """
    Get member IDs of all members who are on the CTF floor.

    :return:    All member IDs.
    """

    r = db_session.query(CTFFloorStatus).\
        filter(CTFFloorStatus.status == CTFFloorStatusEnum.OnTheFloor).all()
    for s in r:
        yield s.member_id
