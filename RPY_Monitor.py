# 使用するパッケージのインポート
import wx
import datetime
import os
from gpiozero import Button
import multiprocessing

#API関係のモジュール
from RPY_prodAPI import send_status,finish_status,send_log,product_log,finish_log
from SecretEffect import run_emergency
def trigger_emergency():
    p = multiprocessing.Process(target=run_emergency)
    p.start()

#JSON,CSV関係のモジュール
from RPY_Json_edit import load_line, load_plan, load_worker, load_break,save_plan,save_delay
from RPY_prodcsv import collect_csv_row, export_csv

#計算ロジックのモジュール
from RPY_logic import progress_logic

#設定のファイルパス
BASE_DIR = os.environ.get("BASE_DIR")
if not BASE_DIR:
    raise EnvironmentError("BASE_DIR 環境変数が設定されていません。")

SETTINGS_DIR = os.path.join(BASE_DIR,"設定")
os.makedirs(SETTINGS_DIR, exist_ok=True)

# 計画選択のコード
class SettingsDialog(wx.Dialog):
    def __init__(self, parent, current_settings):
        super().__init__(parent, title="生産計画選択", size=(1200, 600))
        self.settings=current_settings
        self.json_path = os.path.join(SETTINGS_DIR, "line_date.json")
        self.date = load_line(self)
        panel = wx.Panel(self)
        panel.SetBackgroundColour("#2b2b3c")
        vbox = wx.BoxSizer(wx.VERTICAL) 
        
        label_colour = "#CCCCCC"
        ctrl_font = wx.Font(22, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        
        def label(text):
            lbl = wx.StaticText(panel, label=text)
            lbl.SetFont(ctrl_font)
            lbl.SetForegroundColour(label_colour)
            return lbl
        
        # 上部：設定項目一覧表示用
        self.list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.list_ctrl.InsertColumn(0, "開始日", width=150)
        self.list_ctrl.InsertColumn(1, "終了日", width=150)
        self.list_ctrl.InsertColumn(2, "ライン", width=180)
        self.list_ctrl.InsertColumn(3, "品番", width=180)
        self.list_ctrl.InsertColumn(4, "CT", width=50)
        self.list_ctrl.InsertColumn(5, "計画数", width=90)
        self.list_ctrl.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        vbox.Add(self.list_ctrl, 8, wx.EXPAND | wx.ALL, 5)
        
        #保存済みの設定行を復元
        self.origin_plans = current_settings.get("plans", [])
        for plan in current_settings.get("plans", []):
            start=plan.get("start", "")
            end=plan.get("end", "")
            line = plan.get("line", "")
            item = plan.get("item", "")
            ct = plan.get("ct", "")
            plan_num = str(plan.get("plan", ""))            

            index = self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(),start )
            self.list_ctrl.SetItem(index, 1, end)
            self.list_ctrl.SetItem(index, 2, line)
            self.list_ctrl.SetItem(index, 3, item)
            self.list_ctrl.SetItem(index, 4, ct)
            self.list_ctrl.SetItem(index, 5, plan_num)        
        
        #各UIを配置
        self.line_choice = wx.ComboBox(panel, choices=list(self.date.keys()), style=wx.CB_READONLY)
        self.line_choice.SetFont(ctrl_font)
        
        self.dayplan_input = wx.TextCtrl(panel, value="")
        self.dayplan_input.SetFont(ctrl_font)
        self.numkey_btn = wx.Button(panel, label="テンキー")
        
        self.btn_start = wx.Button(panel, label="生産開始")
        self.btn_stop = wx.Button(panel, label="生産終了")

        for btn in [self.btn_start,self.numkey_btn,self.btn_stop]:
            btn.SetFont(ctrl_font)
            
        self.set_button_colors()
         
        #メインでの処理に関係するボタン
        self.btn_start.Bind(wx.EVT_BUTTON, lambda evt: self.EndModal(1001))
        self.btn_stop.Bind(wx.EVT_BUTTON, lambda evt: self.EndModal(1002))
        self.line_choice.Bind(wx.EVT_COMBOBOX, self.on_line_selected)        
        self.numkey_btn.Bind(wx.EVT_BUTTON, self.on_open_pad)  
        
        plan_sizer = wx.BoxSizer(wx.HORIZONTAL)
        plan_sizer.Add(label("ライン選択"), 0, wx.ALL, 1)
        plan_sizer.Add(self.line_choice, 2, wx.RIGHT, 1)
        plan_sizer.Add(label("生産指示数"), 0, wx.ALL, 1)
        plan_sizer.Add(self.dayplan_input, 2, wx.RIGHT, 5)        
        plan_sizer.Add(self.numkey_btn,1, wx.RIGHT, 5)
        
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for btn in [self.btn_start, self.btn_stop]:
            btn_sizer.Add(btn, 1, wx.EXPAND | wx.ALL,1)
        vbox.Add(plan_sizer,1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 0)
        vbox.Add(btn_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 1)
        panel.SetSizer(vbox)
        
    #各種ボタンの配色
    def set_button_colors(self):
        self.numkey_btn.SetBackgroundColour("#8b5cf6")
        self.numkey_btn.SetForegroundColour("#000000")
        
        self.btn_start.SetBackgroundColour("#3b82f6")
        self.btn_start.SetForegroundColour("#000000")
        
        self.btn_stop.SetBackgroundColour("#dc2626")
        self.btn_stop.SetForegroundColour("#000000")
        
    #ここから設定した内容の処理
    def load_date(self):
        self.date=load_line(self)

    #計画の読み込み
    def load_settings(self):
        if not self.line_choice.GetCount():
            return
        line = self.line_choice.GetStringSelection()
        load_plan(self, line)
    
    #選択したラインに合わせた計画の表示
    def filter_plans(self):
        self.list_ctrl.DeleteAllItems()
        for plan in self.settings.get("plans", []):
            start = plan.get("start", "")
            end = plan.get("end", "")
            line = plan.get("line", "")
            item = plan.get("item", "")
            ct = plan.get("ct", "")
            plan_num = str(plan.get("plan", ""))

            index = self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), start)
            self.list_ctrl.SetItem(index, 1, end)
            self.list_ctrl.SetItem(index, 2, line)
            self.list_ctrl.SetItem(index, 3, item)
            self.list_ctrl.SetItem(index, 4, ct)
            self.list_ctrl.SetItem(index, 5, plan_num)
    
    #ライン選択後の計画一覧表示
    def on_line_selected(self, event):
        self.load_settings()
        self.filter_plans()
    
    #選択したの計画の取得 
    def get_selected_plan(self):
        selected = self.list_ctrl.GetFirstSelected()
        if selected == -1:
            return None
        return {
            "start":self.list_ctrl.GetItemText(selected, 0),
            "end": self.list_ctrl.GetItemText(selected,1),
            "line": self.list_ctrl.GetItemText(selected, 2),
            "item": self.list_ctrl.GetItemText(selected, 3),
            "ct": self.list_ctrl.GetItemText(selected, 4),
            "plan": int(self.list_ctrl.GetItemText(selected, 5))
        }
    
    #テンキーを呼び出す
    def on_open_pad(self, event):
        dlg = KeypadDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            self.dayplan_input.SetValue(dlg.value)
        dlg.Destroy()
    
    #入力した生産指示数の取得
    def get_dayplan(self):
        try:
            return int(self.dayplan_input.GetValue())
        except ValueError:
            return 0
    
    #選択した計画の取得    
    def get_settings(self):
        return self.settings
        
#遅れ発生時の記録
class ReasonDialog(wx.Dialog):
    def __init__(self, parent, predefined_reasons):
        super().__init__(parent, title="遅れ理由の選択", size=(900, 675))
        self.selected_reason = None
        self.manual_comment = None

        panel = wx.Panel(self)
        panel.SetBackgroundColour("#1e1e2f")

        # フォントや色の定義
        label_font = wx.Font(17, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        text_font = wx.Font(15, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        btn_font = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        label_colour = "#CCCCCC"

        vbox = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(panel, label="遅れの理由を選択してください:")
        lbl.SetFont(label_font)
        lbl.SetForegroundColour(label_colour)
        vbox.Add(lbl, flag=wx.ALL, border=10)

        self.listbox = wx.ListBox(panel, choices=predefined_reasons, style=wx.LB_SINGLE)
        self.listbox.SetFont(text_font)
        vbox.Add(self.listbox, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        self.comment_label = wx.StaticText(panel, label="その他の場合はコメントを入力してください:")
        self.comment_label.SetFont(label_font)
        self.comment_label.SetForegroundColour(label_colour)
        vbox.Add(self.comment_label, flag=wx.LEFT | wx.TOP, border=10)

        self.comment_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE, size=(-1, 80))
        self.comment_text.SetFont(text_font)
        vbox.Add(self.comment_text, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)

        # ボタン類
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_ok = wx.Button(panel, wx.ID_OK, label="登録")
        btn_cancel = wx.Button(panel, wx.ID_CANCEL, label="キャンセル")

        for btn in [btn_ok, btn_cancel]:
            btn.SetFont(btn_font)
            btn.SetMinSize((120, 40))

        hbox.Add(btn_ok, flag=wx.RIGHT, border=10)
        hbox.Add(btn_cancel)
        vbox.Add(hbox, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)

        panel.SetSizer(vbox)
        self.listbox.Bind(wx.EVT_LISTBOX, self.on_reason_selected)
        self.comment_text.Enable(False)
    
    #遅れの理由の選択時の処理
    def on_reason_selected(self, event):
        sel = self.listbox.GetSelection()
        if sel != wx.NOT_FOUND and self.listbox.GetString(sel) == "その他":
            self.comment_text.Enable(True)
        else:
            self.comment_text.SetValue("")
            self.comment_text.Enable(False)
            
    #データの取得        
    def GetResult(self):
        sel = self.listbox.GetSelection()
        reason = None
        comment = None
        if sel != wx.NOT_FOUND:
            reason = self.listbox.GetString(sel)
            if reason == "その他":
                comment = self.comment_text.GetValue().strip()
                if not comment:
                    comment = "その他"
        else:
            return None, None
        return reason, comment

#作業者入力用の画面
class WorkerSettingsDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="作業者選択", size=(700, 500))
        panel = wx.Panel(self)
        panel.SetBackgroundColour("#2b2b3c")
        self.wjson_path = os.path.join(SETTINGS_DIR, "worker_data.json")
        font = wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        label_colour = "#FFFFFF"

        def label(text):
            lbl = wx.StaticText(panel, label=text)
            lbl.SetFont(font)
            lbl.SetForegroundColour(label_colour)
            return lbl

        self.worker_data_path = os.path.join(SETTINGS_DIR, "worker_data.json")
        self.worker_data = load_worker(self)

        self.worker_name = ""

        # UI構成
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.line_combo = wx.ComboBox(panel, style=wx.CB_READONLY)
        self.line_combo.SetFont(font)
        self.line_combo.Bind(wx.EVT_COMBOBOX, self.on_line_selected)

        self.worker_combo = wx.ComboBox(panel, style=wx.CB_READONLY)
        self.worker_combo.SetFont(font)

        self.shift_combo = wx.ComboBox(panel, choices=["昼勤", "夜勤", "応援"], style=wx.CB_READONLY)
        self.shift_combo.SetFont(font)
        self.shift_combo.SetSelection(0)

        self.worker_btn = wx.Button(panel, label="作業者登録")
        self.btn_close = wx.Button(panel, label="閉じる")

        for btn in [self.worker_btn, self.btn_close]:
            btn.SetFont(font)

        self.set_button_colors()

        main_sizer.Add(label("ライン選択"), 0, wx.ALL, 5)
        main_sizer.Add(self.line_combo, 1, wx.EXPAND | wx.ALL, 5)

        main_sizer.Add(label("作業者選択"), 0, wx.ALL, 5)
        main_sizer.Add(self.worker_combo, 1, wx.EXPAND | wx.ALL, 5)

        main_sizer.Add(label("勤務区分"), 0, wx.ALL, 5)
        main_sizer.Add(self.shift_combo, 1, wx.EXPAND | wx.ALL, 5)

        main_sizer.Add(self.worker_btn, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(self.btn_close, 1, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(main_sizer)

        self.worker_btn.Bind(wx.EVT_BUTTON, self.on_register_worker)
        self.btn_close.Bind(wx.EVT_BUTTON, lambda evt: self.EndModal(wx.ID_OK))

        self.update_line_choices()
    
    #ボタンの色指定
    def set_button_colors(self):
        self.worker_btn.SetBackgroundColour("#007BFF")
        self.btn_close.SetBackgroundColour("#FF1744")
    
    #作業者一覧の読み込み
    def load_worker_data(self):
        self.worker_data = load_worker(self)
    
    #ライン選択時の作業者候補の更新
    def update_line_choices(self):
        self.line_combo.Clear()
        self.line_combo.AppendItems(list(self.worker_data.keys()))
        if self.line_combo.GetCount() > 0:
            self.line_combo.SetSelection(0)
            self.update_worker_choices()
    
    #ライン選択時の作業者一覧更新         
    def on_line_selected(self, event):
        self.update_worker_choices()

    #ラインに合わせた作業者の更新    
    def update_worker_choices(self):
        line = self.line_combo.GetStringSelection()
        workers = self.worker_data.get(line, [])
        self.worker_combo.Clear()
        self.worker_combo.AppendItems(workers)
        if workers:
            self.worker_combo.SetSelection(0)
    
    #作業者の登録処理
    def on_register_worker(self, event):
        name = self.worker_combo.GetValue()
        shift = self.shift_combo.GetValue()
        if not name:
            wx.MessageBox("作業者を選択してください。", "入力エラー", wx.ICON_ERROR)
            return
        self.worker_name = f"{name}({shift})"
        wx.MessageBox(f"{self.worker_name}さん、今日もお仕事頑張ってください!", "開始", wx.OK | wx.ICON_INFORMATION)
        self.EndModal(wx.ID_OK)

#テンキー用クラス
class KeypadDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="テンキー", size=(450, 600))
        panel = wx.Panel(self)
        font = wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        panel.SetBackgroundColour("#2b2b3c")
        
        self.secret_codes = {
            "2999": ("裏コード:999", trigger_emergency),
        }
        
        self.input = wx.TextCtrl(panel, style=wx.TE_RIGHT)
        self.input.SetFont(font)

        grid = wx.GridSizer(4, 3, 5, 5)
        buttons = ["7", "8", "9", "4", "5", "6", "1", "2", "3", "C", "0", "←"]
        for label in buttons:
            btn = wx.Button(panel, label=label)
            btn.SetFont(font)
            btn.Bind(wx.EVT_BUTTON, self.on_key)
            grid.Add(btn, 0, wx.EXPAND)
            btn.SetBackgroundColour("#C0C0C0")
        
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
        
    #各キーの処理    
    def on_key(self, event):
        label = event.GetEventObject().GetLabel()
        current = self.input.GetValue()
        if label == "C":
            self.input.SetValue("")
        elif label == "←":
            self.input.SetValue(current[:-1])
        else:
            self.input.SetValue(current + label)
    
    #決定押した際の処理
    def on_ok(self, event):
        self.value = self.input.GetValue()

        if self.value in self.secret_codes:
            message, function = self.secret_codes[self.value]
            print(message)
            self.value = ""
            self.EndModal(wx.ID_OK)
            wx.CallAfter(function)
        else:
            self.EndModal(wx.ID_OK)
            
#詳細な生産状況
class StatisticsDialog(wx.Dialog):
    def __init__(self, parent, production, defects, planday_num, plan_num, elapsed_seconds, cycle_time):
        super().__init__(parent, title="詳細情報", size=(600, 500))
        panel = wx.Panel(self)
        panel.SetBackgroundColour("#1e1e2f")
        
        font = wx.Font(30, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        
        try:
            ct = int(cycle_time)
        except (ValueError, TypeError):
            ct = 1
        
        total = production - defects
        defep = (defects/production)*100 if production > 0 else 0
        elapsed = (elapsed_seconds/3600)
        target = int(elapsed_seconds / (ct or 1))
        target = min(target, planday_num)
        target2 = int(elapsed_seconds / (ct or 1))
        achievement = (total / planday_num) * 100 if planday_num > 0 else 0
        utilization = (total / target2) * 100 if target2 > 0 else 0

        stats = [
            ("計画数", f"{plan_num}個","#CCCCCC"),
            ("進捗数", f"{target}個","#CCCCCC"),
            ("不良数", f"{defects}個","#FF8C00"),
            ("不良率", f"{defep:.2f}%","#FF6347"),
            ("達成率", f"{achievement:.2f}%","#32CD32"),
            ("可動率", f"{utilization:.2f}%", "#1E90FF"),
            ("作業時間", f"{elapsed:.2f}時間","#CCCCCC"),
        ]

        sizer = wx.BoxSizer(wx.VERTICAL)
        for label, value,color in stats:
            row = wx.BoxSizer(wx.HORIZONTAL)
            l = wx.StaticText(panel, label=label)
            l.SetFont(font)
            l.SetForegroundColour(color)
            v = wx.StaticText(panel, label=value)
            v.SetFont(font)
            v.SetForegroundColour("#CCCCCC")
            row.Add(l, 1, wx.ALL, 5)
            row.Add(v, 1, wx.ALL, 5)
            sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        panel.SetSizer(sizer)

# ここからメイン画面のコード        
class ProductionEfficiencyApp(wx.Frame):   
    def __init__(self, parent, title):
        display_width, display_height = wx.GetDisplaySize()
        
        max_width = int(display_width * 0.9)
        max_height = int(display_height * 0.9)    
        
        super().__init__(parent, title=title, size=(max_width, max_height))
        self.panel = wx.Panel(self)
        self.SetBackgroundColour("#000000")         
        self.panel.SetBackgroundColour("#000000")
    
        self.Bind(wx.EVT_SIZE, self.on_size)
        
        #メインでの表示に使う関数
        #タイマーと各種初期設定
        self.timer_interval = 1000
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_timer, self.timer)
        self.timer.Start(self.timer_interval)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        #生産状態の管理フラグ
        self.production_running = False
        self.production_paused = False
        self.abnormal_pause = False
        #各種数値の初期設定
        self.total_production = 0
        self.total_defproduction = 0
        self.progress = 0
        self.diff = 0
        self.total = 0
        self.plan_num = 0
        self.planday_num = 0
        #各種時間管理の初期設定
        self.total_min = 0
        self.elapsed_seconds = 0
        self.api_timer = 0
        self.cycle_time = 1
        self.remaining=0
        self.rct=1
        self.worktime=1
        #各種データリストの初期化
        self.production_log = []
        self.break_schedules = []
        self.csv_rows = []
        self.log_rows = []
        #各種基本情報の初期化
        self.start_day_str = ""
        self.end_day_str = ""
        self.status_str = ""
        self.worker_name = ""
        self.selected_line = None
        self.selected_item = None
        #CSV収集用の初期設定
        self.production_start_time = None
        self.production_started = False
        self.collect_start_time = None
        self.last_csv_collect_time = None
        #設定ファイルの読み込み
        self.load_break_schedules()
        self.settings = {}
        self.selected_plan = {}
        self.entry = {}
        
        self.build_ui()
        self.apply_setting(self.selected_plan)
        self.Centre()
        self.Show()
        self.setup_gpio()

    #ウィンドサイズ変更時の処理    
    def on_size(self, event):
        self.Layout()
        self.Refresh()
        event.Skip() 
    
    def setup_gpio(self):
        self.production_button=Button(17,pull_up=False,bounce_time=0.005)
        self.production_button.when_pressed=self.on_gpio_signal
     
    def on_gpio_signal(self):
        wx.CallAfter(self.on_add_production)
           
    #各種表示画面の作成
    def build_ui(self):
        now = datetime.datetime.now()
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # ステータス画面（左側）
        status_panel = wx.Panel(self.panel)
        status_sizer = wx.BoxSizer(wx.VERTICAL)
        
        #各種フォントの定義
        font = wx.Font(178, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD,False,"Arial")
       
        other_font = wx.Font(35, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        front_font = wx.Font(25, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        
        title_font = wx.Font(60,wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD,False,"Arial")
        ltitle_font = wx.Font(39,wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD,False,"Arial")
        
        unit_font = wx.Font(15,wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD,False,"Arial")
        
        status_panel.SetBackgroundColour("#1e1e2f")

        def make_label(text):
            lbl = wx.StaticText(status_panel, label=text)
            lbl.SetFont(font)
            lbl.SetForegroundColour("#CCCCCC")
            return lbl
        
        def add_row_gbs(parent,title_text, value_text,unit_text, title_font, value_font, unit_font):
            
            title = wx.StaticText(parent, label=title_text)
            value = wx.StaticText(parent, label=value_text,style=wx.ALIGN_RIGHT)
            unit = wx.StaticText(parent, label=unit_text)
            
            title.SetFont(title_font)
            value.SetFont(value_font)
            unit.SetFont(unit_font)
            
            title.SetForegroundColour("#CCCCCC")
            value.SetForegroundColour("#CCCCCC")
            unit.SetForegroundColour("#CCCCCC")

            return title,value,unit  
       
        # 各種表示の内容
        #最上部の表示
        info_sizer = wx.BoxSizer(wx.HORIZONTAL)
        status_sizer.Add(info_sizer, 0,wx.ALIGN_LEFT | wx.BOTTOM , 1)
        self.selection_label = make_label("品番名：未設定")
        info_sizer.Add(self.selection_label, 4, wx.RIGHT,20)
        self.ct_display_label = make_label("CT：0秒")
        info_sizer.Add(self.ct_display_label, 2,wx.LEFT ,10)
        self.worker_label = make_label("作業者：未登録")
        info_sizer.Add(self.worker_label, 2, wx.LEFT,20)
        
        for front in [
            self.selection_label,self.worker_label,self.ct_display_label,
        ]:
            front.SetFont(front_font)
        
        #時間と状態の表示
        con_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.prod_status_label = make_label("生産状態：停止中")
        con_sizer.Add(self.prod_status_label, 3, wx.ALL | wx.ALIGN_LEFT, 3)
        self.time_label = make_label(f"現在時刻:{now.strftime('%H:%M:%S')}")
        con_sizer.Add(self.time_label, 3, wx.ALL | wx.ALIGN_LEFT, 3)
        for others in [self.time_label,self.prod_status_label,]:
            others.SetFont(other_font)
        status_sizer.Add(con_sizer, 0, wx.ALL | wx.EXPAND , 1)
        
        grid_sizer = wx.GridBagSizer(hgap=5, vgap=5)
        
        # 左4行
        left_items = [
            ("    指示数：", "0", "個", "planday"),
            ("    実績数：", "0", "個", "total"),
            ("    実績差：", "0", "個", "diff"),
            ("    予定終了時刻：",f"{now.strftime('%H:%M')}","","ltime"),
        ]
        
        for row_idx, (left) in enumerate(left_items):
            #左側
            if left[0]:
                ltitle, lvalue, lunit = add_row_gbs(status_panel,left[0], left[1], left[2], title_font, font, unit_font)
                setattr(self, f"{left[3]}_title", ltitle)
                setattr(self, f"{left[3]}_value", lvalue)
                setattr(self, f"{left[3]}_unit", lunit)
                
                grid_sizer.Add(ltitle, pos=(row_idx, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=70)
                grid_sizer.Add(lvalue, pos=(row_idx, 1), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
                grid_sizer.Add(lunit,  pos=(row_idx, 2), flag=wx.ALIGN_CENTER_VERTICAL)

                self.planday_title.SetForegroundColour("#2196F3") if left[3] == "planday" else None
                self.total_title.SetForegroundColour("#00FFCC") if left[3] == "total" else None
                self.ltime_title.SetForegroundColour("#c084fc") if left[3] == "ltime" else None
                
                self.ltime_title.SetFont(ltitle_font) if left[3] == "ltime" else None
                self.ltime_value.SetFont(title_font) if left[3] == "ltime" else None           
                
        status_sizer.Add(grid_sizer, 0, wx.EXPAND | wx.ALL, 0)
        
        # 各valueラベルの幅調整（任意）
        for value_label in [
            self.planday_value,self.total_value,self.diff_value
        ]:
            if value_label is not None:
                value_label.SetMinSize(wx.Size(450, -1))  # 適宜調整可能
        
        status_panel.SetSizer(status_sizer)
        main_sizer.Add(status_panel, 7, wx.EXPAND | wx.ALL, 0)

        # 入力画面（右側）
        input_panel = wx.Panel(self.panel)
        input_sizer = wx.BoxSizer(wx.VERTICAL)
        dp_sizer = wx.BoxSizer(wx.HORIZONTAL)
        input_font = wx.Font(25, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        input_panel.SetBackgroundColour("#160B3BC5")
        
        def label(text):
            inp = wx.StaticText(input_panel, label=text)
            inp.SetFont(input_font)
            inp.SetForegroundColour("#FFFFFF")
            return inp
        
        self.defep_input = wx.TextCtrl(input_panel, style=wx.TE_RIGHT)
        self.defep_input.SetFont(input_font)
        self.keypad_open_btn = wx.Button(input_panel, label="テンキー")
        self.defep_btn = wx.Button(input_panel, label="不良数追加")
        
        self.abnormal_stop_btn = wx.Button(input_panel, label="一時停止")
        self.abnormal_resume_btn = wx.Button(input_panel, label="稼働再開")
        
        self.btn_stats = wx.Button(input_panel, label="詳細表示")
        self.btn_open_setting = wx.Button(input_panel, label="設定",)
        
        buttons = [self.keypad_open_btn,self.defep_btn,self.btn_open_setting,self.abnormal_stop_btn,self.btn_stats,self.abnormal_resume_btn]
        
        self.set_button_colors()
        
        for btn in buttons:
            btn.SetFont(input_font)

        #入力画面の管理
        input_sizer.Add(label("不良数入力"), 0, wx.ALL, 1)
        dp_sizer.Add(self.defep_input, 4, wx.EXPAND | wx.ALL, 1)
        dp_sizer.Add(self.keypad_open_btn, 2, wx.EXPAND | wx.ALL, 1)
        input_sizer.Add(dp_sizer, 0, wx.EXPAND | wx.ALL, 1)
        input_sizer.Add(self.defep_btn, 1, wx.EXPAND | wx.ALL, 1)
        input_sizer.Add(self.abnormal_stop_btn, 2, wx.EXPAND | wx.ALL, 1)
        input_sizer.Add(self.abnormal_resume_btn, 2, wx.EXPAND | wx.ALL, 1)
        input_sizer.Add(self.btn_stats, 1, wx.EXPAND | wx.ALL, 1)
        input_sizer.Add(self.btn_open_setting, 1, wx.EXPAND | wx.ALL, 1)

        input_panel.SetSizer(input_sizer)
        main_sizer.Add(input_panel,3, wx.EXPAND | wx.ALL, 0)

        self.panel.SetSizer(main_sizer)

        # 各種ボタンの動作固定
        self.keypad_open_btn.Bind(wx.EVT_BUTTON, self.on_open_keypad)
        self.defep_btn.Bind(wx.EVT_BUTTON, self.on_add_defproduction)
        self.btn_open_setting.Bind(wx.EVT_BUTTON, self.on_open_settings)
        self.abnormal_stop_btn.Bind(wx.EVT_BUTTON, self.on_abnormal_pause)
        self.abnormal_resume_btn.Bind(wx.EVT_BUTTON, self.on_abnormal_resume)
        self.btn_stats.Bind(wx.EVT_BUTTON, self.on_show_statistics)
        
    # ボタンの色を設定
    def set_button_colors(self):
        self.keypad_open_btn.SetBackgroundColour("#4b0ae2eb") 
        self.keypad_open_btn.SetForegroundColour("#EDEDED")
        
        self.defep_btn.SetBackgroundColour("#FA8805F4") 
        self.defep_btn.SetForegroundColour("#EDEDED")
        
        self.abnormal_stop_btn.SetBackgroundColour("#D61958EB")  
        self.abnormal_stop_btn.SetForegroundColour("#EDEDED")
        
        self.abnormal_resume_btn.SetBackgroundColour("#07D14AED")
        self.abnormal_resume_btn.SetForegroundColour("#EDEDED")
        
        self.btn_stats.SetBackgroundColour("#1DC4B6ED")
        self.btn_stats.SetForegroundColour("#EDEDED")
        
        self.btn_open_setting.SetBackgroundColour("#1869D3F6")  
        self.btn_open_setting.SetForegroundColour("#EDEDED")
    
    #============ここからメインの各種処理=============
    
    #テンキーの呼び出し
    def on_open_keypad(self, event):
        dlg = KeypadDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            self.defep_input.SetValue(dlg.value)
        dlg.Destroy()
    
    #ライン設定の保存
    def save_settings(self):
        line = self.selected_line
        save_plan(self,line)

    #休憩設定の読み込み
    def load_break_schedules(self):
        load_break(self)
    
    #作業者の登録    
    def on_open_worker_settings(self, event = None):
        dlg = WorkerSettingsDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            if dlg.worker_name:
                self.worker_name = dlg.worker_name
            self.update_status_labels()
        dlg.Destroy()
    
    #生産数追加の処理
    def on_add_production(self):
        if not self.production_running or self.abnormal_pause:
            wx.MessageBox("生産稼働中でないか一時停止中のため追加できません。", "警告", wx.ICON_WARNING)
            return
        
        val = 1
        self.total_production += val
        
        self.update_status_labels()
        
    #不良数追加の処理    
    def on_add_defproduction(self, event):
        if not self.production_running or self.abnormal_pause:
            wx.MessageBox("生産稼働中でないか一時停止中のため追加できません。", "警告", wx.ICON_WARNING)
            return

        try:
            defval = int(self.defep_input.GetValue())
            if defval < 1:
                raise ValueError
        except ValueError:
            wx.MessageBox("正の整数を入力してください。", "入力エラー", wx.ICON_ERROR)
            return        
        self.total_defproduction += defval
        self.defep_input.SetValue("")
            
        self.update_status_labels()    
    
    #非稼働時間の合計取得
    def break_min(self,start = False):
        if not start:
            return 0
        
        now = datetime.datetime.now()
        today = now.weekday()
        tomorrow = (today + 1) % 7
        total_min = 0
        
        ct = int(self.cycle_time)
        ctr = ct*1.25   
        worktime=(self.remaining*ctr)/3600
        time_end = now + datetime.timedelta(hours=worktime)
        
        target_days = {today, tomorrow}
        for brk in self.break_schedules:
            try:
                brk_weekday = brk["weekday"]
                if brk_weekday not in target_days:
                    continue

                start_h, start_m = map(int, brk["start_time"].split(":"))
                duration = brk["duration_min"]

                # 日付補正
                day_offset = (brk_weekday - today) % 7
                brk_date = now.date() + datetime.timedelta(days=day_offset)
                start_dt = datetime.datetime.combine(brk_date, datetime.time(start_h, start_m))

                if now <= start_dt <= time_end:
                    total_min += duration

            except Exception as e:
                print(f"休憩抽出エラー: {e}")
                continue

        return total_min
    
    #生産開始の関数
    def start_production(self):
        #状態管理用のフラグ
        self.production_running = True
        self.production_paused = False
        self.abnormal_pause = False
        self.production_started = True
        #処理や各種表示用の初期値
        self.total_min = self.break_min(start=True)
        self.elapsed_seconds = 0
        self.total_production = 0
        self.total_defproduction = 0
        self.production_start_time = datetime.datetime.now()
        self.last_csv_collect_time = self.production_start_time
        
    #生産終了の関数    
    def end_production(self):
        #状態管理や出力用のフラグ
        collect_csv_row(self)
        export_csv(self)
        finish_log(self)
        self.production_running = False
        self.production_paused = False
        self.abnormal_pause = False
        self.production_started = False
        #各種処理用の数値の初期化
        #時間やタイマー関係の変数
        self.elapsed_seconds = 0
        self.total_min = 0
        self.api_timer = 0
        self.worktime=1
        self.production_start_time = None
        self.last_csv_export_time = None
        self.collect_start_time = None
        self.last_csv_collect_time = None
        #生産数関係の変数
        self.total_production = 0
        self.total_defproduction = 0
        self.progress = 0
        self.total = 0
        self.diff = 0
        #各種基本情報の初期化
        self.start_day_str = ""
        self.end_day_str = ""
        self.worker_name = ""
        self.selected_line = None
        self.selected_item = None
        self.cycle_time = 1
        self.plan_num = 0
        self.planday_num = 0
        self.csv_rows.clear()
        self.log_rows.clear()
        
    #設定の取得    
    def apply_setting(self, selected_plan):
        if not selected_plan:
            return False
        
        plan = selected_plan
        self.start_day_str = plan.get("start", "")
        self.end_day_str = plan.get("end", "")
        self.selected_line = plan.get("line", "")
        self.selected_item = plan.get("item", "")
        self.cycle_time = int(plan.get("ct", ""))
        self.plan_num = int(plan.get("plan", 0))
        return True
    
    #ライン設定の反映        
    def on_open_settings(self, event):
        dlg = SettingsDialog(self, self.settings)
        ret_code = dlg.ShowModal()

        if ret_code == 1001:  # 生産開始
            
            if self.production_running:
                wx.MessageBox("すでに生産が開始されています。終了してから再度実行してください。", "生産中", wx.ICON_WARNING)
                return
        
            selected_plan = dlg.get_selected_plan()
            if not selected_plan:
                wx.MessageBox("計画を選択して下さい", "警告", wx.ICON_WARNING)
                return
            
            planday_num=dlg.get_dayplan()
            
            if planday_num <= 0:
                wx.MessageBox("生産指示数を入力してください", "入力漏れ", wx.ICON_WARNING)
                return
            
            self.settings = dlg.get_settings()
            self.load_break_schedules()
            self.apply_setting(selected_plan)
            self.planday_num = planday_num
            self.on_open_worker_settings()
            self.start_production()
            
        elif ret_code == 1002:  # 生産終了
            if not self.production_running:
                wx.MessageBox("生産が開始されていません。", "生産未開始", wx.ICON_WARNING)
                return
            
            #ラインが選択されていない(生産が開始されていない場合)は処理しない
            if not self.selected_line:
                return
            line = self.selected_line
            load_plan(self, line)

            self.total = self.total_production - self.total_defproduction
            rest = self.planday_num - self.total
            ctl = int(self.cycle_time)
            prtime = self.planday_num * ctl

            is_delayed = self.elapsed_seconds > prtime or rest > 0

            if is_delayed:
                predefined_reasons = [
                    "機械トラブル", "異常による不良の発生", "段取り","刃具交換",
                    "材料不足", "体調不良", "遅れの挽回", "残業前提での指示数","その他"
                ]
                dlg = ReasonDialog(self, predefined_reasons)
                res = dlg.ShowModal()
                reason, comment = dlg.GetResult()
                dlg.Destroy()

                if res != wx.ID_OK or not reason:
                    return  # キャンセルや入力なしは終了しない

                delaym = max(0, (self.elapsed_seconds - prtime) // 60)

                # 保存データの作成
                self.entry = {
                    "日時": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "作業者": self.worker_name,
                    "品番": self.selected_item,
                    "指示数": self.planday_num,
                    "生産数": self.total,
                    "差": rest,
                    "遅延分": delaym,
                    "遅延理由": reason,
                    "コメント": comment or ""
                }
                save_delay(self)

            finish_status(self)    
            self.end_production()  
                
        dlg.Destroy()
        self.update_status_labels()
        self.status_string()
    
    #詳細設定表示
    def on_show_statistics(self, event):
        dlg = StatisticsDialog(
            self,
            production=self.total_production,
            defects=self.total_defproduction,
            plan_num = self.plan_num,
            planday_num=self.planday_num,
            elapsed_seconds=self.elapsed_seconds,
            cycle_time=self.cycle_time or 1
        )
        dlg.ShowModal()
        dlg.Destroy()
        
    #緊急停止の処理    
    def on_abnormal_pause(self, event):
        if self.production_running and not self.abnormal_pause:
            self.abnormal_pause = True
            self.production_paused = True
            wx.MessageBox("生産を一時停止しました。", "一時停止", wx.ICON_WARNING)
            self.status_string()

    #稼働再開の処理        
    def on_abnormal_resume(self, event):
        if self.production_running and self.abnormal_pause:
            self.abnormal_pause = False
            self.production_paused = False
            wx.MessageBox("生産を再開しました。", "稼働再開", wx.ICON_INFORMATION)
            self.status_string()
            
    #非稼働時間の確認        
    def check_break_time(self):
        now = datetime.datetime.now()
        weekday = now.weekday()

        for brk in self.break_schedules:
            try:
                # 休憩開始曜日
                brk_weekday = brk["weekday"]
                start_h, start_m = map(int, brk["start_time"].split(":"))
                duration = brk["duration_min"]

                # 開始日時（曜日ベースで正確な日付に調整）
                days_diff = (brk_weekday - weekday) % 7
                brk_date = now.date() + datetime.timedelta(days=days_diff)
                start_dt = datetime.datetime.combine(brk_date, datetime.time(start_h, start_m))

                # 終了日時（duration を分単位で加算）
                end_dt = start_dt + datetime.timedelta(minutes=duration)

                # 現在時刻が開始〜終了の範囲に含まれるか
                if start_dt <= now < end_dt:
                    return True
            except Exception as e:
                print(f"稼働外時間チェック中のエラー: {e}")
                continue

        return False
    
    #時間の処理    
    def update_timer(self, event):
        now = datetime.datetime.now()
        self.time_label.SetLabel(f"現在時刻:{now.strftime('%H:%M:%S')}")
        self.now = now
        progress_logic(self)

        #稼働開始後の加算処理
        if self.production_running and not self.production_paused and not self.abnormal_pause:
            self.elapsed_seconds += 1

        #APIの定期呼び出し
        if self.production_running:
            self.api_timer += 1
            #リアルタイムダッシュボード用
            if self.api_timer % 5 == 0:  # 5秒ごと
                try:
                    send_status(self)
                except Exception as e:
                    print(f"API送信エラー: {e}")    
            
            #時系列データ用API呼び出し
            if self.api_timer % 1200 == 0: #20分ごと
                product_log(self)
                try:
                    send_log(self)
                except Exception as e:
                    print(f"logAPI送信エラー:{e}")           

        #稼働外時間の処理
        if self.check_break_time():
            self.production_paused = True
            self.status_string()
        else:
           if self.production_paused:
               self.total_min = self.break_min(start=True)
               self.production_paused = False
               self.status_string()             

        # 1時間ごとのCSV収集
        if self.production_running and self.production_started:
            if (now - self.last_csv_collect_time).total_seconds() >= 3600:
                collect_csv_row(self)
                self.last_csv_collect_time = now
        
        self.update_status_labels()
        

    #表示画面の更新処理    
    def update_status_labels(self):
        now = datetime.datetime.now()
        self.worker_label.SetLabel(f"作業者：{self.worker_name if self.worker_name else '未登録'}")
        
        #計画選択後のセット
        if self.selected_line and self.selected_item:
            self.selection_label.SetLabel(f"品番名：{self.selected_item}")
            self.ct_display_label.SetLabel(f"CT：{self.cycle_time}秒")       
        else:
            self.selection_label.SetLabel("品番名：未設定")
            self.ct_display_label.SetLabel("CT：0秒")

        self.planday_value.SetLabel(f"{self.planday_num}")
        
        #計画がセットされ生産が始まったら    
        if self.production_running and self.selected_item:
            #残りの予想作業時間
            time_end = now + datetime.timedelta(hours=self.worktime) + datetime.timedelta(minutes=self.total_min)
            last_str = time_end.strftime("%H:%M")
            self.ltime_value.SetLabel(f"{last_str}")            

            self.diff_value.SetLabel(f"{self.diff}")
            
            if  self.total < self.progress:
                self.diff_value.SetForegroundColour("#B22222")
            else:
                self.diff_value.SetForegroundColour("#CCCCCC")
            self.diff_value.Refresh()
                
        else:
            self.diff_value.SetLabel("0")
            self.diff_value.SetForegroundColour("#CCCCCC")
            self.ltime_value.SetLabel(f"{now.strftime('%H:%M')}")
        self.diff_value.Refresh()    
        self.total_value.SetLabel(f"{self.total}")
        
    #生産状態の表記
    def status_string(self):    
        if self.production_running:
            if self.abnormal_pause:
                status_str = "異常停止中"
                self.prod_status_label.SetForegroundColour("#F44336")
            elif self.production_paused:
                status_str = "一時停止中"
                self.prod_status_label.SetForegroundColour("#FFFACD")
            else:
                status_str = "稼働中"
                self.prod_status_label.SetForegroundColour("#00FF00")
        else:
            status_str = "停止中"
            self.prod_status_label.SetForegroundColour("#F1F1F1")

        self.status_str = status_str    
        self.prod_status_label.SetLabel(f"生産状態：{status_str}")

    #GPIOを安全に終わる為の処理
    def OnClose(self, event):
        try:
            self.production_button.close()
        except Exception as e:
            print("GPIO cleanup error:", e)
        self.Destroy()
        
if __name__ == "__main__":
    app = wx.App(False)
    frame=ProductionEfficiencyApp(None, "生産モニター")
    frame.Show()
    app.MainLoop()
