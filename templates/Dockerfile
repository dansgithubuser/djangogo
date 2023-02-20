FROM python:3-slim-buster

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /{name}
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY manage.py .
COPY {proj_name} ./{proj_name}
COPY do.py .
COPY {app_name} ./{app_name}
COPY git-state.txt .
RUN ./do.py m -- collectstatic --no-input

EXPOSE {port}

ENTRYPOINT gunicorn\
	-w 4\
	-b 0.0.0.0:{port}\
	{proj_name}.wsgi:application
