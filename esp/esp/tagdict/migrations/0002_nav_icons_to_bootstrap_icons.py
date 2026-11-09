"""Convert saved navigation icons from Glyphicons to Bootstrap Icons.

The bigpicture and droplets themes now render a nav link's icon as
<i class="bi bi-NAME">, but sites set up before the Bootstrap 5 upgrade saved
Glyphicon names in the theme_template_control Tag.  Names without a close
Bootstrap Icon (e.g. the chess pieces) are left as they are; the theme setup
page's icon picker flags them for an admin to replace.
"""

import json

from django.db import migrations

#   Glyphicon names shared with Bootstrap Icons that mean the same icon are
#   omitted, so they stay as they are.
GLYPHICON_TO_BOOTSTRAP_ICON = {
    #   Same name, different icon
    'align-center': 'text-center',
    'forward': 'fast-forward',
    'fast-forward': 'skip-forward',
    'menu-down': 'caret-down-fill',
    'menu-up': 'caret-up-fill',
    'menu-left': 'caret-left-fill',
    'menu-right': 'caret-right-fill',
    #   Filled/outline pairs
    'star': 'star-fill',
    'star-empty': 'star',
    'heart': 'heart-fill',
    'heart-empty': 'heart',
    'plus-sign': 'plus-circle-fill',
    'minus-sign': 'dash-circle-fill',
    'remove-sign': 'x-circle-fill',
    'ok-sign': 'check-circle-fill',
    'question-sign': 'question-circle-fill',
    'info-sign': 'info-circle-fill',
    'exclamation-sign': 'exclamation-circle-fill',
    'remove-circle': 'x-circle',
    'ok-circle': 'check-circle',
    'ban-circle': 'ban',
    'warning-sign': 'exclamation-triangle-fill',
    'alert': 'exclamation-triangle',
    'folder-close': 'folder-fill',
    'folder-open': 'folder2-open',
    'eye-open': 'eye',
    'eye-close': 'eye-slash',
    #   Renamed
    'euro': 'currency-euro',
    'usd': 'currency-dollar',
    'gbp': 'currency-pound',
    'yen': 'currency-yen',
    'jpy': 'currency-yen',
    'bitcoin': 'currency-bitcoin',
    'btc': 'currency-bitcoin',
    'xbt': 'currency-bitcoin',
    'minus': 'dash',
    'music': 'music-note-beamed',
    'user': 'person',
    'th-large': 'grid',
    'th': 'grid-3x3',
    'th-list': 'list-ul',
    'ok': 'check',
    'remove': 'x',
    'off': 'power',
    'cog': 'gear',
    'home': 'house',
    'time': 'clock',
    'download-alt': 'download',
    'refresh': 'arrow-clockwise',
    'list-alt': 'card-list',
    'qrcode': 'qr-code',
    'barcode': 'upc',
    'print': 'printer',
    'font': 'fonts',
    'bold': 'type-bold',
    'italic': 'type-italic',
    'header': 'type-h1',
    'text-size': 'type',
    'align-left': 'text-left',
    'align-right': 'text-right',
    'align-justify': 'justify',
    'indent-left': 'text-indent-left',
    'indent-right': 'text-indent-right',
    'facetime-video': 'camera-video',
    'picture': 'image',
    'map-marker': 'geo-alt',
    'adjust': 'circle-half',
    'tint': 'droplet',
    'edit': 'pencil-square',
    'move': 'arrows-move',
    'step-backward': 'skip-start',
    'fast-backward': 'skip-backward',
    'backward': 'rewind',
    'step-forward': 'skip-end',
    'screenshot': 'crosshair',
    'share-alt': 'share',
    'resize-full': 'arrows-angle-expand',
    'resize-small': 'arrows-angle-contract',
    'resize-vertical': 'arrow-down-up',
    'resize-horizontal': 'arrow-left-right',
    'plane': 'airplane',
    'random': 'shuffle',
    'comment': 'chat',
    'retweet': 'arrow-repeat',
    'shopping-cart': 'cart',
    'bullhorn': 'megaphone',
    'certificate': 'award',
    'thumbs-up': 'hand-thumbs-up',
    'thumbs-down': 'hand-thumbs-down',
    'hand-up': 'hand-index',
    'circle-arrow-right': 'arrow-right-circle',
    'circle-arrow-left': 'arrow-left-circle',
    'circle-arrow-up': 'arrow-up-circle',
    'circle-arrow-down': 'arrow-down-circle',
    'tasks': 'list-task',
    'dashboard': 'speedometer2',
    'pushpin': 'pin',
    'sort': 'arrow-down-up',
    'sort-by-alphabet': 'sort-alpha-down',
    'sort-by-alphabet-alt': 'sort-alpha-down-alt',
    'sort-by-order': 'sort-numeric-down',
    'sort-by-order-alt': 'sort-numeric-down-alt',
    'sort-by-attributes': 'sort-down',
    'sort-by-attributes-alt': 'sort-down-alt',
    'unchecked': 'square',
    'expand': 'caret-right-square',
    'collapse-down': 'caret-down-square',
    'collapse-up': 'caret-up-square',
    'log-in': 'box-arrow-in-right',
    'log-out': 'box-arrow-right',
    'flash': 'lightning',
    'new-window': 'box-arrow-up-right',
    'import': 'box-arrow-in-down',
    'export': 'box-arrow-up',
    'floppy-disk': 'floppy',
    'floppy-saved': 'floppy',
    'floppy-remove': 'floppy',
    'floppy-save': 'floppy',
    'floppy-open': 'floppy',
    'transfer': 'arrow-left-right',
    'earphone': 'telephone',
    'phone-alt': 'telephone',
    'stats': 'bar-chart',
    'sd-video': 'badge-sd',
    'hd-video': 'badge-hd',
    'subtitles': 'badge-cc',
    'copyright-mark': 'c-circle',
    'registration-mark': 'r-circle',
    'tree-conifer': 'tree',
    'tree-deciduous': 'tree',
    'cd': 'disc',
    'save-file': 'file-earmark-arrow-down',
    'open-file': 'file-earmark-arrow-up',
    'level-up': 'arrow-90deg-up',
    'paste': 'clipboard',
    'equalizer': 'sliders',
    'blackboard': 'easel',
    'erase': 'eraser',
    'duplicate': 'files',
    'education': 'mortarboard',
    'option-horizontal': 'three-dots',
    'option-vertical': 'three-dots-vertical',
    'menu-hamburger': 'list',
    'modal-window': 'window',
    'console': 'terminal',
    'object-align-top': 'align-top',
    'object-align-bottom': 'align-bottom',
    'object-align-left': 'align-start',
    'object-align-right': 'align-end',
    'triangle-right': 'caret-right-fill',
    'triangle-left': 'caret-left-fill',
    'triangle-bottom': 'caret-down-fill',
    'triangle-top': 'caret-up-fill',
}


def convert_nav_icons(apps, schema_editor):
    Tag = apps.get_model('tagdict', 'Tag')
    for tag in Tag.objects.filter(key='theme_template_control'):
        try:
            data = json.loads(tag.value)
        except ValueError:
            continue
        nav_structure = data.get('nav_structure') if isinstance(data, dict) else None
        if not isinstance(nav_structure, list):
            continue
        changed = False
        for tab in nav_structure:
            links = tab.get('links') if isinstance(tab, dict) else None
            for link in links if isinstance(links, list) else []:
                if isinstance(link, dict) and link.get('icon') in GLYPHICON_TO_BOOTSTRAP_ICON:
                    link['icon'] = GLYPHICON_TO_BOOTSTRAP_ICON[link['icon']]
                    changed = True
        if changed:
            tag.value = json.dumps(data)
            tag.save(update_fields=['value'])


class Migration(migrations.Migration):

    dependencies = [
        ('tagdict', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(convert_nav_icons, migrations.RunPython.noop),
    ]
