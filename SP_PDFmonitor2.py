#必要なライブラリやモジュールをインポートする
import wx
import fitz
import os
import json
import threading
import uvicorn
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
import datetime
import csv

#端末のIPとユーザー名を取得するモジュール(SP_getIP.pyを同じディレクトリに配置していないとエラーが出る)
from SP_getIP import get_info
# ---------------------- 設定 ----------------------
#ベースとなるディレクトリまでのパスを環境変数から取得(環境変数未設定の場合起動しない為、事前設定必須)
TEST_DIR = os.environ.get("TEST_DIR")
if not TEST_DIR:
    raise EnvironmentError("TEST_DIR 環境変数が設定されていません。")

#設定ファイル用のディレクトリ
SETTINGS_DIR = os.path.join(TEST_DIR,"設定","手順書")
os.makedirs(SETTINGS_DIR, exist_ok=True)

# ---------------------- 状態管理 ----------------------
class State:
    def __init__(self):
        #排他制御用のロック
        self.lock = threading.RLock()
        #作業者、品番など
        self.item = "未取得"
        self.worker = "未取得"
        #測定項目の管理用変数
        self.steps = []
        self.step_baselines = {}
        #各PDFファイルまでのパス
        self.pdf_path = None
        self.draw_path = None
        self.another1_path = None
        self.another2_path = None
        self.last_loaded_key = None
        #状態を管理する為のフラグ
        self.start_flag = False  #生産開始のフラグ(GUI側で監視)
        self.end_flag = False
        
        self.machine_name = self.get_machine()#実行端末の設置されている旋盤機名を取得

        #万が一対応する旋盤機名が無かった際のセーフティ(旋盤機名の未登録やネットワークの未接続時は必ずエラーが出る為、事前登録必須)
        if not self.machine_name:
            raise RuntimeError("この端末に対応するマシン定義がありません")

    #IPと端末のユーザー名から設置箇所を取得    
    def get_machine(self):
        pi = get_info()
        user = pi["user"]
        device_ip = pi["deviceip"]
        machine_path=os.path.join(SETTINGS_DIR,"ip_date.json")

        with open(machine_path, "r", encoding="utf-8") as f:
            machine_date = json.load(f)

        for machine, map in machine_date.items():
            for usr,ip in map.items():
                if usr == user and ip == device_ip:
                    return machine
        return None        


    # PDFの読み込み
    def load_resources(self):
        #各種PDFファイルのパスを取得
        pdf_file = os.path.join(SETTINGS_DIR,self.machine_name,self.item,"process.pdf")
        draw_file = os.path.join(SETTINGS_DIR,self.machine_name,self.item,"draw.pdf")
        a1_file = os.path.join(SETTINGS_DIR,self.machine_name,self.item,"another1.pdf")
        a2_file = os.path.join(SETTINGS_DIR,self.machine_name,self.item,"another2.pdf")
        
        #測定項目の読み込み用パスを取得
        json_file = os.path.join(SETTINGS_DIR,self.machine_name,self.item,"item_date.json")
        
        #その他が無い場合は続行するが図面と手順書が無い場合は止まる為、ダミーでもPDFを用意してください
        if not (os.path.exists(pdf_file)) and not (os.path.exists(draw_file)):
            return False
        
        #取得したパス等を変数に格納(現状リセットは行わず、上書きする形式)
        try:
            #先ほどのパスから測定項目の読み込み
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.step_baselines = data
                self.steps = list(data.keys())

            #各PDFファイルのパスを変数に格納
            self.pdf_path = pdf_file
            self.draw_path = draw_file
            self.another1_path = a1_file
            self.another2_path = a2_file
            self.last_loaded_key = self.item
            return True
        except Exception:
            return False

state = State()

# ========== FASTAPI ==========
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# POST でライン・品番・作業者・フラグを受け取る
@app.post("/set_status")
async def set_status(request:Request):
    data = await request.json()
    with state.lock:
        state.item = data.get("item")
        state.worker = data.get("worker")
        state.start_flag = data.get("start_flag")
    return {"received": True}

#生産終了のフラグを受け取る
@app.post("/end_status")
async def end_status(request:Request):
    data = await request.json()
    with state.lock:
        state.item = data.get("item")
        state.worker = data.get("worker")
        state.end_flag = data.get("end_flag")
    return {"received": True}

#host=0.0.0.0を推奨、外部からのアクセスが出来ない場合は固定IPに変更
def start_api():
    uvicorn.run(app, host="0.0.0.0", port=8200, log_level="warning")

# テンキー用クラス（小数点対応版）
class KeypadDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="テンキー", size=(450, 600))
        panel = wx.Panel(self)
        font = wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        panel.SetBackgroundColour("#2b2b3c")
        
        self.input = wx.TextCtrl(panel, style=wx.TE_RIGHT)
        self.input.SetFont(font)

        # ---- 小数点追加 ----
        grid = wx.GridSizer(4, 3, 5, 5)
        buttons = ["7", "8", "9",
                   "4", "5", "6",
                   "1", "2", "3",
                   "C", "0", ".",  # "." を追加
                   "←"
        ]
        # 最後の "←" が配置ずれしないよう、GridSizer を 5行 x 3列 にする
        grid = wx.GridSizer(5, 3, 5, 5)

        # 並べ直し
        buttons = [
            "7", "8", "9",
            "4", "5", "6",
            "1", "2", "3",
            "C", "0", ".",
            "←", "", ""    # 空枠2つでレイアウトを整える
        ]

        for label in buttons:
            if label == "":
                grid.Add(wx.Panel(panel))  # 空スペース
                continue

            btn = wx.Button(panel, label=label)
            btn.SetFont(font)
            btn.Bind(wx.EVT_BUTTON, self.on_key)
            btn.SetBackgroundColour("#C0C0C0")
            grid.Add(btn, 0, wx.EXPAND)
        
        self.ok_btn = wx.Button(panel, label="決定")
        self.ok_btn.SetFont(font)
        self.ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        self.ok_btn.SetBackgroundColour("#00FF00")
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.input, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(grid, 8, wx.EXPAND | wx.ALL, 10)
        sizer.Add(self.ok_btn, 2, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(sizer)
        self.value = ""
        
    # 各キーの処理    
    def on_key(self, event):
        label = event.GetEventObject().GetLabel()
        current = self.input.GetValue()

        if label == "C":
            self.input.SetValue("")

        elif label == "←":
            self.input.SetValue(current[:-1])

        elif label == ".":
            # 小数点の多重入力を防ぐ
            if "." not in current:
                self.input.SetValue(current + label)

        else:
            self.input.SetValue(current + label)
    
    # 決定押した際の処理
    def on_ok(self, event):
        self.value = self.input.GetValue()
        self.EndModal(wx.ID_OK)

# ========== GUI部分 ==========
class PDFStepEntryApp(wx.Frame):
    def __init__(self):
        super().__init__(None, title="手順書モニター", size=(1680, 940))#メインウィンドウのサイズ指定(モニターのサイズが変わった場合は変更推奨)
        
        #測定項目用の変数
        self.steps = []
        self.total_steps = 0
        self.current_step = 0
        self.results = []
        self.total_results = []

        #PDFファイル用の変数
        self.dpage = None
        self.prpage = None
        self.a1page = None
        self.a2page = None
        self.select_page = None

        self.InitUI()
        self.Centre()
        self.Show()

        # タイマーでフラグ監視
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(1000)  # 1秒ごと

    # ====== GUI構築 ======
    def InitUI(self):
        panel = wx.Panel(self)
        main = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        panel.SetBackgroundColour("#07021DC5")

        #上側
        right = wx.BoxSizer(wx.VERTICAL)
        self.pdf_bitmap = wx.StaticBitmap(panel)
        
        #基本情報のラベルやボタンなどの生成
        font = wx.Font(30, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        cfont = wx.Font(26, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        lfont = wx.Font(13, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        
        self.item_label = wx.StaticText(panel, label="品番: 未取得")
        self.item_label.SetFont(font)
        self.item_label.SetForegroundColour("#91FF00")

        self.worker_label = wx.StaticText(panel, label="作業者: 未取得")
        self.worker_label.SetFont(font)
        self.worker_label.SetForegroundColour("#00E6D2")

        self.process_btn = wx.Button(panel, label="手順書")
        self.draw_btn = wx.Button(panel, label="図面")
        self.another1_btn = wx.Button(panel, label="その他1")
        self.another2_btn = wx.Button(panel, label="その他2")

        #上側の基本情報のラベルやボタンの設置
        line_box = wx.BoxSizer(wx.HORIZONTAL)
        line_box.Add(self.item_label, flag=wx.LEFT, border=20)
        line_box.Add(self.worker_label, flag=wx.LEFT, border=20)
        line_box.Add(self.process_btn,flag=wx.LEFT, border=100)
        line_box.Add(self.draw_btn,flag=wx.LEFT, border=20)
        line_box.Add(self.another1_btn,flag=wx.LEFT, border=20)
        line_box.Add(self.another2_btn,flag=wx.LEFT, border=20)
        
        # 右側
        #検査関連のラベル設置
        category_box = wx.BoxSizer(wx.VERTICAL)

        self.input_label = wx.StaticText(panel, label="測定項目:未選択")
        self.input_label.SetFont(cfont)
        self.input_label.SetForegroundColour("#FFFFFF")
        category_box.Add(self.input_label, flag=wx.EXPAND | wx.LEFT, border=5)

        self.baseline_label = wx.StaticText(panel, label="基準値:-")
        self.baseline_label.SetFont(cfont)
        self.baseline_label.SetForegroundColour("#FFFFFF")
        category_box.Add(self.baseline_label, flag=wx.EXPAND | wx.LEFT, border=5)

        #入力欄の設置
        value_box = wx.BoxSizer(wx.HORIZONTAL)

        self.input_box = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER,size=(220,-1))
        self.input_box.SetFont(cfont)

        self.keypad_btn = wx.Button(panel,label="テンキー")
        self.keypad_btn.SetFont(cfont)

        value_box.Add(self.input_box, flag=wx.EXPAND|wx.LEFT, border=5)
        value_box.Add(self.keypad_btn, flag=wx.EXPAND | wx.LEFT, border=5)

        #操作用のボタン類設置
        btn_box = wx.BoxSizer(wx.VERTICAL)
        self.time_combo = wx.ComboBox(panel,choices=["初物","中物","終物"],style=wx.CB_READONLY)
        self.time_combo.SetSelection(0)
        self.time_combo.SetFont(cfont)
        btn_box.Add(self.time_combo, flag=wx.EXPAND | wx.LEFT, border=5)

        cbtn_box = wx.BoxSizer(wx.HORIZONTAL)
        self.prev_step_btn = wx.Button(panel, label="前へ")
        self.prev_step_btn.SetFont(cfont)
        self.next_step_btn = wx.Button(panel, label="次へ")
        self.next_step_btn.SetFont(cfont)
        cbtn_box.Add(self.prev_step_btn, flag=wx.EXPAND | wx.LEFT, border=5)
        cbtn_box.Add(self.next_step_btn, flag=wx.EXPAND | wx.LEFT, border=5)
        btn_box.Add(cbtn_box, flag=wx.EXPAND | wx.LEFT, border=0)
        
        self.register_btn = wx.Button(panel,label="登録して1項目へ")
        self.finish_btn = wx.Button(panel, label="保存して終了")

        for opb in [self.register_btn, self.finish_btn]:
            opb.SetFont(cfont)
            btn_box.Add(opb, flag=wx.EXPAND | wx.LEFT, border=5)

        #測定記録のリスト
        self.record_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.record_list.InsertColumn(0, "時間", width=45)
        self.record_list.InsertColumn(1, "作業者", width=70)
        self.record_list.SetFont(lfont)
        
        #右側の各種要素を配置
        right.Add(category_box, flag=wx.TOP | wx.LEFT, border=1)
        right.Add(value_box,flag=wx.TOP | wx.LEFT, border=1)
        right.Add(btn_box,flag=wx.TOP | wx.LEFT, border=1)
        right.Add(self.record_list, flag=wx.EXPAND | wx.ALL, border=5)

        #各種ボタンの機能固定
        #数値による自動判定
        self.input_box.Bind(wx.EVT_TEXT_ENTER, self.on_next_step)
        #PDF表示用ボタン
        self.process_btn.Bind(wx.EVT_BUTTON, self.on_process)
        self.draw_btn.Bind(wx.EVT_BUTTON, self.on_draw)
        self.another1_btn.Bind(wx.EVT_BUTTON,self.on_another1)
        self.another2_btn.Bind(wx.EVT_BUTTON,self.on_another2)
        #測定ステップ用ボタン
        self.next_step_btn.Bind(wx.EVT_BUTTON,self.on_next_step)
        self.prev_step_btn.Bind(wx.EVT_BUTTON,self.on_prev_step)
        #登録・終了用ボタン
        self.register_btn.Bind(wx.EVT_BUTTON,self.on_register)
        self.finish_btn.Bind(wx.EVT_BUTTON,self.on_finish)
        #その他
        self.input_box.Bind(wx.EVT_TEXT,self.on_input_change)
        self.keypad_btn.Bind(wx.EVT_BUTTON,self.on_keypad)

        #ボタンの一括フォント指定
        for b in[self.process_btn,self.draw_btn,self.another1_btn,self.another2_btn]:
            b.SetFont(cfont)        
        self.btn_set_colors()

        #全体のレイアウト設定
        #PDFの表示領域と右側の操作領域を配置(proportionが比率)
        hbox.Add(self.pdf_bitmap, proportion=3, flag=wx.EXPAND|wx.ALL, border=0)
        hbox.Add(right, proportion=1, flag=wx.EXPAND|wx.ALL, border=0)

        #上部に基本情報、下部に先ほどの左右分割領域を配置
        main.Add(line_box,proportion=1,flag=wx.TOP,border=0)
        main.Add(hbox,proportion=9,flag=wx.EXPAND|wx.ALL,border=0)
        panel.SetSizer(main)

    #各ボタンの色指定(Backgroundがボタン、Foregroundが文字)    
    def btn_set_colors(self):
        #手順書表示
        self.process_btn.SetBackgroundColour("#7AC404")
        self.process_btn.SetForegroundColour("#E2E2E2")
        #図面表示
        self.draw_btn.SetBackgroundColour("#622F72FF")
        self.draw_btn.SetForegroundColour("#E2E2E2")
        #その他1表示
        self.another1_btn.SetBackgroundColour("#009CCC")
        self.another1_btn.SetForegroundColour("#E2E2E2")
        #その他1表示
        self.another2_btn.SetBackgroundColour("#27A570")
        self.another2_btn.SetForegroundColour("#E2E2E2")
        #前に戻る
        self.prev_step_btn.SetBackgroundColour("#D84F00")
        self.prev_step_btn.SetForegroundColour("#E2E2E2")
        #次へ進む
        self.next_step_btn.SetBackgroundColour("#00D1AE")
        self.next_step_btn.SetForegroundColour("#E2E2E2")
        #登録して1項目へ
        self.register_btn.SetBackgroundColour("#02C432")
        self.register_btn.SetForegroundColour("#E2E2E2")
        #保存して終了
        self.finish_btn.SetBackgroundColour("#C70D0D")
        self.finish_btn.SetForegroundColour("#E2E2E2")
        #テンキー表示
        self.keypad_btn.SetBackgroundColour("#4900D1")
        self.keypad_btn.SetForegroundColour("#E2E2E2")
                                              
    # ====== テンキー表示 ======
    def on_keypad(self, _):
        dlg = KeypadDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            value = dlg.value
            self.input_box.SetValue(value)
        dlg.Destroy()

    # ====== タイマーでフラグ監視 ======
    def on_timer(self, _):
        with state.lock:
            # ラベル更新
            self.item_label.SetLabel(f"品番:{state.item}")
            self.worker_label.SetLabel(f"作業者:{state.worker}")

            # フラグが立ったらPDFファイルをロード
            if state.start_flag:
                if state.load_resources():
                    self.prpage = self.load_pdf(state.pdf_path,"prpage")
                    self.dpage = self.load_pdf(state.draw_path,"draw")
                    self.a1page = self.load_pdf(state.another1_path,"another1")
                    self.a2page = self.load_pdf(state.another2_path,"another2")
                    self.update_pdf_image(self.prpage)
                    self.select_page = self.prpage
                    self.load_steps()
                state.start_flag = False  # 反映済みでリセット

            #生産終了したら表示もリセット
            if state.end_flag:
                self.on_finish(None)
                self.reset_state()
                self.show_step()
                state.end_flag = False


    # ====== PDF 読み込み ======

    #図面PDF読み込み用共通関数    
    def load_pdf(self,path,name:str):
        if not path:
            return
        try:
            doc = fitz.open(path)
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            png_path = f"{name}.png"
            pix.save(png_path)
            doc.close()
            return png_path
        except Exception:
            return

    #選択したPDF表示用の共通関数    
    def show_page(self,page_path):
        if not page_path:
            return
        if self.select_page == page_path:
            return
        self.update_pdf_image(page_path)
        self.select_page = page_path

    #手順書表示ボタン    
    def on_process(self,event):
        self.show_page(self.prpage)    

    #図面表示ボタン    
    def on_draw(self,event):
        self.show_page(self.dpage) 

    #その他1表示ボタン    
    def on_another1(self,event):
        self.show_page(self.a1page)    

    #その他2表示ボタン    
    def on_another2(self,event):
        self.show_page(self.a2page)

    #表示するPDFの更新    
    def update_pdf_image(self,path):
        if not path or not os.path.exists(path):
            return
        img = wx.Image(path, wx.BITMAP_TYPE_PNG)
        img = img.Scale(1435,900)#PDFの表示サイズの指定(メインウィンドウ同様モニターサイズが変わった際は変更推奨)
        self.pdf_bitmap.SetBitmap(wx.Bitmap(img))
        self.pdf_bitmap.Update()

    #古いpngのクリーンアップ
    def cleanup_png(self):
        for f in ("prpage.png", "draw.png", "another1.png", "another2.png"):
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
    
    #Listctrlのカラム生成            
    def build_columns(self):
        self.record_list.ClearAll()

        # 固定カラム
        headers = ["時間", "作業者"]

        # JSON から取得した検査項目
        headers.extend(self.steps)   # ["測定項目A", "測定項目B", ...]

        # カラム作成
        for i, h in enumerate(headers):
            self.record_list.InsertColumn(i, h, width=100)
        
        # 後で使えるよう保存
        self.dynamic_headers = headers
    

    #入力された数値の判定
    def on_input_change(self,event):
        """入力値が変わるたびに自動で判定して色分け"""
        value = self.input_box.GetValue().strip()

        # 対象ステップが存在しない場合
        if not self.steps:
            return

        step_name = self.steps[self.current_step]
        baseline = state.step_baselines.get(step_name)

        if not baseline or "min" not in baseline or "max" not in baseline:
            self.input_box.SetBackgroundColour(wx.NullColour)
            self.input_box.Refresh()
            return

        # 数値以外 → 初期色に戻す
        try:
            value_f = float(value)
            min_f = float(baseline.get("min"))
            max_f = float(baseline.get("max"))
        except:
            self.input_box.SetBackgroundColour(wx.NullColour)
            self.input_box.Refresh()
            return

        # 基準値内かの判定
        if min_f <= value_f <= max_f:
            self.input_box.SetBackgroundColour("#03E76A")  # 緑（視認性の良い緑）
        else:
            self.input_box.SetBackgroundColour("#F50743")  # 赤（注意色）

        self.input_box.Refresh()  # 色を即時反映

    # ====== 測定ステップ ======
    #測定項目の読み込み
    def load_steps(self):
        self.steps = state.steps
        self.total_steps = len(self.steps)
        self.results = [""] * self.total_steps
        self.build_columns()
        self.current_step = 0
        self.show_step()

    #読み込んだ測定ステップの表示    
    def show_step(self):
        #ステップが存在しなければ初期値を返す
        if not self.steps:
            self.input_label.SetLabel("測定項目")
            self.baseline_label.SetLabel("基準値:-")
            return
        
        step = self.steps[self.current_step]
        baseline = state.step_baselines.get(step, "-")
        minc = float(baseline.get("min"))
        maxc = float(baseline.get("max"))
        self.input_label.SetLabel(f"測定項目{self.current_step+1}/{self.total_steps}:{step}")
        self.baseline_label.SetLabel(f"基準値:最小{minc}~最大{maxc}")
        self.input_box.SetValue(self.results[self.current_step])
        self.input_box.SetBackgroundColour(wx.NullColour)
        self.input_box.Refresh()

    # ====== ボタン ======
    #前のステップへ戻る
    def on_prev_step(self, _):
        self.results[self.current_step] = self.input_box.GetValue().strip()
        if self.current_step > 0:
            self.current_step -= 1
            self.show_step()
            self.on_input_change(None)

    #次のステップへ進む        
    def on_next_step(self, _):
        self.results[self.current_step] = self.input_box.GetValue().strip()
        if self.current_step < self.total_steps - 1:
            self.current_step += 1
            self.show_step()
            self.on_input_change(None)

    #検査項目を登録して最初のステップへ        
    def on_register(self, _):
        # 入力値を現在ステップに反映（Enterや次へで更新されてない可能性を補う）
        self.results[self.current_step] = self.input_box.GetValue().strip()

        # 時刻
        time = self.time_combo.GetValue()

        # 作業者は state.worker を使用
        operator = state.worker

        # 行データ作成（インデックスループで安全に取り出す）
        row = [time, operator]
        for step_name, value in zip(self.steps, self.results):
            baseline = state.step_baselines.get(step_name)

            if value.strip() == "":
                row.append(f"{value} (NG)")
                continue

            try:
                f_val = float(value)
                f_min = float(baseline.get("min"))
                f_max = float(baseline.get("max"))

                # 基準値内かを判定
                if f_min <= f_val <= f_max:
                    row.append(f"{value} (OK)")
                else:
                    row.append(f"{value} (NG)")

            except:
                row.append(f"{value} (NG)")


        # ListCtrl に追加（末尾へ）
        insert_at = self.record_list.GetItemCount()
        index = self.record_list.InsertItem(insert_at, row[0])
        for col, value in enumerate(row):
            # InsertItem で追加した行の各セルを埋める
            try:
                self.record_list.SetItem(index, col, str(value))
            except Exception:
                # 万一列数が足りない場合に備えて ignore しつつ安全に続行
                pass

        # 次の検査開始に向けてステップをリセット
        self.results = [""] * len(self.steps)
        self.current_step = 0
        self.show_step()                            
    
    #登録されたデータをCSVに保存して終了    
    def on_finish(self, _):
        if not hasattr(self, "dynamic_headers"):
            return
        
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"測定_{now}.csv"
        filepath = os.path.join(TEST_DIR, "記録","測定記録",state.item,state.machine_name, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)

            # ヘッダー
            writer.writerow(self.dynamic_headers)

            # 全行書き出し
            row_count = self.record_list.GetItemCount()
            col_count = len(self.dynamic_headers)

            for row_idx in range(row_count):
                row = []
                for col_idx in range(col_count):
                    row.append(self.record_list.GetItemText(row_idx, col_idx))
                writer.writerow(row)

        self.reset_state()
        self.load_steps()

    #生産終了のフラグを受け取った際、リセットを掛ける為の関数   
    def reset_state(self):
        # GUI 側リセット
        #GUI側のファイルパスをリセット
        self.prpage = None
        self.dpage = None
        self.a1page = None
        self.a2page = None
        self.select_page = None

        #測定項目関連の変数も初期化
        self.steps = []
        self.total_steps = 0
        self.current_step = 0
        self.results = []
        self.total_results = []
        
        #ラベルの内容も初期化
        self.worker_label.SetLabel("作業者: 未取得")
        self.item_label.SetLabel("品番: 未取得")

        #PDFの表示領域を空にして古いpngを削除
        self.pdf_bitmap.SetBitmap(wx.NullBitmap)
        self.cleanup_png()

        # state側リセット
        with state.lock:
            #大元のパスを初期化
            state.pdf_path = None
            state.draw_path = None
            state.another1_path = None
            state.another2_path = None
            state.last_loaded_key = None
            #大元の測定項目関連の変数も初期化
            state.steps = []
            state.step_baselines = {}
            #開始フラグもリセットしておく
            state.start_flag = False

# ========== MAIN ==========
if __name__ == "__main__":
    # API を裏スレッドで起動
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()

    # GUI 起動
    app = wx.App()
    gui = PDFStepEntryApp()
    app.MainLoop()