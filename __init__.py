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
  parser.add_argument('--create-database', action='store_true', help='create local database for this project')
  parser.add_argument('--drop-database', action='store_true', help='drop local database for this project')
  parser.add_argument('--create-user', action='store_true', help='create local database user for this project')
  parser.add_argument('--drop-user', action='store_true', help='drop local database user for this project; database must be dropped first')
  parser.add_argument('--manage', '-m', help='set up djangogo env and run manage.py with given args')
  parser.add_argument('--deploy', '-d', action='store_true', help='deploy to heroku')
  parser.add_argument('--log', '-l', action='store_true', help='tail heroku server logs')
  parser.add_argument('--run', '-r', action='store_true', help='run server locally')
  parser.add_argument('--heroku-psql', '-s', action='store_true', help='psql to heroku database')
  parser.add_argument('--browser', '-b', action='store_true', help='open heroku website in browser')
  parser.add_argument('--show-urls', '-u', action='store_true', help='show exposed URLs')
  parser.add_argument('--install', '-i', action='store_true', help='update Pipfile.lock wrt Pipfile')
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

def drop_user(user): psqlc('DROP USER {}'.format(user))

def main(args, project, app, db_name, db_user, heroku_url, db_password='dev-password'):
  os.environ['DJANGOGO_ENV'] = 'local'

  if args.create_database: create_database(db_name)
  if args.drop_database: drop_database(db_name)
  if args.create_user: create_user(db_name, db_user, db_password)
  if args.drop_user: drop_user(db_user)

  if args.manage:
    invoke('python3', 'manage.py', args.manage)

  if args.deploy:
    invoke('python3', 'manage.py', 'check', '--deploy')
    invoke('git', 'push', '-f', 'heroku', 'master')
    invoke('heroku', 'run', 'python', 'manage.py', 'migrate', shell=True)

  if args.log:
    invoke('heroku', 'logs', '--tail', shell=True)

  if args.run:
    invoke('python3', 'manage.py', 'runserver', '--settings', project+'.settings_debug')

  if args.heroku_psql:
    invoke('heroku', 'pg:psql', shell=True)

  if args.browser:
    webbrowser.open_new_tab(heroku_url)

  if args.show_urls:
    invoke('python3', 'manage.py', 'show_urls')

  if args.install:
    invoke('pipenv', '--three')
    invoke('pipenv', 'install')
