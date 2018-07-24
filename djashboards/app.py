# -*- coding: utf-8 -*-

from flask import Flask, Blueprint
from flask import render_template, request, Response, jsonify, send_file, make_response, redirect, url_for, flash
#from flask_tinydb import PDFFormDB, PDFFormCommitDataD

import json, uuid
import os, re
from datetime import datetime
import urllib

from module_contextpath import get_contextRootPath
from slack_interface import SlackInterface
from chatwork_interface import ChatworkInterface
from mail_utils import MailUtils

# PATH
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR,"static","media") # /static/media
URL_HEADER = "http://127.0.0.1:5000"

# General Settings
app = Flask(__name__)
#app = Blueprint("djashboards",__name__,url_prefix="/djashboards",template_folder=get_contextRootPath(__file__,"templates"))
app.secret_key = str(uuid.uuid4())

# DB Setiings

# Globals


# Generals


# Router
@app.route("/")
def home():
    """ ワードファイルアップロード基底ペー ジ"""
    # スラックタイムライン取得
    slack = SlackInterface().inject_defaults()
    try :
        slack_timeline = slack.get_message(5) # タイムライン抜く
        slack_timeline.reverse() # 昇順にする
    except :
        print "Slack ERROR"
        slack_timeline = []

    # スラックタイムライン２
    try:
        slack.inject2("channel_id","CB52R5BLJ")
        slack_timeline2 = slack.get_message(5) # タイムライン抜く
        slack_timeline2.reverse() # 昇順にする
    except :
        print "Slack ERROR"
        slack_timeline2 = []

    # チャットワークタイムライン取得
    try:
        chatwork = ChatworkInterface().inject_defaults()
        chatwork_timeline = chatwork.get_message(5)
    except :
        print "Chatwork ERROR"
        chatwork_timeline = []

    # メール取得
    mail = MailUtils().inject_defaults()
    mail_list = reversed(mail.get_mails()) # 未読タイトル一覧取得 :逆順に

    ns = {
        "title" : u"HOME",
    }

    # チャット未読状況取得
    try:
        channel_dataList = slack.get_channelInfo(["C9EQ2L2TA","C5HN61S3B","CB52R5BLJ","CALJSB350"]) # Slackのチャンネル情報を抜く
        chatwork_unread_count = chatwork.get_unreads() # チャットワークの未読情報
        channel_dataList.append({
            "channel_name" : "chatwork",
            "unread_count" : int(chatwork_unread_count)
        })
    except :
        print "Chat ERROR"
        channel_dataList = []

    # 全フォームデータ抜く
    return render_template("home.html",
        slack_timeline = slack_timeline,
        slack_timeline2 = slack_timeline2,
        mail_list = mail_list,
        chatwork_timeline = chatwork_timeline,
        channel_dataList = channel_dataList,
        **ns
        )


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')

