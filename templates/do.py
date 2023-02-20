#! /usr/bin/env python3

#===== imports =====#
import dotenv

import argparse
import datetime
import os
import re
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
manage_parser = subparsers.add_parser('manage', aliases=['m'], help='Load .env and run manage.py with given args. Example: `./do.py m -- --help`')
manage_parser.add_argument('manage', nargs='*')
parser.add_argument('--run', '-r', action='store_true')

args = parser.parse_args()

#===== consts =====#
DIR = os.path.dirname(os.path.realpath(__file__))

#===== setup =====#
os.chdir(DIR)
assert dotenv.load_dotenv('env.dev')

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
            for i in args: print(f'\t{{i}} \\')
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

#===== main =====#
if len(sys.argv) == 1:
    parser.print_help()
    sys.exit()

if args.db_create:
    psql('CREATE DATABASE {db_name}')

if args.db_drop:
    psql('DROP DATABASE {db_name}')

if args.db_user_create:
    db_password = os.environ['DB_PASSWORD']
    psql(f"CREATE USER {db_user} WITH PASSWORD '{{db_password}}'")
    psql('GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user}')

if args.db_user_drop:
    psql('DROP USER {db_user}')

if hasattr(args, 'manage'):
    invoke('./manage.py', *args.manage)

if args.run:
    invoke('./manage.py', 'runserver', '0.0.0.0:8000')
