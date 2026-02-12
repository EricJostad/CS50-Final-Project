import os
from flask import Flask, render_template, request
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")
