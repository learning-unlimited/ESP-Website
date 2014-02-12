#!/usr/bin/env python
from distutils.core import setup

for cmd in ('egg_info', 'develop', 'upload_sphinx', 'build_sphinx'):
    import sys
    if cmd in sys.argv:
        from setuptools import setup

if 'sdist' in sys.argv:
    # do not skip git files
    sys.argv.insert(sys.argv.index('sdist') + 1, '--no-prune')

version='0.8a1'

setup(
    name='django-fab-deploy',
    version=version,
    author='Mikhail Korobov',
    author_email='kmike84@gmail.com',

    packages=['fab_deploy', 'fab_deploy.vcs', 'fab_deploy.db', 'fab_deploy.webserver'],
    package_data={
        'fab_deploy': [
            'config_templates/*.config',
            'config_templates/*.py',
            'example_reqs/*.txt',
        ]
    },

    scripts = ['bin/django-fab-deploy'],

    url='https://bitbucket.org/kmike/django-fab-deploy/',
    download_url = 'https://bitbucket.org/kmike/django-fab-deploy/get/%s.zip' % version,
    license = 'MIT license',
    description = """ Django deployment tool """,

    long_description = open('README.rst').read() + open('docs/CHANGES.rst').read(),
    requires = ['Fabric (>=1.4.0)', 'jinja2', 'taskset (>= 0.1, < 0.2)'],

    classifiers=(
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ),
)
