from collections import defaultdict
import argparse
import os
import re
import subprocess
import sys
import time
import webbrowser

def make_parser():
  parser = argparse.ArgumentParser()
  #setup
  parser.add_argument('--create-database', action='store_true', help='create local database for this project')
  parser.add_argument('--drop-database', action='store_true', help='drop local database for this project')
  parser.add_argument('--create-user', action='store_true', help='create local database user for this project')
  parser.add_argument('--drop-user', action='store_true', help='drop local database user for this project; database must be dropped first')
  parser.add_argument('--freshen-database', action='store_true', help='drop database, drop user, create database, create user, run migrations')
  #development
  parser.add_argument('--manage', '-m', nargs='*', help='set up djangogo env and run manage.py with given args')
  parser.add_argument('--run', '-r', action='store_true', help='run server locally')
  parser.add_argument('--show-urls', '-u', action='store_true', help='show exposed URLs')
  parser.add_argument('--install', '--ins', action='store_true', help='update Pipfile.lock wrt Pipfile')
  parser.add_argument('--interact', '-i', action='store_true', help='enter interactive Python with models imported')
  #heroku
  parser.add_argument('--deploy', '-d', action='store_true', help='deploy to heroku')
  parser.add_argument('--heroku-log', '-l', action='store_true', help='tail heroku server log')
  parser.add_argument('--heroku-bash', '-b', action='store_true', help='psql to heroku database')
  parser.add_argument('--heroku-psql', '-s', action='store_true', help='psql to heroku database')
  parser.add_argument('--heroku-remote-add', '--hra', action='store_true')
  parser.add_argument('--heroku-browser', '--hb', action='store_true', help='open heroku website in browser')
  return parser

def invoke(*args, **kwargs):
  if not kwargs.get('quiet'):
    print('invoking {} in {}'.format(args, os.getcwd()))
  shell = kwargs.get('shell', False)
  if shell:
    args = ' '.join(args)
  if kwargs.get('stdout', False):
    return subprocess.check_output(args, shell=shell).decode()
  else:
    subprocess.check_call(args, shell=shell)

def psqlc(command): invoke('psql', '-c', command, 'postgres')
def psqla(name, value, user): psqlc("ALTER ROLE {} SET {} TO '{}';".format(user, name, value))

def create_database(name): psqlc('CREATE DATABASE {}'.format(name))
def drop_database(name): psqlc('DROP DATABASE {}'.format(name))

def create_user(database, user, password='dev-password'):
  psqlc("CREATE USER {} WITH PASSWORD '{}';".format(user, password))
  psqla('client_encoding', 'utf8', user)
  psqla('default_transaction_isolation', 'read committed', user)
  psqla('timezone', 'UTC', user)
  psqlc('GRANT ALL PRIVILEGES ON DATABASE {} TO {};'.format(database, user))
  psqlc('ALTER USER {} CREATEDB;'.format(user))

def drop_user(user): psqlc('DROP USER {}'.format(user))

def main(args, project, app, db_name, db_user, heroku_url, heroku_repo=None, db_password='dev-password'):
  os.environ['DJANGOGO_ENV'] = 'local'

  if args.create_database: create_database(db_name)
  if args.drop_database: drop_database(db_name)
  if args.create_user: create_user(db_name, db_user, db_password)
  if args.drop_user: drop_user(db_user)
  if args.freshen_database:
    def attempt(f):
      try: f()
      except: pass
    attempt(lambda: drop_database(db_name))
    attempt(lambda: drop_database('test_'+db_name))
    drop_user(db_user)
    create_database(db_name)
    create_user(db_name, db_user, db_password)
    invoke('python3', 'manage.py', 'migrate')

  if args.manage:
    invoke('python3', 'manage.py', *[i.strip() for i in args.manage])

  if args.run:
    invoke('python3', 'manage.py', 'runserver', '--settings', project+'.settings_debug', '0.0.0.0:8000')

  if args.show_urls:
    invoke('python3', 'manage.py', 'show_urls')

  if args.install:
    invoke('pipenv', '--three')
    invoke('pipenv', 'install')

  if args.interact:
    os.environ['PYTHONSTARTUP'] = 'shell_startup.py'
    invoke('python3', 'manage.py', 'shell')

  if args.deploy:
    invoke('python3', 'manage.py', 'check', '--deploy')
    invoke('git', 'push', '-f', 'heroku', 'HEAD:master')
    invoke('heroku', 'run', 'python', 'manage.py', 'migrate', shell=True)

  if args.heroku_log:
    invoke('heroku', 'logs', '--tail', shell=True)

  if args.heroku_bash:
    invoke('heroku', 'run', 'bash')

  if args.heroku_psql:
    invoke('heroku', 'pg:psql', shell=True)

  if args.heroku_remote_add:
    invoke('git', 'remote', 'add', 'heroku', heroku_repo)

  if args.heroku_browser:
    webbrowser.open_new_tab(heroku_url)
