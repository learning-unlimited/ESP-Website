from esp.themes.controllers import ThemeController

from django import template

import os.path
import json

register = template.Library()

def count_matching_chars(url, link):
    """ Determines the length of the common substring at the beginning of
        url and link up to a path boundary. Used to identify the best matching tab.
    """
    if not url or not link:
        return 0

    match_len = 0
    for i in range(min(len(url), len(link))):
        if url[i] == link[i]:
            match_len += 1
        else:
            break

    boundaries = ('/', '?', '#')

    # Check if the match stops in the middle of a path segment.
    # This happens if either string has more characters and the next character is NOT a boundary.
    url_bad = (match_len < len(url) and url[match_len] not in boundaries)
    link_bad = (match_len < len(link) and link[match_len] not in boundaries)

    if match_len > 0 and (url_bad or link_bad):
        # The match ended inside a word (e.g., 'ideas' vs 'ideas.html', or 'index' vs 'ideas').
        # Backtrack to the last slash to ensure we only match full directories.
        last_slash = url[:match_len].rfind('/')
        if last_slash != -1:
            match_len = last_slash + 1
        else:
            match_len = 0

    return match_len

@register.filter
def mux_tl(str, type):
    splitstr = str.split("/") # String should be of the format "/learn/foo/bar/index.html"
    if len(splitstr) < 2 or splitstr[0] != "":
        return str
    elif splitstr[1] in ("teach", "learn", "manage", "onsite", "volunteer"):
        return f"/{type}/" + "/".join(splitstr[2:])
    else:
        return str

@register.filter
def split(str, splitter):
    return str.split(splitter)

@register.filter
def index(arr, index):
    try:
        return arr[index]
    except IndexError:
        return ''

@register.filter
def concat(str, text):
    return str + text

@register.filter
def equal(obj1, obj2):
    return obj1 == obj2

@register.filter
def notequal(obj1, obj2):
    return obj1 != obj2

@register.filter
def bool_or(obj1, obj2):
    return obj1 or obj2

@register.filter
def bool_and(obj1, obj2):
    return obj1 and obj2

@register.filter
def get_field(object, field):
    return getattr(object, field)

@register.filter
def regexsite(str):
    return str.replace(".", r"\.")

@register.filter
def extract_theme(url):
    #   Get the appropriate color scheme out of the Tag that controls nav structure
    #   (specific to MIT theme)
    tab_index = 0
    tc = ThemeController()
    settings = tc.get_template_settings()
    max_chars_matched = 0
    for category in settings['nav_structure']:
        num_chars_matched = count_matching_chars(url, category['header_link'])
        if num_chars_matched > max_chars_matched:
            max_chars_matched = num_chars_matched
            tab_index = 0
        i = 1
        for item in category['links']:
            num_chars_matched = count_matching_chars(url, item['link'])
            # Prefer the sub-link if it's a strictly longer match, OR if it matches
            # equally well but is an exact match of the link's URL. This prevents
            # the header base color from continuously overriding the tab link color.
            if num_chars_matched > max_chars_matched or (num_chars_matched == max_chars_matched and num_chars_matched == len(item['link'])):
                max_chars_matched = num_chars_matched
                tab_index = i
            i += 1
    return f'tabcolor{tab_index}'

@register.filter
def get_nav_category(path):
    tc = ThemeController()
    settings = tc.get_template_settings()
                #   Search for current nav category based on request path
    first_level = ''.join(path.lstrip('/').split('/')[:1])
    for category in settings['nav_structure']:
        if category['header_link'].lstrip('/').startswith(first_level):
            return category
    #   Search failed - use default nav category
    default_nav_category = 'learn'
    for category in settings['nav_structure']:
        if category['header_link'].lstrip('/').startswith(default_nav_category):
            return category

@register.filter
def truncatewords_char(value, arg):
    """
    Truncates a string before a certain number of characters,
    using as many complete words as possible.

    Argument: Number of characters to truncate before.
    """
    try:
        length = int(arg)
    except ValueError: # Invalid literal for int().
        return value # Fail silently.

    txt_spaces = value.split()
    txt_result = ''
    for item in txt_spaces:
        if len(txt_result) + 1 + len(item) < length:
            txt_result += ' ' + item
        else:
            txt_result += ' ...'
            break

    return txt_result

@register.filter
def as_form_label(str):
    return str.replace('_', ' ').capitalize()
