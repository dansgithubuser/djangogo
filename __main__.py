#===== imports =====#
import argparse
import copy
import datetime
import os
import re
import subprocess
import sys

#===== args =====#
parser = argparse.ArgumentParser(description='Start a project in `./{name}`')
parser.add_argument('name')
parser.add_argument('--proj-name', default='proj')
parser.add_argument('--app-name', default='app')
parser.add_argument('--port', type=int, default=8000)
args = parser.parse_args()

#===== consts =====#
DIR = os.path.dirname(os.path.realpath(__file__))

#===== helpers =====#
def blue(text):
    return '\x1b[34m' + text + '\x1b[0m'

def print_separator():
    print(blue('-'*40))

def timestamp():
    return '{:%Y-%m-%d %H:%M:%S.%f}'.format(datetime.datetime.now())

def invoke(
    *args,
    popen=False,
    no_split=False,
    out=False,
    quiet=False,
    **kwargs,
):
    if len(args) == 1 and not no_split:
        args = args[0].split()
    if not quiet:
        print_separator()
        print(timestamp())
        print(os.getcwd()+'$', end=' ')
        if any([re.search(r'\s', i) for i in args]):
            print()
            for i in args: print(f'\t{i} \\')
        else:
            for i, v in enumerate(args):
                if i != len(args)-1:
                    end = ' '
                else:
                    end = ';\n'
                print(v, end=end)
        if kwargs: print(kwargs)
        if popen: print('popen')
        print()
    if kwargs.get('env') != None:
        env = copy.copy(os.environ)
        env.update(kwargs['env'])
        kwargs['env'] = env
    if popen:
        return subprocess.Popen(args, **kwargs)
    else:
        if 'check' not in kwargs: kwargs['check'] = True
        if out: kwargs['capture_output'] = True
        result = subprocess.run(args, **kwargs)
        if out:
            result = result.stdout.decode('utf-8')
            if out != 'exact': result = result.strip()
        return result

def render_template(src, dst=None, subs=None):
    if dst == None:
        dst = src
    print_separator()
    print(src, '-->', dst)
    with open(f'{DIR}/templates/{src}') as f:
        contents = f.read()
    if subs:
        contents = contents.format(**subs)
    with open(dst, 'w') as f:
        f.write(contents)

#===== main =====#
# accounting
wd = os.getcwd()
django_version = invoke('django-admin version', out=True)
os.chdir(DIR)
djangogo_version = invoke('git rev-parse HEAD', out=True)
if invoke('git diff', out=True) or invoke('git diff --cached', out=True):
    djangogo_version += ' with diff'
os.chdir(wd)
subs = {
    'name': args.name,
    'proj_name': args.proj_name,
    'app_name': args.app_name,
    'db_name': args.name.lower(),
    'db_user': 'u_' + args.name.lower(),
    'port': args.port,
}

# django project & git init
os.mkdir(args.name)
invoke(f'django-admin startproject {args.proj_name} {args.name}')
os.chdir(args.name)
invoke('git init .')
render_template('gitignore', '.gitignore')
invoke('git add .')
invoke('git', 'commit', '-m', f'django-admin startproject {args.proj_name} {args.name} - django {django_version}')

# django app
invoke(f'./manage.py startapp {args.app_name}')
invoke('git add .')
invoke('git', 'commit', '-m', f'./manage.py startapp {args.app_name}')

# settings
render_template('settings.py', f'{args.proj_name}/settings.py', subs)

# URLs
render_template('app_urls.py', f'{args.app_name}/urls.py', subs)
render_template('proj_urls.py', f'{args.proj_name}/urls.py', subs)

# views
render_template('views.py', f'{args.app_name}/views.py')

# templates
os.mkdir(f'{args.app_name}/templates')
os.mkdir(f'{args.app_name}/templates/registration')
render_template('base.html', f'{args.app_name}/templates/base.html', subs)
render_template('home.html', f'{args.app_name}/templates/home.html')
render_template('login.html', f'{args.app_name}/templates/registration/login.html')

# do.py
render_template('do.py', subs=subs)
os.chmod('do.py', 0o775)

# requirements.txt
render_template('requirements.txt')

# docker
render_template('Dockerfile', subs=subs)
render_template('docker-compose.yml', subs=subs)

# final git commit
invoke('git add .')
invoke('git', 'commit', '-m', f'djangogo setup complete - djangogo {djangogo_version}')
