def default_user_search(user_param='user'):
    """Returns a list containing all the default ways we like to be able to search a user by."""
    return [i % user_param for i in ['%s__username', '%s__first_name', '%s__last_name', '%s__email', '=%s__id']]
