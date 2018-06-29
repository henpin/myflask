# -*- coding: utf-8 -*-

from tinydb import TinyDB, Query
import json
import uuid

"""
flask-tinyDBクライアント
"""

DB = TinyDB('myflask.json')

class BaseMyTinyTable(object):
    """ テーブルラッパ """
    table = None
    ForeignKeyCls = None # FKクラス
    ForeignKeyName = None # FK名

    def __init__(self):
        self.fk_uuid = None # 外部参照UUID

    def insert(self,*args,**kwargs):
        """ 汎用インサート """
        return self.table.insert(*args,**kwargs)

    def search(self,*args,**kwargs):
        """ 検索 """
        return self.table.search(*args,**kwargs)

    def all(self):
        """ 普通にALL """
        return self.table.search((Query().living == True))

    def get_foreignKey(self,data=None,_uuid=None):
        """ フォーリングキー検索 """
        if not data and not _uuid :
            raise ValueError("なんもないねん")
        elif _uuid:
            # そもそも検索基底オブジェクトを抜いてくる
            data = self.search_data(_uuid)
            
        key = data[self.ForeignKeyName]
        return self.ForeignKeyCls().search_data(_uuid=key)

    def search_fromFK(self,fk_data):
        """ FKのUUIDで検索 """
        que = Query()
        return self.table.search( (que[self.ForeignKeyName] == fk_data["uuid"]) & (que.living == True) )

    def delete(self,_uuid):
        """ 削除しまつ """
        # 生存フラグ下げる
        self.table.update({ "living" : False }, Query().uuid == _uuid)


class PDFFormDB(BaseMyTinyTable):
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


class PDFFormCommitDataDB(BaseMyTinyTable):
    """ PDFフォームのコミットデータ """
    # テーブル
    table = DB.table("pdf_form_commitdata")
    # FK
    ForeignKeyCls = PDFFormDB # フォームデータにFK
    ForeignKeyName = "form_uuid" # フォーリンキーキー

    def insert_data(self,_json,datetime,form_name,form_uuid):
        """ コミットデータの保存 """
        self.insert({
            "uuid" : str(uuid.uuid4()),
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
            

