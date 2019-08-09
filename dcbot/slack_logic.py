"""
Slack-related logic layer of dcbot.
"""

import time
import hmac
import hashlib

import slack

from .errors import BotUserError, BotGroupError
from .utils import get_group_name, get_service_name, group_name_prefix
from .config import APP_TOKEN, BOT_TOKEN, SIGNING_SECRET


class SlackLogic:
    def __init__(self, app, bot):
        self.app = app
        self.bot = bot

    @staticmethod
    def verify_signature(body, ts, signature):
        if abs(time.time() - float(ts.decode("ascii"))) > 60 * 5:
            # The request timestamp is more than five minutes from local time.
            # It could be a replay attack, so let's ignore it.
            return False

        sig_basestring = b'v0:' + ts + b':' + body
        sig = 'v0=' + hmac.new(
            SIGNING_SECRET,
            sig_basestring,
            hashlib.sha256,
        ).hexdigest()
        return sig == signature

    def hello_world(self, channel="#random"):
        """
        Send a hello-world message to @channel.
        """
        response = self.bot.chat_postMessage(
                channel=channel,
                text="Hello world!"
                )
        print(response)

    def yell(self, channel, message, resiliency=True):
        """
        Yell @message in @channel.

        :param str channel: Name of the channel to yell in.
        :param str message: String to yell.
        :return:            True if the message is sent successfully, False otherwise.
        """
        try:
            self.bot.chat_postMessage(
                channel=channel,
                text=message,
            )
        except slack.errors.SlackApiError as ex:
            if resiliency:
                pass
            else:
                raise BotGroupError(ex.response.get("error", "unknown error"))

    def create_group_for_service(self, service_name):
        """
        Create a private channel for a given service name. A BotGroupError will be thrown if the private channel cannot
        be created.
        """
        group_name = get_group_name(service_name)
        try:
            r = self.app.groups_create(name=group_name, validate=True)
            if r.data.get("ok", False) is True:
                return r.data['group']['id']
            raise BotGroupError(r.get("error", "unknown error"))
        except slack.errors.SlackApiError as ex:
            raise BotGroupError(ex.response.get("error", "unknown error"))

    def get_group_id_for_service(self, service_name):
        """
        Get the ID of the private channel for service specified by @service_name.
        """
        group_name = get_group_name(service_name)
        return self.get_group_id(group_name)

    def get_group_id(self, group_name):
        # enumerate all conversations
        r = self.app.conversations_list(limit=1000, types="private_channel")
        if r.data.get("ok", False) is not True:
            raise BotGroupError(r.data.get("error", "unknown error"))
        for ch in r.data['channels']:
            if ch.get("name_normalized", None) == group_name:
                return ch["id"]
        raise BotGroupError("Group %s does not exist." % group_name)

    def get_members_for_service(self, service_name):
        """
        Get a list of member IDs for service specified by @service_name.
        """
        group_id = self.get_group_id_for_service(service_name)
        return self.get_members_for_channel(group_id)

    def get_members_for_channel(self, channel_id):
        """
        Get all member IDs for a channel specified by @channel_id.
        """
        # FIXME: Fewer than the requested number of items may be returned, even if the end of the users list hasn't been reached.
        try:
            r = self.app.conversations_members(channel=channel_id, limit=100)
        except slack.errors.SlackApiError as ex:
            raise BotGroupError(ex.response.get("error", "unknown error"))
        assert r.data.get("ok", False) is True
        for member_id in r.data['members']:
            yield member_id

    def get_member_info(self, member_id):
        """
        Retrieve member info of a member specified by @member_id.
        """
        try:
            r = self.app.users_info(user=member_id)
        except slack.errors.SlackApiError as ex:
            raise BotUserError(ex.response.get("error", "unknown error"))
        assert r.data.get("ok", False) is True
        display_name = r.data['user']['profile']['display_name']
        real_name = r.data['user']['profile']['real_name']
        name = r.data['user']['name']
        return {
            'id': member_id,
            'name': name,
            'display_name': display_name,
            'real_name': real_name,
        }

    def add_member_to_service(self, member_id, service_name):
        """
        Add a member specified by @member_id to the private channel for service specified by @service_name.
        """
        # TODO: Make sure member_id is in the main defcon2019 channel (to prevent other members from joining)
        group_id = self.get_group_id_for_service(service_name)
        try:
            r = self.app.conversations_invite(channel=group_id, users=member_id)
        except slack.errors.SlackApiError as ex:
            raise BotGroupError(ex.response.get("error", "unknown_error"))

    def get_service_list(self, exclude_archived=False):
        """
        Get a list of service names and whether they are archived or not.
        """
        group_prefix = group_name_prefix()
        # TODO: Handle pagination
        try:
            r = self.app.conversations_list(limit=1000, types="private_channel",
                                            exclude_archived="true" if exclude_archived else "false")
        except slack.errors.SlackApiError as ex:
            raise BotGroupError(ex.response.get("error", "unknown error"))
        assert r.data.get("ok", False) is True
        for ch in r.data['channels']:
            if ch.get("name_normalized", "").startswith(group_prefix):
                yield get_service_name(ch["name_normalized"]), ch['is_archived']


def test():
    # create_group_for_service("serv4")
    # member_ids = list(get_members_for_service("serv4"))
    # for member_id in member_ids:
    #     print(get_member_name(member_id))
    # add_member_to_service("UM1JL2NKS", "serv3")
    # add_member_to_service("UM1JL2NKS", "serv2")
    print(list(sl.get_service_list()))



_app = slack.WebClient(token=APP_TOKEN)
_bot = slack.WebClient(token=BOT_TOKEN)
sl = SlackLogic(_app, _bot)
