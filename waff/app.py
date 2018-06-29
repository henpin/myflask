# -*- coding: utf-8 -*-

from flask import Flask
from flask import render_template, request, Response, jsonify, send_file, make_response, redirect, url_for, flash
from flask_tinydb import PDFFormDB, PDFFormCommitDataDB

import json
import uuid
import os
import re
from datetime import datetime
import urllib

import pdf_utils

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR,"static","media") # /static/media

pdfDB = PDFFormDB()
pdf_commitDB = PDFFormCommitDataDB()

PDFApp = pdf_utils.App()
URL_HEADER = "http://127.0.0.1:5000"

# general
def is_allowedFile(filename):
    """ docファイルか否か """
    return any( ext in filename for ext in (".docx",".xlsx") )

def gen_pdf_fileName(_uuid):
    """ UUIDからPDFファイル名を作る """
    return os.path.join(MEDIA_DIR,_uuid+".pdf")

def gen_png_fileName(_uuid,initial=False,root=True):
    """ ピングファイルを生み出す """
    if initial:
        endphrase = "_%d.png"
    else :
        endphrase = "_0.png"
        
    if root :
        return os.path.join(MEDIA_DIR,_uuid+endphrase)
    else :
        return _uuid +endphrase


# Router
@app.route("/")
def home():
    """ ワードファイルアップロード基底ペー ジ"""
    # 全フォームデータ抜く
    form_data = pdfDB.all()

    return render_template("home.html", form_data=form_data)

@app.route("/demo/")
def demo():
    """ ワードファイルアップロード基底ペー ジ"""
    return render_template("demo.html")

@app.route("/demo2/")
def demo2():
    """ ワードファイルアップロード基底ペー ジ"""
    return render_template("demo2.html")

@app.route("/file_upload/upload/", methods=["POST"])
def upload_file():
    """ ファイルアップロード """
    # ファイル抜く
    _file = request.files['word_file']

    # ファイル名つくる
    if _file and is_allowedFile(_file.filename):
        # 一意名生成
        _uuid = str(uuid.uuid4())
        filename =  _uuid+".docx"
        filepath = os.path.join(MEDIA_DIR,filename)
        # 保存
        _file.save(filepath)

    else:
        return "<p>許可されていない拡張子です</p>"

    # PDFコンバータ
    pdf = pdf_utils.PDFConverter()

    # word2pdf
    out_dir = MEDIA_DIR
    pdf.word2pdf(filepath,out_dir) # 変換

    # pdf2image 
    pdf_fileName = gen_pdf_fileName(_uuid)
    png_fileName = gen_png_fileName(_uuid, initial=True)
    pdf.pdf2png(pdf_fileName,png_fileName) # さらに変換

    # コンテキスト定義
    ns = {
        "title" : u"電子帳票デザイナ",
        "subtitle" : u"form_design",
        "uuid" : _uuid, # 基本UUID
        "png_file" : "/static/media/" +gen_png_fileName(_uuid,root=False), # ファイル名
    }

    # フォーム作成画面レンダリング
    return render_template("pdf_form.html", **ns)


@app.route("/pdf_form/detail/<string:_uuid>", methods=["GET"])
def pdf_form_detail(_uuid):
    """ フォームの詳細情報 """
    # UUIDからフォーム情報抜く
    form_data = pdfDB.search_data(_uuid)

    # form_nameから入力済み全内容ゲッちゅする
    form_name = form_data["form_name"]
    input_dataList = pdf_commitDB.search_fromFK(form_data) # フォームデータから関連コミットデータ全部抜く
    # インピーダンスマッチ用データオブジェクト
    if input_dataList :
        # 辞書のリストでつくる
        data_list = [ { "data" : json.loads(input_data["json"]), "uuid" : input_data["uuid"] } for input_data in input_dataList ]
    else :
        data_list = []

    # メタ名リスト抽出
    metaName_list = form_data["metaNames"]
    #metaName_list_filtered = filter(lambda s: not re.match(u'入力(.|..)',s), metaName_list)
    #metaName_list = metaName_list_filtered if metaName_list_filtered else metaName_list

    # iframeフレーズつくる
    iframe_url = URL_HEADER +url_for("load_input_form",_uuid=_uuid) # 埋め込みフォームURL
    iframe_tag = '<iframe src="%s" width=1190 height=1800 scrolling="no"></iframe>' % (iframe_url,)

    # 公開NS
    ns = {
        "title" : u"フォームデータ",
        "form_name" : form_name,
        "uuid" : _uuid,
        "iframe_url" : iframe_url,
        "iframe_tag" : iframe_tag,
    }

    # レンダリング
    return render_template("pdf_form_detail.html", metaName_list=metaName_list, data_list = data_list, **ns)

def generate_pdf(json_data,template_fileName):
    """ 出力データJSONとテンプレファイル名からPDF生成 """
    # 出力ファイル名をランダムで作る
    out_fileName = gen_pdf_fileName(str(uuid.uuid4())+"_out")

    # JSON読む
    data_list = json.loads(json_data)
    # PDF化する
    with pdf_utils.PDFGenerator().init_pdf() as pdf :
        pdf.load_template(template_fileName) # テンプレ読む
        pdf.set_outfile(out_fileName) # 出力先読む
        for val in data_list.values() : # 全フォームテキストデータでくるくる
            # データ抽出
            x,y = pdf.pos2lefttop(
                val["x"]/1.6, val["y"]/1.6 +val["height"]/1.6 # 半分
            )
            text = val["text"]
             # 書き込み
            pdf.draw_string(x,y,text)

    return out_fileName

@app.route("/pdf_form/output/", methods=["POST"])
def output_pdf():
    """ PDFにして返す """
    # データ抜く
    json_data = request.form["data"] # JSON
    _uuid = request.form["uuid"] # uuid抜く

    # テンプレPDF名参照
    pdf_fileName = gen_pdf_fileName(_uuid)

    # PDF出力
    out_fileName = generate_pdf(json_data,pdf_fileName)

    # PDF返す
    return send_file(out_fileName, mimetype='application/pdf')


@app.route("/pdf_form/output_data/<string:_uuid>", methods=["GET"])
def output_pdf_fromUUID(_uuid):
    """ UUIDから入力データ抜いてそこから出力 """
    # UUIDから入力データ参照
    commit_data = pdf_commitDB.search_data(_uuid)
    if commit_data :
        # フォームデータも参照
        form_data = pdf_commitDB.get_foreignKey(commit_data)
        
        # データJSON参照
        json_data = commit_data["json"]
        # テンプレPDF名参照 : フォームデータのUUIDより
        pdf_fileName = gen_pdf_fileName(form_data["uuid"])

        # PDF化する
        out_fileName = generate_pdf(json_data,pdf_fileName)

        # PDF返す
        return send_file(out_fileName, mimetype='application/pdf')

    else :
        return "<p>NotFOund</p>"


@app.route("/pdf_form/form/save/", methods=["POST"])
def save_form():
    """ フォーム保存 """
    # データ抜く
    json_data = request.form["data"] # json抜く
    _uuid = request.form["uuid"] # uuid抜く
    form_name = request.form["form_name"] # フォーム名抜く

    # 保存
    png_file = "/static/media/" +gen_png_fileName(_uuid,root=False) # 参照可能PNGファイルパス
    pdfDB.insert_data(
        _uuid = _uuid,
        _json = json_data,
        png_file = png_file,
        form_name = form_name
        )

    # ホーム画面に飛ぶ
    flash(u"フォームを保存しました")
    return redirect(url_for('home'))


@app.route("/pdf_form/form/<string:_uuid>", methods=["GET"])
def load_form(_uuid):
    """ フォーム読み込む """
    result = pdfDB.search_data(_uuid) # リザルト抜く
    if result :
        # 値抜く
        json_data = result["json"]
        form_name = result["form_name"]

        # コンテキスト構築
        ns = {
            "title" : u"電子フォーム入力",
            "subtitle" : u"form_input",
            "form_name" : form_name,
            "uuid" : _uuid, # 基本UUID
            "png_file" : "/static/media/" +gen_png_fileName(_uuid,root=False), # ファイル名
        }
        
        # フォーム作成画面レンダリング
        return render_template("pdf_form.html", json_data=json_data, **ns)

    else :
        return "<p>Not Found</p>"

@app.route("/pdf_form/input_form/<string:_uuid>", methods=["GET"])
def load_input_form(_uuid):
    """ フォーム読み込む """
    result = pdfDB.search_data(_uuid) # リザルト抜く
    if result :
        # 値抜く
        json_data = result["json"]

        # コンテキスト構築
        ns = {
            "uuid" : _uuid, # 基本UUID
            "png_file" : "/static/media/" +gen_png_fileName(_uuid,root=False), # ファイル名
        }
        
        # フォーム作成画面レンダリング
        return render_template("pdf_input_form.html", json_data=json_data, **ns)

    else :
        return "<p>Not Found</p>"


@app.route("/pdf_form/form/open/<string:_uuid>", methods=["GET"])
def open_form(_uuid):
    """ 保存したインプットフォームを開く """
    # 保存済みフォームを抜く
    result = pdf_commitDB.search_data(_uuid) # 抜く
    if result :
        # フォームデータも抜く
        form_data = pdf_commitDB.get_foreignKey(result)
        _uuid = form_data["uuid"] # フォームのUUIDに上書き
        form_name = form_data["form_name"]

        # 値抜く
        json_data = result["json"]

        # コンテキスト構築
        ns = {
            "title" : u"電子フォーム再入力",
            "subtitle" : u"form_input",
            "form_name" : form_name,
            "uuid" : _uuid, # 基本UUID
            "png_file" : "/static/media/" +gen_png_fileName(_uuid,root=False), # ファイル名
        }
        
        # フォーム作成画面レンダリング
        return render_template("pdf_form.html", json_data=json_data, **ns)

    else :
        return "<p>Not Found</p>"

@app.route("/pdf_form/form/delete/<string:_uuid>", methods=["GET"])
def delete_form(_uuid):
    """ フォーム削除 """
    # 消す
    pdfDB.delete(_uuid)

    # ホームに飛ばす
    flash(u"フォームを削除しました")
    return redirect(url_for('home'))


@app.route("/pdf_form/commit/", methods=["POST"])
def commit_data():
    """ フォーム入力内容保存 """
    # 値抜く
    json_data = request.form["data"] # json抜く
    _uuid = request.form["uuid"] # uuid抜く
    form_name = request.form["form_name"] # フォーム名抜く

    # データベースに保存
    pdf_commitDB.insert_data(
        _json = json_data,
        form_name = form_name,
        form_uuid = _uuid,
        datetime = datetime.now().isoformat()
    )
    
    # とりまdetail
    flash(u"フォームを送信しました")
    return redirect(url_for('pdf_form_detail',_uuid=_uuid))


@app.route("/pdf_form/form_data/delete/<string:_uuid>", methods=["GET"])
def delete_formData(_uuid):
    """ 消す """
    # フォーム抜いておく
    form_data = pdf_commitDB.get_foreignKey(_uuid=_uuid)
    # 消す
    pdf_commitDB.delete(_uuid)

    # とりdetail
    flash(u"入力データを削除しました")
    return redirect(url_for('pdf_form_detail',_uuid=form_data["uuid"]))


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')

