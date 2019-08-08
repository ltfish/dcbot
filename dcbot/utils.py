
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