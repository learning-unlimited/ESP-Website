def default_user_search(user_param='user'):
    """Returns a list containing all the default ways we like to be able to search a user by."""
    return [f'{user_param}__username', f'{user_param}__first_name', f'{user_param}__last_name', f'{user_param}__email', f'={user_param}__id']
