def default_user_search(user_param='user'):
    """Returns a list containing all the default ways we like to be able to search a user by."""
    return [f'{user_param}__username', f'{user_param}__first_name', f'{user_param}__last_name', f'{user_param}__email', f'={user_param}__id']

def optimized_user_search(user_param='user'):
    """Returns optimized search fields for better admin performance."""
    # Only include the most commonly used and efficient search fields
    return [f'{user_param}__username', f'{user_param}__email', f'={user_param}__id']

def minimal_user_search(user_param='user'):
    """Returns minimal search fields for maximum performance."""
    # Only include essential search fields to minimize JOINs
    return [f'{user_param}__username', f'={user_param}__id']
