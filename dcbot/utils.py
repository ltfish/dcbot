
import string


def user_text_to_user_id(user_text):
    """
    Convert a user-related string (Slack user ID, user name, formatted Slack user ID) to a user ID.

    :param str user_text:
    :return:
    """

    from .logic import get_user_id

    CHARSET = string.ascii_letters + string.digits

    if user_text.startswith("<@") and user_text.endswith(">") and len(user_text) == 12:
        # Slack user ID
        return user_text[2:-1]
    elif len(user_text) == 9 and all(chr in CHARSET for chr in user_text):
        # Slack user ID
        return user_text
    elif user_text.startswith("@"):
        # user name
        return get_user_id(user_text[1:])
    else:
        # user name
        return get_user_id(user_text)


def group_name_prefix():
    return "defcon2019-"


def get_group_name(service_name):
    """
    Generate a private channel name for a service name.
    """
    group_name = "%s%s" % (group_name_prefix(), service_name)
    return group_name


def get_service_name(group_name):
    """
    Get the name of a service from its corresponding group name.
    """
    prefix = group_name_prefix()
    if not group_name.startswith(prefix):
        raise ValueError("Group name %s does not start with the group name prefix %s." % (group_name, prefix))
    return group_name[len(prefix):]