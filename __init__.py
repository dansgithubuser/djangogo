from collections import defaultdict
import argparse
import os
import subprocess
import sys
import time
import webbrowser

def make_parser():
	parser=argparse.ArgumentParser()
	parser.add_argument('--create-database', action='store_true')
	parser.add_argument('--drop-database', action='store_true')
	parser.add_argument('--create-user', action='store_true')
	parser.add_argument('--drop-user', action='store_true', help='as implemented, database must be dropped first')
	parser.add_argument('--database-freshen', action='store_true', help='drop database and user; create database and user')
	parser.add_argument('--database-server-start', '--db', action='store_true')
	parser.add_argument('--database-server-stop', action='store_true')
	parser.add_argument('--migrate', action='store_true')
	parser.add_argument('--deploy-setup', action='store_true')
	parser.add_argument('--deploy', '-d', action='store_true')
	parser.add_argument('--log', '-l', action='store_true')
	parser.add_argument('--run', '-r', action='store_true')
	parser.add_argument('--heroku-psql', action='store_true')
	parser.add_argument('--browser', '-b', action='store_true')
	return parser

def invoke(*args):
	print('invoking {}'.format(args))
	subprocess.check_call(args)

def postgres(*args): invoke('sudo', '-i', '-u', 'postgres', *args)
def psql(*args): postgres('psql', *args)
def psqlc(command): psql('-c', command)
def psqla(name, value, user): psqlc("ALTER ROLE {} SET {} TO '{}';".format(user, name, value))

def create_database(database): psqlc('CREATE DATABASE {}'.format(database))
def drop_database(database): psqlc('DROP DATABASE {}'.format(database))

def create_user(user):
	psqlc("CREATE USER map_database_user WITH PASSWORD 'dev-password';")
	psqla('client_encoding', 'utf8', user)
	psqla('default_transaction_isolation', 'read committed', user)
	psqla('timezone', 'UTC', user)
	psqlc('GRANT ALL PRIVILEGES ON DATABASE map_database TO map_database_user;')

def drop_user(user): psqlc('DROP USER {}'.format(user))

def main(args, project, app, database, user, heroku_repo, heroku_url):
	if args.create_database: create_database(database)
	if args.drop_database: drop_database(database)
	if args.create_user: create_user(user)
	if args.drop_user: drop_user(user)
	
	if args.database_freshen:
		drop_database(database)
		drop_user(user)
		create_database(database)
		create_user(user)
	
	if args.database_server_start:
		invoke('sudo', 'systemctl', 'start', 'postgresql@10-main')
	
	if args.database_server_stop:
		invoke('sudo', 'systemctl', 'stop', 'postgresql@10-main')
	
	if args.migrate:
		invoke('python3', 'manage.py', 'makemigrations', app)
		invoke('python3', 'manage.py', 'migrate')
	
	if args.deploy_setup:
		invoke('git', 'remote', 'add', 'heroku', heroku_repo)
	
	if args.deploy:
		invoke('python3', 'manage.py', 'check', '--deploy')
		invoke('git', 'push', '-f', 'heroku', 'master')
		invoke('heroku', 'run', 'python', 'manage.py', 'migrate')
	
	if args.log:
		invoke('heroku', 'logs', '--tail')
	
	if args.run:
		invoke('python3', 'manage.py', 'runserver', '--settings', project+'.settings_debug')
	
	if args.heroku_psql:
		invoke('heroku', 'pg:psql')
	
	if args.browser:
		webbrowser.open_new_tab(heroku_url)
