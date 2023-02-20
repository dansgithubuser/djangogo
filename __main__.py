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
parser.add_argument('--project-name', default='proj')
parser.add_argument('--app-name', default='app')
args = parser.parse_args()

#===== consts =====#
DIR = os.path.dirname(os.path.realpath(__file__))

#===== helpers =====#
def blue(text):
    return '\x1b[34m' + text + '\x1b[0m'

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
        print(blue('-'*40))
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

def render_template(src, dst, subs={}):
    with open(f'{DIR}/templates/{src}') as f:
        contents = f.read()
    contents = contents.format(**subs)
    with open(dst, 'w') as f:
        f.write(contents)

#===== main =====#
django_version = invoke('django-admin version', out=True)

# django project & git init
os.mkdir(args.name)
invoke(f'django-admin startproject {args.project_name} {args.name}')
os.chdir(args.name)
invoke('git init .')
invoke('git add .')
invoke('git', 'commit', '-m', f'django-admin startproject {args.project_name} {args.name} - django {django_version}')

# django app
invoke(f'./manage.py startapp {args.app_name}')
invoke('git add .')
invoke('git', 'commit', '-m', f'./manage.py startapp {args.app_name}')

# .gitignore
render_template('gitignore', '.gitignore')
