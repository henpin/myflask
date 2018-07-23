
function App(){
    var self = this;
    var canvas = null;
    var input_num = 0;
    var elem_holder = {}; // element-holder
    var elem_list = []; // element-holder2
    var tabber = [];
    var now_tabber = 0;
    var mode = "creation"; // 実行モード
    var commit_mode = "form";
    var uuid = ""; // UUID
    self.set_commit_mode = function(mode){ 
        console.log("commit_mode:" +mode);
        commit_mode = mode; 
        } /* セッター */

    /* エントリーポイント*/
    this.init = function(){
        // UUID
        uuid = self.get_uuid();
        self.init_canvas();
        self.init_keyEvents();
        self.init_canvasEvents();
        self.init_domEvents();
        self.init_ajaxEvents();
        return self;
    }

    /* キャンバス初期化 */
    this.init_canvas = function(){
        // init canvas
        canvas = new fabric.Canvas('c',{isDrawingMode: false});

        // set canvasSize
        canvas.setWidth($("#my-image").width());
        canvas.setHeight($("#my-image").height());

        // set center
        $(".canvas-container").css("margin:auto;")

        // bg
        self.init_bg()
    }

    /* 背景初期化 */
    this.init_bg = function(){
        var img_path = $("#my-image").attr("src"); // ファイルパス
        setTimeout(function(){
            canvas.setBackgroundImage(img_path, canvas.renderAll.bind(canvas));},0);
    }

    /* キャンバスイベントの初期化*/
    this.init_canvasEvents = function(){
        // Events
        var startX = 0;
        var startY = 0;

        // ドラッグスタート
        canvas.on('mouse:down', function(opt) {
            // 要素上なら無視
            if (opt.target && opt.target._objects){
                startX = 0;
                startY = 0;
            } else {
                startX = opt.pointer.x; // 保存
                startY = opt.pointer.y; // 保存
            }
        });

        // ドラッグエンド => 入力欄つくる
        canvas.on('mouse:up', function(opt){
            if ( mode != "creation"){ return; }
            var x = opt.pointer.x;
            var y = opt.pointer.y;

            if (x-startX<10 && y-startY<10){ return }
            if (!startX && !startY){ return }

            // 範囲中に何らかのオブジェクトが存在したら無視
            for (let elem of Object.values(elem_holder)){
                // 範囲内にあるか探索
                if ( (startX <= elem.left && elem.left <= x) && (startY <= elem.top && elem.top <= y) ){
                    return ;
                } else if ( elem.left <= -1 || elem.top <= -1 ) {
                    // 複数の場合は何故か座標値がひっくり返る
                    return ;
                }
            }

            // 入力欄レクトを生成
            var width = x -startX;
            var height = y -startY;
            self.regist_inputRect(startX,startY,width,height); // 生成
        });

        // タッチイベント
        canvas.on({
            'touch:gesture': function(e) {
                if (e.e.touches && e.e.touches.length == 2) {
                    pausePanning = true;
                    var point = new fabric.Point(e.self.x, e.self.y);
                    if (e.self.state == "start") {
                        zoomStartScale = self.canvas.getZoom();
                    }
                    var delta = zoomStartScale * e.self.scale;
                    self.canvas.zoomToPoint(point, delta);
                    pausePanning = false;
                }
            },
            'object:selected': function() {
                pausePanning = true;
            },
            'selection:cleared': function() {
                pausePanning = false;
            },
            'touch:drag': function(e) {
                if (pausePanning == false && undefined != e.e.layerX && undefined != e.e.layerY) {
                    currentX = e.e.layerX;
                    currentY = e.e.layerY;
                    xChange = currentX - lastX;
                    yChange = currentY - lastY;

                    if( (Math.abs(currentX - lastX) <= 50) && (Math.abs(currentY - lastY) <= 50)) {
                        var delta = new fabric.Point(xChange, yChange);
                        canvas.relativePan(delta);
                    }

                    lastX = e.e.layerX;
                    lastY = e.e.layerY;
                }
            },
        });

        // ズームイベント
        /*
        canvas.on('mouse:wheel', function(opt) {
          var delta = opt.e.deltaY;
          var pointer = canvas.getPointer(opt.e,true);
          var zoom = canvas.getZoom();
          zoom = zoom - delta/500;
          if (zoom > 20) zoom = 20;
          if (zoom < 0.01) zoom = 0.01;
          canvas.zoomToPoint({ x: opt.e.offsetX, y: opt.e.offsetY }, zoom);
          opt.e.preventDefault();
          opt.e.stopPropagation();
        });
        */
    }

    /*
    * 新規入力欄RECT生成
    */
    this.regist_inputRect = function(x,y,width,height,alignment,intercepter){
        // 基盤のrect作成
        var rect = new fabric.Rect({ 
            width: width, height: height,
            fill: '#3C8DBC', opacity: 0.2,
            });

        // 入力欄text作成
        var tmp_name = '入力'+(input_num+1); // 一時テキスト
        var text = new fabric.IText(tmp_name, {
            width: width, height: height,
            fontSize:16, textAlign: alignment
        });

        // group化してcanvas追加
        var group = new fabric.Group([rect,text],{
            left: x, top: y,
            cornerSize: 6, hasRotatingPoint : false,
        });
        canvas.add(group)

        // インタセプターがあれば実行
        if ( intercepter ){ intercepter(group); }

        // センタリング定義
        self.set_text_center(text,rect,alignment);

        // 入力欄として保存
        self.regist_inputForm(group);
    }

    /*
    * 新規入力欄の追加
    */
    this.regist_inputForm = function(group){
        // 入力番号インクリメント
        input_num += 1;
        var input_name = "入力" +input_num;

        // テキスト設定
        text = group._objects[1]; // テキストエレメント抽出

        // プリセットされたMetanameを尊重
        var preset_metaName = text.metaName;
        console.log(text)
        text.text = preset_metaName || input_name;
        text.metaName = preset_metaName || input_name;
        text.align_type = text.align_type || alignment || "left"; // デフォルト値

        // 入力欄保管庫に保存
        elem_holder[input_num] = group;

        // フォームエリアに追加
        $("#form-area").append(
            '<div class="form-group col-sm-12 row">'
                +'<div class="col-sm-12"><label class="control-label">入力欄'+input_num+'</label></div>'
                +'<div class="col-sm-12">'
                +'<input type="text" class="input-name form-control form-input" placeholder="入力項目名" data-target="'+input_num+'">' // 項目名
                +'<select class="input-type form-control col-sm-4" data-target="'+ input_num+'">' // 入力タイプ
                    +'<option value="input">入力欄</option> <option value="承認欄">承認欄</option> <option value="checkbox">チェックボックス</option> <option value="select">選択○</option>'
                +'</select>'
                +'<input type="text" class="default-value form-control form-input" placeholder="デフォルト値" data-target="'+input_num+'" autocomplete="on" list="dv">' // デフォルト値
                +'<datalist id="dv">'
                +'<option value="%full_year%">西暦</option> <option value="%lower_year%">西暦下二桁</option> <option value="%jp_year%">和暦</option>'
                +'<option value="%jp_era%">元号</option> <option value="%month%">月(入力月)</option> <option value="%date%">日(入力日)</option>'
                +'<option value="%day%">曜日(入力日)</option><option value="%name%">名前(入力者)</option>'
                +'</datalist>'
                +'<select class="align-type form-control col-sm-4" data-target="'+ input_num+'">' // アライメント
                    +'<option value="left">左寄せ</option> <option value="center">中央揃え</option> <option value="right">右寄せ</option>'
                +'</select>'
                +'</div>'
            +'</div>'
            );
        // イベントつける
        $(".input-name").change(function(){
            // 値を変える 
            elem_holder[$(this).attr("data-target")].item(1).set({ text : $(this).val() });
            // メタ名も一緒につける
            elem_holder[$(this).attr("data-target")].item(1).metaName = $(this).val();

            canvas.renderAll(); // レンダリング
        });
        $(".default-value").change(function(){
            // デフォルト値くっつける
            elem_holder[$(this).attr("data-target")].item(1).defaultValue = $(this).val();
        });
        $(".input-type").change(function(){
            // データ型くっつける
            elem_holder[$(this).attr("data-target")].item(1).input_type = $(this).val();
        });
        $(".align-type").change(function(){
            // データ型くっつける
            elem_holder[$(this).attr("data-target")].item(1).align_type = $(this).val();
        });

        // 逆連関
        if (text.input_type){ // input_typeの逆反映
            $(".input-type[data-target='"+input_num+"'").val(text.input_type);
        }
        if (text.defaultValue){ // defaultValueの逆反映
            $(".default-value[data-target='"+input_num+"'").val(text.defaultValue);
        }
        if (preset_metaName){ // メタ名の逆反映
            $(".input-name[data-target='"+input_num+"'").val(preset_metaName);
        }
        if (text.align_type){ // アライメントの逆反映
            $(".align-type[data-target='"+input_num+"'").val(text.align_type);
        }
    }

    /* フォームデータJSONを生成 */
    this.gen_dataJSON = function(){
        // JSONデータ
        var data = {};

        // Elemを簡易化
        if (Object.keys(elem_holder).length){ // フォームジェネレーション時
            Object.entries(elem_holder).forEach( (item,i) => {
                var elem = item[1];
                if (elem._objects){
                    var rect = elem._objects[0]
                    var text = elem._objects[1]
                    var metaName = text.metaName; // メタ名
                    // データに追加
                    data[metaName] = {
                        x : elem.left ,
                        y : elem.top,
                        width : rect.width,
                        height : rect.height,
                        text : text.text,
                        font : text.fontSize,
                        order : i, // 順序
                        defaultValue : text.defaultValue, // デフォルト値
                        input_type : text.input_type, // 入力タイプ
                        align_type: text.align_type,  // アライメント
                    };
                }
            })
        } else if (elem_list.length){ // フォーム入力時
            // データリストつくる
            elem_list.forEach( (elem,i) => {
                var metaName = elem.metaName; // メタ名
                // データ追加
                data[metaName] = {
                    x : elem.base_x ,
                    y : elem.base_y,
                    width : elem.base_width, // 読み込み時保存された値
                    height : elem.base_height, // 読み込み時保存された値
                    text : elem.text,
                    font : elem.fontSize,
                    defaultValue : elem.defaultValue,
                    input_type : elem.input_type,
                    align_type: elem.align_type,  // アライメント
                };
            })
        }

        // JSON化
        return JSON.stringify(data);
    }

    /* JSONデータからフォーム読み込み*/
    this.load_formJson = function(_json){
        mode = "creation"; // フォーム生成モード

        // jsonからオブジェクトデータ構築
        var json_data = JSON.parse(_json);

        // くるくるしてインプットレクトの復元
        Object.keys(json_data).forEach( metaName => {
            // 値
            var v = json_data[metaName];
            var align_type = v.align_type || "center"; // 前方互換対応

            // グループに属性値貼り付ける関数
            var intercepter = (group) => {
                // テキスト抜く
                var text = group._objects[1];
                // デフォルト値入れる
                text.defaultValue = v.defaultValue || "";
                // 入力タイプ入れる
                text.input_type = v.input_type || "";
                // メタ名を入れる
                text.metaName = metaName;
                // アライメントを入れる
                text.align_type = align_type;
            }
            // つくる
            self.regist_inputRect(v.x,v.y,v.width,v.height,align_type,intercepter);
        })
    }

    /* jsonデータからふぉーむつくる*/
    this.load_dataJson = function(_json){
        /* フォーム生成 */
        mode = "form"; // フォーム受付モード

        // jsonからオブジェクトデータ構築
        var json_data = JSON.parse(_json);
        // メタ名でくるくるしてBoxつくる
        Object.keys(json_data).forEach( metaName => {
            // データ
            var data = json_data[metaName];
            var input_type = data.input_type; // 入力タイプ
            var align_type = data.align_type || "center"; // 前方互換対応

            // データ束縛関数
            var data_binding = elem => {
                elem.metaName = metaName;
                elem.defaultValue = data.defaultValue;
                elem.input_type = input_type;
                elem.align_type = align_type;
                // 読み込み時の値の保存
                elem.base_width = data.width;
                elem.base_height = data.height;
                elem.base_x = data.x;
                elem.base_y = data.y;
            }

            // 基礎データ抽出
            var settings = {
                left : data.x,
                top : data.y,
                width : data.width,
                height : data.height,
                text : data.text,
                hasControls : false,
                hasBorders : false,
            }

            // レクトつくる
            var rect = new fabric.Rect({ 
                fill: '#e8e8e8', opacity: 0.2,
                selectable: false,
                });
            rect.set(settings);

            if (input_type == "承認欄"){ // 承認欄
                // 属性地束縛
                data_binding(rect)
                
                // ペースタブルにする
                self.set_pastable(rect,"seal-id")

                // テキストがあれば判子あるので張る
                if (data.text){
                    rect.do_paste(); // ペタ
                }

            } else { // 入力欄
                // textつくる
                var text = new fabric.IText(data.text, {
                    fontSize:16, textAlign: align_type,
                });

                // 属性地束縛
                data_binding(text)

                // 共通設定あてる
                text.set(settings);

                // エディタぶるディクトつくる
                self.add_editableRect(rect,text,input_type,align_type);
                // タバーにアッペンドする
                tabber.push(text);
            }
        })
        
        canvas.renderAll();
    }

    /**
    * ペースタブルにする
    */
    this.set_pastable = function(rect,_id){
        var _rect = rect;

        // クロージャ用画像読み
        var imgElem = document.getElementById(_id);
        var imgInst = new fabric.Image(imgElem,{
            left : _rect.left,
            top : _rect.top,
            selectable: false,
        });

        // ペーストする関数
        var flag = false; // 存在フラグ
        var do_paste = function(){
            if (flag){ // あれば消す
                canvas.remove(imgInst);
                _rect.text = ""; // テキストを消す
                flag = false; // フラグ下げる
            } else { // なければ画像ぺタ
                canvas.add(imgInst);
                _rect.text = $(imgElem).attr("src"); // ソース入れとく
                flag = true; // フラグ上げる
            }
        }
        _rect.do_paste = do_paste; // 束縛しとく

        // クリックされたらぺタ
        canvas.on("mouse:down",function(opt){
            if ( opt.target == _rect || opt.target == imgInst){
                // ペースト
                do_paste();
                // インタラクティブモードなら送信
                self.interactive_commit(_rect);
            }
        });

        canvas.add(rect);
        // ElemListにほうりこむ
        elem_list.push(rect);
    }

    /* DOMイベントの初期化 */
    this.init_domEvents = function(){
        // Nomal Events
        $('form').submit(function(e) { e.preventDefault();return false; });
    }

    /* キーイベントアクティベーション */
    this.init_keyEvents = function(){
        $(window).keyup( e => {
            // タバー処理
            if (e.keyCode == 9 && tabber){
                now_tabber += 1;
                if (tabber.length <= now_tabber){
                    now_tabber = 0; // reset 
                }
                var elem = tabber[now_tabber];
                // フォーカス移動 
                elem.enterEditing();
                elem.selectAll();
            }

            // コピペ処理
            if (e.ctrlKey){
                if (e.keyCode == 67){
                    self.copy_elem(); // コピー
                } else if (e.keyCode == 86){
                    self.paste_elem(); // ペースト
                }
            }
        });
    }

    /* 
    エディタぶるなRectをアッペンド
    新版。普通にやるver
    */
    var active_text = null; // フォーカス対象テキスト
    this.add_editableRect = function(rect,text,input_type,alignment){
        /* 大きさ変更等不可 */
        text.hasControls = false;
        text.hasBorders = false;

        /* 入力イベント定義 */
        var _rect = rect; // for closure
        var _text = text; // for closure
        // 入力タイプで分岐
        if (input_type == "checkbox"){ // チェックマーク
            self.set_checkableRect(_rect,_text,"✓"); // チェッカブルレクトにする
        } else if (input_type == "select"){ // ○
            self.set_checkableRect(_rect,_text,"○",40); // チェッカブルレクトにする
        } else {
            // ワンクリックで入力モード
            canvas.on("mouse:down",function(opt){
                if ( opt.target == _text || opt.target == _rect ){
                    _text.enterEditing();
                    _text.selectAll()
                } else {
                    if (active_text){
                        active_text.exitEditing();
                        active_text = null; // フォーカス抜く
                    }
                }
            });
        }

        canvas.on("text:editing:exited", function(opt){
            if ( opt.target == _text ){
                _text.dirty = false;
                canvas.renderAll();
                active_text = null; // フォーカス抜く

                // インタラクティブモードなら送信
                self.interactive_commit(_text);
            }
        });
        canvas.on("text:editing:entered", function(opt){
            if ( opt.target == _text ){
                setTimeout(_ =>{ // 時差処理
                    active_text = opt.target; // アクティブなターゲットとする
                    },1000) 
                self.update_now_tabber(opt.target); // タバー更新
                //canvas.zoomToPoint({ x: _text.left, y: _text.top }, 1.5); // zoom
            }
        })

        // キャンバスに追加
        canvas.add(rect);
        canvas.add(text);

        // センタリング定義
        self.set_text_center(text,rect,alignment);

        // ElemListにほうりこむ
        elem_list.push(text);
    }

    /*
    * チェッカブルレクトにする
    */
    this.set_checkableRect = function(rect,text,check,font_size){
        // クロージャ束縛
        var _text = text;
        var _rect = rect;
        var _check = check;

        // フォントサイズ調整
        _text.set({ fontSize:font_size || 25 }); // デフォルト25

        // クリックでチェック化
        canvas.on("mouse:down",function(opt){
            if ( opt.target == _text || opt.target == _rect ){
                if (_text.text){ _text.text = ""; } // あればなくす
                else { _text.text = _check; } // チェックマークつける
                _text.do_centering(); // センタリング。センタリング設定関数で束縛される
                setTimeout(_ => {
                    _text.exitEditing(); // エグジットイベントをディスパッチ
                    },500);
            }
        });
    }

    /**
    * インタラクティブコミット
    */
    this.interactive_commit = function(elem){
        /* インタラクティブ送信モード*/
        if ( commit_mode == "interactive" ){
            setTimeout( _ => {
                // データ構築
                var data = {};
                data[elem.metaName] = elem.text;
                $.post(URL_FOR_COMMIT,{ "data": JSON.stringify(data) }); // Ajaxで送信
                noty({text: 'データを送信しました', layout: 'topCenter', type: 'information', timeout:2000 });
            },0);
        }
    }

    /**
    * タバー位置調整関数
    */
    this.update_now_tabber = function(text){
        // 位置を探して保存
        now_tabber = tabber.findIndex( elem => elem === text )
    }

    /**
    * コピー関数
    * アクティブオブジェクトを保管
    */
    var _clipboard = null;
    var copy_base = null; 
    this.copy_elem = function(){
        // コピーベースオブジェクトの保存
        copy_base = canvas.getActiveObject()
        // クローンして保管
        copy_base.clone(function(cloned) {
            _clipboard = cloned; // copy
            });
    }

    /*
    * ペースト関数
    * アクティブオブジェクトを複製
    * 複製後、新規入力欄として登録処理
    */
    this.paste_elem = function(){
        // クローンする
        _clipboard.clone(function(clonedObj) {
            canvas.discardActiveObject();

            // クローン対象をキャンバスに張って入力欄としてエディタぶるレクトをコピーする
            if (clonedObj.type === 'activeSelection') { // 複数選択範囲レクト
                // 位置調整 : 表形式用に高さ分だけそのまま下げる
                clonedObj.set({
                    top: clonedObj.top + clonedObj.height,
                    evented: true,
                });
                /* キャンバスレベルコピー */
                // active selection needs a reference to the canvas.
                clonedObj.canvas = canvas;
                clonedObj.forEachObject(function(obj) {
                    canvas.add(obj);
                });
                // this should solve the unselectability
                clonedObj.setCoords();

                /* エディタブルレクトレベルコピー */
                // 選択されたレクトごとに属性をコピーして入力欄として保存
                copy_base._objects.forEach( (editableRect,index) => {
                    // クローン済み対象レクト抽出
                    var clone_rect = clonedObj._objects[index];

                    // 属性コピー
                    self.copy_editableRectAttr(editableRect,clone_rect);
                    
                    // 入力欄として登録
                    self.regist_inputForm(clone_rect);
                });
                console.log(clonedObj);

                // 繰り返しコピペ用調整
                _clipboard.top += clonedObj.height;

            } else { // 通常のエディタぶるレクト
                // 位置調整 : 少し斜め下のそれっぽい位置におく
                clonedObj.set({
                    left: clonedObj.left + 10,
                    top: clonedObj.top + 10,
                    evented: true,
                });

                // 描画
                canvas.add(clonedObj);

                // コピーベースのレクトから今作ったクローンへ属性コピーする
                self.copy_editableRectAttr(copy_base,clonedObj);

                // 入力欄として登録
                self.regist_inputForm(clonedObj);

                // 繰り返しコピペ用調整
                _clipboard.top += 10;
                _clipboard.left += 10;
            }

            canvas.setActiveObject(clonedObj);
            canvas.requestRenderAll();
        });
    }

    /*
    * ２つのエディタブルレクトの属性コピー
    */
    this.copy_editableRectAttr = function(from_rect,to_rect){
        // コピーベースからinput_type/defaultValueの同期 => text間のやり取り
        to_rect._objects[1].input_type = from_rect._objects[1].input_type;
        to_rect._objects[1].defaultValue = from_rect._objects[1].defaultValue;
    }

    /* UUIDゲッタ */
    this.get_uuid = function(){
        return $("#uuid").val(); // UUID抜く
    }

    /* Ajax関数 */
    var URL_FOR_FORM = "/save/";
    var URL_FOR_PDF = "/output/";
    var URL_FOR_COMMIT = "/commit/"

    // コミットURL注入関数
    this.set_form_save_url = function(url){ URL_FOR_FORM = url; }
    this.set_commit_url = function(url){ URL_FOR_COMMIT = url; }

    /* 送信関数 */
    this.init_ajaxEvents = function(){
        // フォーム生成ボタン
        $("#gen_form").click(function(){
            var form_name = $("#form-name").val(); // 名前抜く
            // ふぉーむつくる
            var $form = $('<form/>', {'action': URL_FOR_FORM, 'method': 'post'});
            $form.append($('<input/>', {'type': 'hidden', 'name': "data", 'value': self.gen_dataJSON()}));
            $form.append($('<input/>', {'type': 'hidden', 'name': "uuid", 'value': uuid}));
            $form.append($('<input/>', {'type': 'hidden', 'name': "form_name", 'value': form_name}));
            $form.appendTo(document.body);
            $form.submit(); // サブミット
        });
        // PDF生成ボタン
        $("#gen_pdf").click(function(){
            // ふぉーむつくる
            var $form = $('<form/>', {'action': URL_FOR_PDF, 'method': 'post', "target" : "_blank"});
            $form.append($('<input/>', {'type': 'hidden', 'name': "data", 'value': self.gen_dataJSON()}));
            $form.append($('<input/>', {'type': 'hidden', 'name': "uuid", 'value': uuid}));
            $form.appendTo(document.body);
            $form.submit(); // サブミット
        });
        // 入力終了ボタン
        $("#commit").click(function(){
            var form_name = $("#form-name").val(); // 名前抜く
            // ふぉーむつくる
            var $form = $('<form/>', {'action': URL_FOR_COMMIT, 'method': 'post'});
            $form.append($('<input/>', {'type': 'hidden', 'name': "data", 'value': self.gen_dataJSON()}));
            $form.append($('<input/>', {'type': 'hidden', 'name': "uuid", 'value': uuid}));
            $form.append($('<input/>', {'type': 'hidden', 'name': "form_name", 'value': form_name}));
            $form.appendTo(document.body);

            // 送信
            if (commit_mode == "form"){
                $form.submit(); // サブミット
            } else if(commit_mode == "ajax"){
                $.post(URL_FOR_COMMIT, $form.serialize()); // Ajaxで送信
                noty({text: 'データを送信しました', layout: 'topCenter', type: 'information', timeout:2000 });
            }
        })
    }

    /**
    * デフォルト値入力補完する
    */
    var now = new Date();
    this.complete_default = function(openmode){
        // 全エレメントを捜査する
        elem_list.forEach( elem => {
            if ( openmode && elem.text ){ return; } // ファイル展開モード:既にあれば戻る
            // デフォルト値設定
            switch(elem.defaultValue){
                case "%full_year%": // フル西暦
                    elem.set({ "text" : now.getFullYear().toString() });
                    break;
                case "%lower_year%": // 西暦下二桁
                    elem.set({ "text" : now.getFullYear().toString().slice(-2) });
                    break;
                case "%jp_year%": // 和暦
                    elem.set({ "text" : now.toLocaleDateString("ja-JP-u-ca-japanese",{year:"numeric"}).slice(0,2) });
                    break;
                case "%jp_era%": // 元号
                    elem.set({ "text" : now.toLocaleDateString("ja-JP-u-ca-japanese",{"era":"short"}).slice(-1) });
                    break;
                case "%month%": // 月
                    elem.set({ "text" : (now.getMonth()+1).toString() });
                    break;
                case "%date%": // 日
                    elem.set({ "text" : now.getDate().toString() });
                    break;
                case "%day%": // 曜日
                    elem.set({ "text" : ["日","月","火","水","木","金","土"][now.getDay()] });
                    break;
                case "%name%": // 名前
                    elem.set({ "text" : "神長優舞" });
                    break;
                case undefined:
                    elem.set({ "text" : "" });
                    break;
                default :
                    elem.set({ "text" : elem.defaultValue });
            }
            // 変化イベントかける
            canvas.trigger('text:changed', {target: elem});
        });
    }

    /**
    * テキストをレクトの中央にする
    */
    this.set_text_center = function(_text,_rect,alignment){
        // クロージャ用に名前再束縛
        var text = _text;
        var rect = _rect;
        // センタリング関数
        var do_centering = function(){
            // 中心地を計算
            var center_of_text = [ text.left +text.width/2, text.top +text.height/2 ];
            var center_of_rect = [ rect.left +rect.width/2, rect.top +rect.height/2 ];

            // 中心地の差分を取得
            diff = [
                center_of_rect[0] -center_of_text[0],
                center_of_rect[1] -center_of_text[1]
            ]

            // 差分をleft-topに適用
            pos = [
                text.left +diff[0],
                text.top +diff[1]
            ]

            // 適用
            if ( alignment == "center" ){
                text.set({
                    left : pos[0],
                    top : pos[1]
                });
            } else if ( alignment == "left" ){
                text.set({
                    top : pos[1]
                });
            } else if ( alignment == "right" ){ // 右寄せ
                var right_x = (rect.left +rect.width);
                text.set({
                    left : right_x -text.width,
                    top : pos[1]
                });
            }
        }

        // 変更イベントを束縛
        canvas.on('text:changed', function(e) {
            if ( e.target == text ){
                do_centering(); // センタリング関数する
            }
        });

        // _textに束縛しとく
        text.do_centering = do_centering;
        // とりまかける
        do_centering();
    }
}


// 読み込み時初期化
var app = new App();
$(function(){ 
    app.init();
    })

