After cloning into a folder at, say, /path/to/djangogo, navigate to where you want to create a new Django repo and run:
`python3 djangogo repo_name`

Djangogo performs the following setup:
- heroku
	- gunicorn
	- postgres
	- static resources
	- various security settings
- new app
- dev helper script called go.py
- commit tracking details if they are ever needed
