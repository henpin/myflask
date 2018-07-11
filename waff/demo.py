# -*- coding: utf-8 -*-

from flask_tinydb import PDFFormDB, PDFFormCommitDataDB
from app_util import BasicApp

import json
import uuid
import os
import re
import urllib

from plane_node import Node
from dpy3_force import ForceNodeCollection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR,"static","media") # /static/media

pdfDB = PDFFormDB()
pdf_commitDB = PDFFormCommitDataDB()


class App(BasicApp):
    """ アプリケーション """
    def main(self):
        # Dpy3起こす
        dpy3 = ForceNodeCollection()

        # 全データ抜く
        all_data = pdfDB.all()

        # ノードツリー化
        for data in all_data:
            root = Node(data["form_name"])
            root.color = "aliceblue"

            # 入力欄名でノード化
            input_names = json.loads(data["json"]).keys()
            for name in input_names:
                child = Node(name)
                child.color = "lavender"
                # 関連化
                root.add_rel(child)
                # dpy3に保存
                dpy3.add_node(child)

            # dpy3に保存
            dpy3.add_node(root)

        f_name = self.get_contextPath("text","waff_dpy3.html")
        dpy3.write(f_name)

if __name__ == '__main__':
    App().main()

