from flask import Flask, session, render_template, redirect, url_for, request
from flask import Markup, send_from_directory
from flask_session import Session
from datetime import timedelta
from system.config_load import config_dict
import json
import calendar
import time
import urllib.parse
from functools import wraps

from system.db import Database

from flask_wtf.csrf import CSRFProtect, CSRFError

from system.crypto_functions import check_hash

from forms import *

from os import environ

from routes import *


global db
db = Database()

csrf = CSRFProtect()

config = config_dict()

app = Flask(__name__,
            static_url_path='',
            static_folder='static',
            template_folder='templates')

app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)
app.config['SECRET_KEY'] = config['main']['secret']


app.register_blueprint(routes)

sess = Session()

sess.init_app(app)

csrf.init_app(app)


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return render_template('csrf_error.html', reason=e.description), 400


def check_session(fn):
    @wraps(fn)
    def decorated_view(*args, **kwargs):
        if 'id' not in session:
            return redirect('/logout')
        current_user = db.select_user_by_id(session['id'])
        if not db.select_user_by_id(session['id']):
            return redirect('/logout')
        kwargs['current_user'] = current_user[0]
        return fn(*args, **kwargs)

    return decorated_view


def check_team_access(fn):
    @wraps(fn)
    def decorated_view(*args, **kwargs):
        team_id = kwargs['team_id']
        user_teams = db.select_user_teams(session['id'])
        current_team = {}
        for found_team in user_teams:
            if found_team['id'] == str(team_id):
                current_team = found_team
        if not current_team:
            return redirect(url_for('create_team'))
        kwargs['current_team'] = current_team
        return fn(*args, **kwargs)

    return decorated_view


# init some global variables
@app.context_processor
def inject_stage_and_region():
    return dict(db=db,
                escape=Markup.escape,
                json_unpack=json.loads,
                format_date=lambda unix_time,
                                   str_format: datetime.datetime.fromtimestamp(
                    int(unix_time)).strftime(str_format),
                urlencode=urllib.parse.quote,
                time=time.time,
                open=open,
                len=len
                )


if __name__ == '__main__':
    if config_dict()['main']['ssl'] == '1':
        app.run(
            ssl_context=(config_dict()['ssl']['cert'],
                         config_dict()['ssl']['priv_key']),
            host=config_dict()['network']['host'],
            port=config_dict()['network']['port'],
            debug=(config_dict()['main']['debug'] == '1'))
    # bugfix for heroku TODO: fix later
    elif 'PORT' in environ:
        app.run(
            host=config_dict()['network']['host'],
            port=environ['PORT'],
            debug=(config_dict()['main']['debug'] == '1'))
    else:
        app.run(
            host=config_dict()['network']['host'],
            port=config_dict()['network']['port'],
            debug=(config_dict()['main']['debug'] == '1'))
