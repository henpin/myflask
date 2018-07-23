# -*- coding: utf-8 -*-

from flask import Flask, Blueprint, abort
from flask import render_template, request, Response, jsonify, send_file, make_response, redirect, url_for, flash
from flask_tinydb import PDFFormDB, PDFFormCommitDataDB
from flask.views import MethodView

import json
import uuid
import os
import re
import urllib

from module_contextpath import get_contextRootPath, get_contextPath
import pdf_utils
from plane_node import Node
from dpy3_force import ForceNodeCollection
from time import sleep
from tinydb_utils import Locker

#app = Blueprint("waff",__name__,url_prefix="/waff",template_folder=get_contextRootPath(__file__,"templates"))
app = Flask(__name__)
app.secret_key = str(uuid.uuid4())
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR,"static","media") # /static/media

pdfDB = PDFFormDB()
pdf_commitDB = PDFFormCommitDataDB()

URL_HEADER = "http://127.0.0.1:8000"
COMMIT_LOCK = Locker() # 適当コミットロッカー

# general
def is_allowedFile(filename):
    """ docファイルか否か """
    return any( ext in filename for ext in (".docx",".xlsx",".pptx",".doc") )

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
# Home -----------------------------------------------
@app.route("/")
def home():
    """ ワードファイルアップロード基底ペー ジ"""
    # 全フォームデータ抜く
    form_data = pdfDB.all()

    # 未承認バッジ数くっつけておく
    for data in form_data :
        # input_type==承認欄の数を調べる
        input_data = json.loads(data["json"]) # JSON抜く
        data["unauthorized"] = len([ _ for _ in input_data.values() if _.get("input_type") == u"承認欄" ])

    return render_template("home.html", form_data=form_data)

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


# Detail ----------------------------------------------
@app.route("/pdf_form/detail/<string:_uuid>", methods=["GET"])
def pdf_form_detail(_uuid):
    """ フォームの詳細情報 """
    # UUIDからフォーム情報抜く
    form_data = pdfDB.search_data(_uuid) or abort(404)

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
    iframe_url = URL_HEADER +url_for("iframe_form",_uuid=_uuid) # 埋め込みフォームURL
    iframe_tag = '<iframe src="%s" width="100%%" height=1800 scrolling="no" frameborder="0"></iframe>' % (iframe_url,)

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


# Output ----------------------------------------------------
class PDFFormOutputAPIView(MethodView):
    """ PDF出力APIビュー """
    def get(self,_uuid):
        """ 出力API """
        # UUIDから入力データ参照
        commit_data = pdf_commitDB.search_data(_uuid) or abort(404)

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

    def post(self):
        """ 注入バージョン """
        # データ抜く
        json_data = request.form["data"] # JSON
        _uuid = request.form["uuid"] # uuid抜く

        # テンプレPDF名参照
        pdf_fileName = gen_pdf_fileName(_uuid)

        # PDF出力
        out_fileName = generate_pdf(json_data,pdf_fileName)

        # PDF返す
        return send_file(out_fileName, mimetype='application/pdf')

def generate_pdf(json_data,template_fileName):
    """ 出力データJSONとテンプレファイル名からPDF生成 """
    # 出力ファイル名をランダムで作る
    out_fileName = gen_pdf_fileName(str(uuid.uuid4())+"_out")

    # JSON読む
    if isinstance(json_data,dict):
        data_list = json_data
    else:
        data_list = json.loads(json_data)

    # PDF化する
    with pdf_utils.PDFGenerator().init_pdf() as pdf :
        pdf.load_template(template_fileName) # テンプレ読む
        pdf.set_outfile(out_fileName) # 出力先読む
        for val in data_list.values() : # 全フォームテキストデータでくるくる
            # データ抽出
            # posとW/Hから中点を抜く
            center_pos = pdf.pos2lefttop(
                val["x"]/1.6 +(val["width"]/1.6)/2, val["y"]/1.6 +(val["height"]/1.6)/2 # 微調整
            )
            text = val["text"]
            align_type = val["align_type"]

            # 画像のときは画像を張る
            if text.startswith("/static"):
                # サイズ
                height = 30
                width = 30
                # 判子画像
                img_path = os.path.join(BASE_DIR,text[1:]) # 参照
                # 張る
                pdf.paste_image(img_path, (center_pos[0]-width/2,center_pos[1]-height/2),(width,height)) # 画像分のサイズを差し引く

            elif ( align_type == "center"):
                # 中点ベースで書き込み
                pdf.draw_centered_string(center_pos[0],center_pos[1]-4,text)

            elif ( align_type == "left" ):
                # 左寄せ
                pdf.draw_string(val["x"]/1.6, center_pos[1]-2, text)

            elif ( align_type == "right" ):
                # 右寄せ
                pdf.draw_right_string(val["x"]/1.6 +val["width"]/1.6, center_pos[1]-4, text)

    return out_fileName


# PDFForm --------------------------------------
class PDFFormView(MethodView):
    """ PDFフォーム生成・よみこみヴー"""
    def get(self,_uuid):
        """ フォーム読み込む """
        result = pdfDB.search_data(_uuid) or abort(404) # リザルト抜く
        if result :
            # 値抜く
            json_data = result["json"].replace(u"\\",u"\\\\").replace(u"'",u"\\'")
            form_name = result["form_name"]

            # コンテキスト構築
            ns = {
                "title" : u"電子フォーム入力",
                "subtitle" : u"form_input",
                "form_name" : form_name,
                "uuid" : _uuid, # 基本UUID
                "png_file" : "/static/media/" +gen_png_fileName(_uuid,root=False), # ファイル名
                "seal_path" : "/static/img/tanaka.png", # はんこパス
            }
            
            # フォーム作成画面レンダリング
            return render_template("pdf_form.html", json_data=json_data, **ns)

        else :
            return "<p>Not Found</p>"

    def post(self):
        """ フォーム保存 """
        # データ抜く
        json_data = request.form["data"] # json抜く
        _uuid = request.form["uuid"] # uuid抜く
        form_name = request.form["form_name"] # フォーム名抜く

        # 存在すれば上書きupdate
        if pdfDB.search_data(_uuid):
            pdfDB.update_data(
                form_name = form_name,
                _json = json_data,
                _uuid = _uuid
                )
        else :
            # 普通に保存
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

class PDFFormEditView(MethodView):
    """ フォーム編集ビュー """
    def get(self,_uuid):
        """ 編集せる"""
        # データ抜く
        result = pdfDB.search_data(_uuid) or abort(404) # リザルト抜く
        # 値抜く
        json_data = result["json"].replace(u"\\",u"\\\\").replace(u"'",u"\\'")
        form_name = result["form_name"]

        # コンテキスト構築
        ns = {
            "title" : u"フォーム編集",
            "subtitle" : u"form_design",
            "form_name" : form_name,
            "uuid" : _uuid, # 基本UUID
            "png_file" : "/static/media/" +gen_png_fileName(_uuid,root=False), # ファイル名
            "seal_path" : "/static/img/tanaka.png", # はんこパス
        }
        
        # フォーム作成画面レンダリング
        return render_template("pdf_form.html", json_data=json_data, **ns)


class PDFFormDeleteView(MethodView):
    """ 削除の為のヴー """
    def get(self,_uuid):
        """ フォーム削除 """
        # 消す
        pdfDB.delete(_uuid)

        # ホームに飛ばす
        flash(u"フォームを削除しました")
        return redirect(url_for('home'))


# IframeForm -----------------------------------------
class IframePDFFormView(MethodView):
    """ Iframe用ビュー """
    def get(self,_uuid):
        """ フォーム読み込む """
        result = pdfDB.search_data(_uuid) or abort(404) # リザルト抜く
        if result :
            # 値抜く
            json_data = result["json"].replace(u"\\",u"\\\\").replace(u"'",u"\\'")
     
            # コンテキスト構築
            ns = {
                "uuid" : _uuid, # 基本UUID
                "png_file" : "/static/media/" +gen_png_fileName(_uuid,root=False), # ファイル名
                "seal_path" : "/static/img/tanaka.png", # はんこパス
            }
            
            # フォーム作成画面レンダリング
            return render_template("pdf_input_form.html", json_data=json_data, **ns)

        else :
            return "<p>Not Found</p>"

class IframeCommitDataView(MethodView):
    """ IFrame版コミットデータビュー """
    def get(self,_uuid):
        """ フォーム読み込む """
        # 送信モード拡張設定
        commit_mode = request.args.get("commit_mode") or "ajax"
        if commit_mode not in ("interactive","ajax"): abort(404)

        # 保存済みフォームを抜く
        result = pdf_commitDB.search_data(_uuid) or abort(404) # 抜く
        commit_uuid = _uuid # 複写
        if result :
            # フォームデータも抜く
            form_data = pdf_commitDB.get_foreignKey(result)
            form_name = form_data["form_name"]
            _uuid = form_data["uuid"] # フォームのUUIDに上書き

            # 値抜く
            json_data = result["json"].replace(u"\\",u"\\\\").replace(u"'",u"\\'")

            # コンテキスト構築
            ns = {
                "title" : u"電子フォーム再入力",
                "subtitle" : u"form_input",
                "form_name" : form_name,
                "uuid" : _uuid, # 基本UUID
                "commit_uuid" : commit_uuid, # コミットデータUUID
                "open_mode" : True, # オープンモード
                "commit_mode" : commit_mode, # コミットモード
                "png_file" : "/static/media/" +gen_png_fileName(_uuid,root=False), # ファイル名
                "seal_path" : "/static/img/tanaka.png", # はんこパス
            }
            
            # フォーム作成画面レンダリング
            return render_template("pdf_input_form.html", json_data=json_data, **ns)

        else :
            return "<p>Not Found</p>"

# Commit data ----------------------------------------
class PDFFormCommitDataView(MethodView):
    """ こっみとデータヴー """
    def get(self,_uuid):
        """ コミットデータを開く"""
        # 保存済みフォームを抜く
        result = pdf_commitDB.search_data(_uuid) or abort(404) # 抜く
        commit_uuid = _uuid # 複写
        if result :
            # フォームデータも抜く
            form_data = pdf_commitDB.get_foreignKey(result)
            form_name = form_data["form_name"]
            _uuid = form_data["uuid"] # フォームのUUIDに上書き

            # 値抜く
            json_data = result["json"].replace(u"\\",u"\\\\").replace(u"'",u"\\'")

            # コンテキスト構築
            ns = {
                "title" : u"電子フォーム再入力",
                "subtitle" : u"form_input",
                "form_name" : form_name,
                "uuid" : _uuid, # 基本UUID
                "commit_uuid" : commit_uuid, # コミットデータUUID
                "open_mode" : True, # オープンモード
                "png_file" : "/static/media/" +gen_png_fileName(_uuid,root=False), # ファイル名
                "seal_path" : "/static/img/tanaka.png", # はんこパス
            }
            
            # フォーム作成画面レンダリング
            return render_template("pdf_form.html", json_data=json_data, **ns)

        else :
            return "<p>Not Found</p>"

    def post(self):
        """ 新規コミット """
        # 値抜く
        json_data = request.form["data"] # json抜く
        # とりまdetail
        flash(u"フォームを送信しました")
        return redirect(url_for('pdf_form_detail',_uuid=_uuid))

    def post(self,_uuid=None):
        """ データコミット"""
        # 値抜く
        json_data = request.form["data"] # json抜く

        if _uuid : # 上書き処理
            # UUIDでコミットデータ索引してJSONデータをUpdate
            pdf_commitDB.update({"json":json_data} ,_uuid)
            form_data = pdf_commitDB.get_foreignKey(_uuid=_uuid)
            _uuid = form_data["uuid"] # フォームデータのUUIDにしとく

        else : # 新規コミット
            # 新規コミット用データ
            _uuid = request.form["uuid"] # uuid抜く
            form_name = request.form["form_name"] # フォーム名抜く

            # データベースに保存
            pdf_commitDB.insert_data(
                _json = json_data,
                form_name = form_name,
                form_uuid = _uuid,
            )

        # とりまdetail
        flash(u"フォームを送信しました")
        return redirect(url_for('pdf_form_detail',_uuid=_uuid))

class PDFFormCommitDataDeleteView(MethodView):
    """ 削除の為ダケノヴー """
    def get(self,_uuid):
        """ コミットデータの削除 """
        # フォーム抜いておく
        form_data = pdf_commitDB.get_foreignKey(_uuid=_uuid) or abort(404)
        # 消す
        pdf_commitDB.delete(_uuid)

        # とりdetail
        flash(u"入力データを削除しました")
        return redirect(url_for('pdf_form_detail',_uuid=form_data["uuid"]))


# API ---------------------------------------------------------
@app.route("/pdf_form/inject/", methods=["POST"])
def inject_data():
    """ 値注入API """
    # 値抜く
    json_data = json.loads(request.form["data"]) # json抜く
    _uuid = request.form["uuid"] # uuid抜く

    # フォームデータ抜く
    form_data = pdfDB.search_data(_uuid) or abort(404)
    form_json_data = json.loads(form_data["json"])

    # JSONデータの置き換え
    for name,value in json_data.items():
        form_json_data[name]["text"] = value # アップデートする

    # 保存しとく
    pdf_commitDB.insert_data(
        _json = json.dumps(form_json_data),
        form_name = form_data["form_name"],
        form_uuid = form_data["uuid"],
    )

    # PDF出力
    pdf_fileName = gen_pdf_fileName(_uuid) # テンプレPDF名参照
    out_fileName = generate_pdf(form_json_data,pdf_fileName)

    # PDF返す
    return send_file(out_fileName, mimetype='application/pdf')

@app.route("/pdf_form/get_all_names/", methods=["GET"])
def pdf_form_names():
    """ 全名前をもらう """
    # データ検索して名前抽出
    return json.dumps([ form_data["form_name"] for form_data in pdfDB.all() ])

class CommitDataAPIView(MethodView):
    """ コミットデータＡＰＩ"""
    def post(self,_uuid):
        """ JSON送って注入 """
        global LOCK
        # 値抜く
        json_data = json.loads(request.form["data"]) # json抜く

        # フォームデータ抜く
        commit_data = pdf_commitDB.search_data(_uuid) or abort(404)
        commit_json_data = json.loads(commit_data["json"])

        # JSONデータの置き換え
        for name,value in json_data.items():
            commit_json_data[name]["text"] = value # アップデートする

        # アップデート
        with COMMIT_LOCK:
            pdf_commitDB.update({ "json" : json.dumps(commit_json_data) },_uuid)

        # PDF出力
        #pdf_fileName = gen_pdf_fileName(_uuid) # テンプレPDF名参照
        #out_fileName = generate_pdf(form_json_data,pdf_fileName)

        # PDF返す
        #return send_file(out_fileName, mimetype='application/pdf')
        return "OK"

class CommitDataModelAPIView(MethodView):
    """ コミットデータモデルAPI """
    def get(self,_uuid):
        """ コミットデータ抜く"""
        # UUIDからデータJSON抜く
        commit_data = pdf_commitDB.search_data(_uuid) or abort(404)
        # フォームデータ抜く
        commit_json_data = commit_data["json"]

        return commit_json_data

    def post(self):
        """ 複数検索 """
        # UUIDリストを抜く
        uuid_list = json.loads(request.form["uuid_list"])
        # くるくるして返す
        result = [ pdf_commitDB.search_data(_uuid) for _uuid in uuid_list ]

        return json.dumps(result)


# Model API ----------------------------------------
class PDFFormModelAPIView(MethodView):
    """ Json取得API """    
    def get(self,_uuid):
        """ UUIDからフォームデータ検索 """
        # データ検索
        form_data = pdfDB.search_data(_uuid) or abort(404) 
        return json.dumps(form_data)

    def post(self):
        """ 複数検索 """
        # UUIDリストを抜く
        uuid_list = json.loads(request.form["uuid_list"])

        # くるくるして返す
        result = [ pdfDB.search_data(_uuid) for _uuid in uuid_list ]

        return json.dumps(result)

@app.route("/pdf_form/get_json/from_name/<string:name>", methods=["GET"])
def pdf_form_getJson_fromName(name):
    """ 名前から索引 """
    # データ検索
    form_data = pdfDB.search_from("form_name",name) or abort(404) 

    # 返す
    return json.dumps(form_data)


# Etc ---------------------------------------------
@app.route("/demo/")
def demo():
    return render_template("demo.html")



# ルーティング ---------------------------------------
# PDF Form 出力API
app.add_url_rule('/pdf_form/output/<string:_uuid>', view_func=PDFFormOutputAPIView.as_view("output_data"))
app.add_url_rule('/pdf_form/output/inject/', view_func=PDFFormOutputAPIView.as_view("output_data_with_inject"))
# PDF Form
app.add_url_rule('/pdf_form/save/', view_func=PDFFormView.as_view("save_form"))
app.add_url_rule('/pdf_form/load/<string:_uuid>', view_func=PDFFormView.as_view("load_form"))
app.add_url_rule('/pdf_form/edit/<string:_uuid>', view_func=PDFFormEditView.as_view("edit_form"))
app.add_url_rule('/pdf_form/delete/<string:_uuid>', view_func=PDFFormDeleteView.as_view("delete_form"))
# Iframe Form
app.add_url_rule('/pdf_form/iframe_form/<string:_uuid>', view_func=IframePDFFormView.as_view("iframe_form"))
app.add_url_rule('/pdf_form/iframe_form/open/<string:_uuid>', view_func=IframeCommitDataView.as_view("iframe_form_open"))
# Commit Data
commit_view = PDFFormCommitDataView.as_view('commit')
app.add_url_rule('/pdf_form/commit/', view_func=commit_view)
app.add_url_rule('/pdf_form/commit/<string:_uuid>', view_func=commit_view)
app.add_url_rule('/pdf_form/open/<string:_uuid>', view_func=PDFFormCommitDataView.as_view("open_commitdata"))
app.add_url_rule('/pdf_form/delete_data/<string:_uuid>', view_func=PDFFormCommitDataDeleteView.as_view("delete_commitdata"))
# API
app.add_url_rule('/pdf_form/api/model/<string:_uuid>', view_func=PDFFormModelAPIView.as_view("pdfform_model_api_get"))
app.add_url_rule('/pdf_form/api/model/', view_func=PDFFormModelAPIView.as_view("pdfform_model_api_post"))
app.add_url_rule('/pdf_form/commit/inject/<string:_uuid>', view_func=CommitDataAPIView.as_view("commit_inject"))
app.add_url_rule('/pdf_form/commit/get/<string:_uuid>', view_func=CommitDataModelAPIView.as_view("commitdata_model_api_get"))
app.add_url_rule('/pdf_form/commit/get/', view_func=CommitDataModelAPIView.as_view("commitdata_model_api_post"))


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0',port=8000)

