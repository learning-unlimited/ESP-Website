#!/usr/bin/python

import os,sys

args = sys.argv[1:]
images = ['search','login','signup','corners_body','corners_main','tab','corners_submenu','overtab','overtab_active']

options = {
    'css':False,
    'files':[]
}

for arg in args:
    if arg == 'css':
        options['css'] = True
    elif arg == 'all':
        options['files'] = images[:]
    elif arg in images:
        options['files'].append(arg)
    else:
        print "Unrecognized option: '%s'" % arg

options['files'] = set(options['files'])

colors = [
  ['yellowgreen', 'yg', 0x88cf00, 0x56a900, 0x3f7a00],
  ['blue',        'bl', 0x3dc0ff, 0x1c6ad2, 0x1041ba],
  ['purple',      'pu', 0x7932e3, 0x63118c, 0x4f0873],
  ['red',         're', 0xd45437, 0xa61031, 0x8c0724],
  ['orange',      'or', 0xff9d00, 0xe36200, 0xc95700],
  ['yellow',      'ye', 0xedb600, 0xd49800, 0xba8200],
  ['lightgreen',  'lg', 0x8cc63f, 0x5b7228, 0x45591b],
  ['darkgreen',   'dg', 0x478a00, 0x2d4217, 0x20300f],
  ['grey',        'gr', 0x666666, 0x212121, 0x000000],
  ['black',       'bk', 0x231f20, 0xff0045, 0xcc0036]
  ]

if options['css']:
    css = open('build/theme.css','w')

for name,short,fore,back,accent in colors:
    os.system(
        ''.join([
                'cat %s.svg | sed "s/FORE/%06x/;s/BACK/%06x/;s/ACCENT/%06x/" > build/%s_%s.svg;' % (image, fore, back, accent, short, image) +
                #'inkscape -z -f build/%s_%s.svg -e build/%s_%s.png' % (short, image, short, image)
                #'rsvg-convert build/%s_%s.svg -o build/%s_%s.png;' % (short, image, short, image)
                'convert build/%s_%s.svg build/%s_%s.png;' % (short, image, short, image)
            for image in options['files']
        ]))
    if options['css']:
        css.write(
            '\n'.join([
                '/* %s %s #%06x #%06x #%06x */' % (name, short, fore, back, accent),
                '#page.%s .forecolor { color: #%06x; }' % (name, fore),
                '#page.%s .backcolor { color: #%06x; }' % (name, back),
                '#page.%s .accentcolor { color: #%06x; }' % (name, accent),
                '#page.%s #main > .corners div { background-image: url(/media/images/theme/gen/%s_corners_main.png); }' % (name, short),
                '#page.%s #body { background: #%06x; }' % (name, fore),
                '.%s a { color: #%06x; }' % (name, accent), # boosting this with an id reference overrides *every* link on the page
                '#page.%s #body > .corners div { background-image: url(/media/images/theme/gen/%s_corners_body.png); }' % (name, short),
                '#page.%s #search_box { background: #fff url(/media/images/theme/gen/%s_search.png) no-repeat 0% 0% scroll; }' % (name, short),
                '#page.%s #login_submit { background: #fff url(/media/images/theme/gen/%s_login.png) no-repeat 0% 0% scroll; }' % (name, short),
                '#page.%s #login_signup { background: #fff url(/media/images/theme/gen/%s_signup.png) no-repeat 0% 0% scroll; }' % (name, short),
                #'li.%s { background: #fff; background-image: url(/media/images/theme/gen/%s_tab.png); }' % (name, short),
                'li.%s a { background-color: #%06x; background-image: url(/media/images/theme/gen/%s_tab.png); }' % (name, fore, short),
                #'li.%s a { background: #%06x; background-image: url(/media/images/theme/gen/%s_tab.png); }' % (name, fore, short),
                '#page.%s #menu li.%s { margin-left: 0; width: 130px }' % (name, name),
                '#page.%s #submenu { background: #%06x; }' % (name, accent),
                '#page.%s #content_header { background: #%06x; }' % (name, back),
                '#page.%s #content_header > .corners div { background-image: url(/media/images/theme/gen/%s_corners_submenu.png); }' % (name, short),
                #'#page.%s #submenu a { color: #%06x; }' % (name, fore),
                '#page.%s #cross_link .inactive a { background-image: url(/media/images/theme/gen/%s_overtab.png); }' % (name, short),
                '#page.%s #cross_link a { background-image: url(/media/images/theme/gen/%s_overtab_active.png); }' % (name, short),
                '\n'
                ])
            )

if options['css']:
    css.close();
