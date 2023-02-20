#! /usr/bin/env python3

#===== imports =====#
import argparse
import datetime
import os
import re
import secrets
import string
import subprocess
import sys

#===== args =====#
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()

# db
parser.add_argument('--db-create', '--dbc', action='store_true', help='Create local database for this project.')
parser.add_argument('--db-drop', '--dbd', action='store_true', help='Drop local database for this project.')
parser.add_argument('--db-user-create', '--dbuc', action='store_true', help='Create local database user for this project.')
parser.add_argument('--db-user-drop', '--dbud', action='store_true', help='Drop local database user for this project. Database must be dropped first.')

# development
manage_parser = subparsers.add_parser('manage', aliases=['m'], help='Run manage.py with given args. Useful for --env. Example: `./do.py --env dev m -- --help`')
manage_parser.add_argument('manage', nargs='*')
parser.add_argument('--run', '-r', action='store_true')

# docker
parser.add_argument('--docker-build', '--dkrb', action='store_true')
parser.add_argument('--docker-create-env-files', '--dkre', nargs='+', metavar='<allowed host>')
parser.add_argument('--docker-run', '--dkrr', action='store_true')
parser.add_argument('--docker-setup-db', '--dkrd', action='store_true')

# env
parser.add_argument('--env', '-e', choices=['dev', 'prod'], default='dev')

args = parser.parse_args()

#===== consts =====#
DIR = os.path.dirname(os.path.realpath(__file__))

#===== setup =====#
os.chdir(DIR)
if args.env == 'dev':
    os.environ['DJANGOGO_ENV'] = 'development'
else:
    os.environ['DJANGOGO_ENV'] = 'production'

#===== helpers =====#
def blue(text):
    return '\x1b[34m' + text + '\x1b[0m'

def timestamp():
    return '{{:%Y-%m-%d %H:%M:%S.%f}}'.format(datetime.datetime.now())

def invoke(
    *args,
    popen=False,
    no_split=False,
    out=False,
    quiet=False,
    hide=[],
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
            for i in args:
                for h in hide:
                    i = i.replace(h, '***')
                print(f'\t{{i}} \\')
        else:
            for i, v in enumerate(args):
                if i != len(args)-1:
                    end = ' '
                else:
                    end = ';\n'
                for h in hide:
                    v = v.replace(h, '***')
                print(v, end=end)
        if kwargs: print(kwargs)
        if popen: print('popen')
        print()
    if kwargs.get('env') != None:
        env = os.environ.copy()
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

def psql(command):
    invoke('sudo', 'su', '-c', f'psql -c "{{command}}"', 'postgres')

def make_secret():
    return ''.join(
        secrets.choice(string.ascii_letters + string.digits)
        for i in range(32)
    )

def git_state():
    diff = invoke('git diff', out=True)
    diff_cached = invoke('git diff --cached', out=True)
    with open('git-state.txt', 'w') as git_state:
        git_state.write(invoke('git show --name-only', out=True)+'\n')
        if diff:
            git_state.write('\n===== diff =====\n')
            git_state.write(diff+'\n')
        if diff_cached:
            git_state.write('\n===== diff --cached =====\n')
            git_state.write(diff_cached+'\n')

def docker_psql(command, db=None, hide=[]):
    args = ['docker', 'exec', 'magic_linker-db', 'psql', '-U', 'postgres', '-c', command]
    if db:
        args.extend(['-d', db])
    invoke(*args, hide=hide)

#===== main =====#
if len(sys.argv) == 1:
    parser.print_help()
    sys.exit()

if args.db_create:
    psql('CREATE DATABASE {db_name}')

if args.db_drop:
    psql('DROP DATABASE {db_name}')

if args.db_user_create:
    psql(f"CREATE USER {db_user} WITH PASSWORD 'dev'")
    psql('GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user}')
    psql('GRANT ALL ON SCHEMA public TO {db_user}')

if args.db_user_drop:
    psql('DROP USER {db_user}')

if hasattr(args, 'manage'):
    invoke('./manage.py', *args.manage)

if args.run:
    invoke('./manage.py', 'runserver', '0.0.0.0:8000')

if args.docker_build:
    git_state()
    invoke('docker build -t {name}:latest .')

if args.docker_create_env_files:
    allowed_hosts = ' '.join(args.docker_create_env_files)
    secret_key = make_secret()
    db_password = make_secret()
    with open('env', 'w') as f:
        lines = [
            'DJANGOGO_ENV=production',
            f'SECRET_KEY={{secret_key}}',
            f'ALLOWED_HOSTS="{{allowed_hosts}}"',
            f'DB_PASSWORD={{db_password}}',
            'DB_HOST=db',
        ]
        for line in lines:
            f.write(line + '\n')
    with open('env-db', 'w') as f:
        lines = [
            f'POSTGRES_PASSWORD={{db_password}}',
        ]
        for line in lines:
            f.write(line + '\n')

if args.docker_run:
    invoke('docker compose up -d')

if args.docker_setup_db:
    with open('env-db') as f:
        env = f.read()
    db_password = re.match('POSTGRES_PASSWORD=(.+)$', env).group(1)
    docker_psql('CREATE DATABASE {db_name}')
    docker_psql(f"CREATE USER {db_user} WITH PASSWORD '{{db_password}}'", hide=[db_password])
    docker_psql('GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user}')
    docker_psql('GRANT ALL ON SCHEMA public TO {db_user}', db='{db_name}')
    invoke('docker', 'exec', 'magic_linker-main', './do.py', '--env', 'prod', 'm', 'migrate')
