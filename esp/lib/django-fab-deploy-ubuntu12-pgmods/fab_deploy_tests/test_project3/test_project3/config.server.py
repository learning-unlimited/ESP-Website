# config file for environment-specific settings

DEBUG = True
DATABASES = {
    'default': {
#        'ENGINE': 'django.contrib.gis.db.backends.postgis',
#        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'ENGINE': '{{ DJANGO_DB_ENGINE }}',
        'NAME': '{{ DB_NAME }}',
        'USER': '{{ DB_USER }}',
        'PASSWORD': '{{ DB_PASSWORD }}',
    }
}
INSTANCE_NAME = '{{ INSTANCE_NAME }}'

GEO = 'gis' in '{{ DJANGO_DB_ENGINE }}'
