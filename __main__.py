from __init__ import *
import argparse
import atexit
import json
import os
import re
import shutil
import subprocess

_DIR = os.path.dirname(os.path.realpath(__file__))
_TMP = os.path.join(_DIR, '.tmp')

def save_progress():
  with open(_TMP, 'w') as f:
    f.write(json.dumps({
      k: v for k, v in globals().items()
      if type(v) in [str, bytes] and not k.startswith('_')
    }))

def check_progress():
  if not os.path.exists(_TMP): return False
  with open(_TMP) as f:
    return json.loads(f.read())['progress'] != 'complete'

def load_progress():
  with open(_TMP) as f:
    globals().update(json.loads(f.read()))

def find_replace_copy(src, find_replace, dst):
  with open(src) as file: contents = file.read()
  for find, replace in find_replace.items():
    contents = contents.replace(find, replace)
  with open(dst, 'w') as file: file.write(contents)

def lower_kebab_case(s): return s.lower().replace('_', '-')
def snake_case(s): return s.replace('-', '_')
def lower_snake_case(s): return snake_case(s.lower())
def camel_case(s): return s.title().replace('_', '')

parser = make_parser()
parser.add_argument('--create', dest='name')
args = parser.parse_args()

if not args.name:
  def find_folder_with(file_name):
    for i in os.listdir('.'):
      if os.path.isdir(i):
        if os.path.exists(os.path.join(i, file_name)):
          return i
  project = find_folder_with('settings.py')
  app = find_folder_with('apps.py')
  sys.path.append(project)
  import settings
  database = settings.DATABASES['default']
  try:
    heroku_info = invoke('heroku', 'info', '-s', stdout=True, shell=True, quiet=True)
  except subprocess.CalledProcessError as e:
    heroku_info = ''
  match = re.search('web_url=(.*)', heroku_info)
  heroku_url = match and match.group(1) or None
  main(args,
    project=project,
    app=app,
    db_name=database['NAME'],
    db_user=database['USER'],
    heroku_url=heroku_url,
    db_password=database['PASSWORD'],
  )
  sys.exit()

if check_progress(): load_progress()
else: progress = 'fresh'
atexit.register(save_progress)

project = 'proj_' + snake_case(args.name)
app = snake_case(args.name)
db_name = 'db_' + lower_snake_case(args.name)
db_user = 'u_' + lower_snake_case(args.name)

if progress == 'fresh':
  #create heroku app with given name, or fail now if it's taken
  heroku_create_stdout = invoke('heroku', 'create', lower_kebab_case(args.name), stdout=True, shell=True)
  progress = 'heroku create'

#=====bookkeeping=====#
start = os.getcwd()
os.chdir(_DIR)
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
diff = len(subprocess.check_output(['git', 'diff', 'HEAD'])) != 0
os.chdir(start)
#=====django start project=====#
if progress == 'heroku create':
  os.mkdir(args.name)
  invoke('django-admin', 'startproject', project, args.name)
  progress = 'django project start'
os.chdir(args.name)
#=====heroku=====#
#Procfile
find_replace_copy(
  os.path.join(_DIR, 'Procfile'),
  {'{project}': project},
  'Procfile',
)
#app.json
shutil.copy(os.path.join(_DIR, 'app.json'), '.')
#Pipfile
shutil.copy(os.path.join(_DIR, 'Pipfile'), '.')
if progress == 'django project start':
  invoke('pipenv', '--three')
  progress = 'pipenv three'
if progress == 'pipenv three':
  invoke('pipenv', 'install')
  progress = 'pipenv install'
#create
heroku_url, heroku_repo = re.search(r'(.+) \| (.+)\n', heroku_create_stdout).groups()
heroku_app = re.search('https://([^.]+)', heroku_url).group(1)
#=====django=====#
#app
if progress == 'pipenv three':
  invoke('python3', 'manage.py', 'startapp', app)
  progress = 'manage start app'
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
    ).format(db_name, db_user, db_name.upper()),
    (
'''\
STATIC_URL = '/static/'\
'''
    ): (
'''\
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

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

if os.environ.get('DJANGOGO_ENV') != 'local':
    import django_heroku
    django_heroku.settings(locals())\
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
    ).format(app, camel_case(app) + 'Config'),
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
    ),
    'DEBUG = True': 'DEBUG = False',
  },
  os.path.join(project, 'settings.py'),
)
#settings_debug.py
shutil.copy(os.path.join(_DIR, 'settings_debug.py'), project)
#=====go.py=====#
def literalify(string): return "'{}'".format(string)
find_replace_copy(
  os.path.join(_DIR, 'go.py'),
  {
    '{project}'    : literalify(project),
    '{app}'        : literalify(app),
    '{db_name}'    : literalify(db_name),
    '{db_user}'    : literalify(db_user),
    '{heroku_url}' : literalify(heroku_url),
    '{heroku_repo}': literalify(heroku_repo),
  },
  'go.py',
)
#=====git=====#
shutil.copy(os.path.join(_DIR, '.gitignore'), '.')
invoke('git', 'init', '.')
os.mkdir('deps')
invoke('git', 'submodule', 'add', 'https://github.com/dansgithubuser/djangogo', 'deps/djangogo')
invoke('git', 'add', '.')
invoke('git', 'commit', '-m', 'initial commit created by djangogo ' + commit + (' with diff' if diff else ''))
invoke('git', 'remote', 'add', 'heroku', 'https://git.heroku.com/{}.git'.format(heroku_app))

progress = 'complete'
