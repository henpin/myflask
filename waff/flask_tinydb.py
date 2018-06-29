# -*- coding: utf-8 -*-

from tinydb import TinyDB, Query
import json
import uuid
from tinydb_utils import BaseTinyTable

"""
flask-tinyDBクライアント
"""

DB = TinyDB('flask.json')

class PDFFormDB(BaseTinyTable):
    """ PDFフォーム用DB """
    # テーブル
    table = DB.table("pdf_form")

    def insert_data(self,_uuid,_json,form_name,png_file=None):
        """ データインサート """
        # JSONからキー抜いてメタネームリスト生成
        json_data = json.loads(_json) # とりま読む
        items = sorted(json_data.items() ,key = lambda item : item[1]["order"]) # items()して、値にオーダーってのが入ってるのでそれでソート
        metaNames = [ key for key,val in items ]  # キーだけ取り除く

        # do インサーション
        self.insert({
            "form_name" : form_name,
            "uuid" : _uuid,
            "json" : _json,
            "png_file" : png_file,
            "metaNames" : metaNames,  # メタネームリスト
            "living" : True # 活性フラグ
        })

    def search_data(self,_uuid):
        """ UUIDで検索 """
        que = Query()
        result = self.search(
            (que.uuid == _uuid) & (que.living == True)
            )
        return result and result[-1]


class PDFFormCommitDataDB(BaseTinyTable):
    """ PDFフォームのコミットデータ """
    # テーブル
    table = DB.table("pdf_form_commitdata")
    # FK
    ForeignKeyCls = PDFFormDB # フォームデータにFK
    ForeignKeyName = "form_uuid" # フォーリンキーキー

    def insert_data(self,_json,datetime,form_name,form_uuid):
        """ コミットデータの保存 """
        self.insert({
            "json" : _json,
            "form_name" : form_name,
            "datetime" : datetime,
            "form_uuid" : form_uuid,
            "living" : True # 活性フラグ
        })

    def search_data(self,_uuid):
        """ 送信データの検索 """
        # UUIDで検索
        que = Query()
        result = self.search(
            (que.uuid == _uuid) & (que.living == True)
            )
        return result and result[-1]
            

