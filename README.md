After cloning into a folder at, say, /path/to/djangogo, navigate to where you want to create a new Django repo and run:
`python3 /path/to/djangogo --create repo_name`

Djangogo performs the following setup:
- heroku
	- gunicorn
	- postgres
	- static resources
	- various security settings
- new app
- dev helper script called go.py
- commit tracking details if they are ever needed

TODO
- option to generate signup and login views; base, home, signup, and login templates; and LOGIN_REDIRECT_URL
- crudify
- shell helper that imports models
- heroku run bash
