# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from flask import Flask, render_template, url_for
from flask_weasyprint import HTML, render_pdf

app = Flask(__name__)

@app.route('/')
def hello_html():
    html = "<h1>ok</h1>"
    return render_pdf(HTML(string=html))

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0',port=8000)
