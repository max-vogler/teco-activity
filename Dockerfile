FROM python:3.6-onbuild

EXPOSE 5000

CMD [ "gunicorn", "-k gthread", "-t 4", "-b 0.0.0.0:5000", "activity.server:app"]
