# -*- coding: utf-8 -*-
from flask import Flask, render_template, url_for, request
from flask_weasyprint import HTML, render_pdf
from flask_cors import CORS, cross_origin
import markdown2
import os

app = Flask(__name__)

# Enable Cross origin Access
cors = CORS(app)

# HEROKU用
port = os.environ.get("PORT") or "8000"


@app.route('/',methods=["POST","GET"])
def md2pdf():
    """ mdをPDFに """
    if request.method == "GET":
        md = "# MD PDF Program\n ## STATE: is runnning"
        # HTML化
        html = markdown2.markdown(md,extras=["tables","fenc-code-blocks","code-color"])
        # PDF化して返す
        return render_pdf(HTML(string=html))

    elif request.method == "POST":
        # MD抜く
        md = request.form['md']
        # HTML化
        html = markdown2.markdown(md,extras=["tables","fenc-code-blocks","code-color"])
        # PDF化して返す
        return render_pdf(HTML(string=html))

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0',port=port)
