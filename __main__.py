from __init__ import *
import argparse
import os
import re
import subprocess

DIR=os.path.dirname(os.path.realpath(__file__))

def find_replace_copy(src, find_replace, dst):
	with open(src) as file: contents=file.read()
	for find, replace in find_replace.items():
		contents=contents.replace(find, replace)
	with open(dst, 'w') as file: file.write(contents)

parser=argparse.ArgumentParser()
parser.add_argument('name')
args=parser.parse_args()
project=args.name+'_proj'
database=args.name+'_database'
user=args.name+'_user'

#=====bookkeeping=====#
start=os.getcwd()
os.chdir(DIR)
commit=subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
diff=len(subprocess.check_output(['git', 'diff', 'HEAD']))!=0
os.chdir(start)
#=====django start project=====#
os.mkdir(args.name)
invoke('django-admin', 'startproject', project, args.name)
os.chdir(args.name)
#=====heroku=====#
#Procfile
find_replace_copy(
	os.path.join(DIR, 'Procfile'),
	{'{project}': project},
	'Procfile',
)
#app.json
invoke('cp', os.path.join(DIR, 'app.json'), '.')
#Pipfile
invoke('cp', os.path.join(DIR, 'Pipfile'), '.')
invoke('pipenv', '--three')
invoke('pipenv', 'install')
#create
stdout=invoke('heroku', 'create', stdout=True)
heroku_url, heroku_repo=re.search(r'(.+) \| (.+)\n', stdout).groups()
heroku_app=re.search('https://([^.]+)', heroku_url).group(1)
#=====django=====#
#app
invoke('python3', 'manage.py', 'startapp', args.name)
#settings.py
find_replace_copy(
	os.path.join(project, 'settings.py'),
	{
		(
'''\
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }\
'''
		): (
'''\
    'default': {{
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '{}',
        'USER': '{}',
        'PASSWORD': os.environ.get('{}_PASSWORD', 'dev-password'),
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }}\
'''
		).format(database, user, database.upper()),
		(
'''\
STATIC_URL = '/static/'\
'''
		): (
'''\
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'static')

# from manage.py check --deploy
SECURE_HSTS_SECONDS = 3600
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

try:
    import django_heroku
    django_heroku.settings(locals())
except Exception as e: print(e)\
'''
		),
		(
'''\
ALLOWED_HOSTS = []\
'''
		): (
'''\
ALLOWED_HOSTS = [
    '{}',
]\
'''
		).format(heroku_url),
		(
'''\
INSTALLED_APPS = [\
'''
		): (
'''\
INSTALLED_APPS = [
    '{}.apps.{}',\
'''
		).format(args.name, args.name.capitalize()+'Config'),
		(
'''\
MIDDLEWARE = [\
'''
		): (
'''\
if os.environ.get('DJANGOGO_ENV', None) == 'local':
    INSTALLED_APPS.append('django_extensions')

MIDDLEWARE = [\
'''
		).format(args.name, args.name.capitalize()+'Config'),
		'DEBUG = True': 'DEBUG = False',
	},
	os.path.join(project, 'settings.py'),
)
#settings_debug.py
invoke('cp', os.path.join(DIR, 'settings_debug.py'), project)
#=====go.py=====#
def literalify(string): return "'"+string+"'"
find_replace_copy(
	os.path.join(DIR, 'go.py'),
	{
		'{project}'   : literalify(project),
		'{app}'       : literalify(args.name),
		'{database}'  : literalify(database),
		'{user}'      : literalify(user),
		'{heroku_url}': literalify(heroku_url),
	},
	'go.py',
)
#=====git=====#
invoke('cp', os.path.join(DIR, '.gitignore'), '.')
invoke('git', 'init', '.')
invoke('mkdir', 'deps')
invoke('git', 'submodule', 'add', 'https://github.com/dansgithubuser/djangogo', 'deps/djangogo')
invoke('git', 'add', '.')
invoke('git', 'commit', '-m', 'initial commit created by djangogo '+commit+(' with diff' if diff else ''))
invoke('git', 'remote', 'add', 'heroku', 'https://git.heroku.com/{}.git'.format(heroku_app))
