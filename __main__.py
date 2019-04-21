from __init__ import *
import argparse
import os
import re
import shutil
import subprocess

DIR = os.path.dirname(os.path.realpath(__file__))

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

project = 'proj_' + snake_case(args.name)
app = snake_case(args.name)
db_name = 'db_' + lower_snake_case(args.name)
db_user = 'u_' + lower_snake_case(args.name)

#create heroku app with given name, or fail now if it's taken
heroku_create_stdout = invoke('heroku', 'create', lower_kebab_case(args.name), stdout=True, shell=True)

#=====bookkeeping=====#
start = os.getcwd()
os.chdir(DIR)
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
diff = len(subprocess.check_output(['git', 'diff', 'HEAD'])) != 0
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
shutil.copy(os.path.join(DIR, 'app.json'), '.')
#Pipfile
shutil.copy(os.path.join(DIR, 'Pipfile'), '.')
invoke('pipenv', '--three')
invoke('pipenv', 'install')
#create
heroku_url, heroku_repo = re.search(r'(.+) \| (.+)\n', heroku_create_stdout).groups()
heroku_app = re.search('https://([^.]+)', heroku_url).group(1)
#=====django=====#
#app
invoke('python3', 'manage.py', 'startapp', app)
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
shutil.copy(os.path.join(DIR, 'settings_debug.py'), project)
#=====go.py=====#
def literalify(string): return "'{}'".format(string)
find_replace_copy(
  os.path.join(DIR, 'go.py'),
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
shutil.copy(os.path.join(DIR, '.gitignore'), '.')
invoke('git', 'init', '.')
os.mkdir('deps')
invoke('git', 'submodule', 'add', 'https://github.com/dansgithubuser/djangogo', 'deps/djangogo')
invoke('git', 'add', '.')
invoke('git', 'commit', '-m', 'initial commit created by djangogo ' + commit + (' with diff' if diff else ''))
invoke('git', 'remote', 'add', 'heroku', 'https://git.heroku.com/{}.git'.format(heroku_app))
