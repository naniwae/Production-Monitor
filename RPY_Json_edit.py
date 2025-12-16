import json
import os
from filelock import FileLock
import wx
import datetime

#環境変数に登録されているパスを読み込み
BASE_DIR = os.environ.get("BASE_DIR")
if not BASE_DIR:
    raise EnvironmentError("BASE_DIR 環境変数が設定されていません。")

#設定フォルダの作成
SETTINGS_DIR = os.path.join(BASE_DIR, "設定")
os.makedirs(SETTINGS_DIR, exist_ok=True)

# === 共通関数 ===

#読み取り時のロック
def read_json_locked(path, encoding="utf-8", default=None):
    lock_path = path + ".lock"
    try:
        with FileLock(lock_path, timeout=5):
            if os.path.exists(path):
                with open(path, "r", encoding=encoding) as f:
                    return json.load(f)
    except Exception as e:
        wx.LogError(f"読み込み失敗: {e}")
    return default

#書き込み時のロック
def write_json_locked(path, data, encoding="utf-8", show_message=False):
    lock_path = path + ".lock"
    try:
        with FileLock(lock_path, timeout=5):
            with open(path, "w", encoding=encoding) as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        if show_message:
            wx.MessageBox("保存しました。", "完了", wx.OK | wx.ICON_INFORMATION)
    except Exception as e:
        wx.MessageBox(f"保存エラー: {e}", "エラー", wx.OK | wx.ICON_ERROR)

# === 各設定の読み込み関数 ===

def load_line(self):
    return read_json_locked(self.json_path, default={})

def load_plan(self, line):
    path = os.path.join(SETTINGS_DIR, line, "settings.json")
    self.settings = read_json_locked(path, encoding="utf-8-sig", default={})

def load_worker(self):
    return read_json_locked(self.wjson_path, default={})

def load_break(self):
    path = os.path.join(SETTINGS_DIR, "break_schedule.json")
    self.break_schedules = read_json_locked(path, encoding="utf-8-sig", default=[])

def load_ct1(self):
    dir_path = os.path.join(BASE_DIR,"サイクルタイム")
    os.makedirs(dir_path, exist_ok=True)
    path = os.path.join(dir_path, "cycletime1.json")
    self.another_ct = read_json_locked(path, encoding="utf-8-sig", default={})

def load_ct2(self):
    dir_path = os.path.join(BASE_DIR,"サイクルタイム")
    os.makedirs(dir_path, exist_ok=True)
    path = os.path.join(dir_path, "cycletime2.json")
    self.another_ct = read_json_locked(path, encoding="utf-8-sig", default={})

# === 各設定の保存関数 ===

def save_line(self, show_message=False):
    json_path = os.path.join(SETTINGS_DIR, "line_date.json")
    write_json_locked(json_path, self.date, show_message=show_message)

def save_plan(self, line):
    dir_path = os.path.join(SETTINGS_DIR, line)
    os.makedirs(dir_path, exist_ok=True)
    path = os.path.join(dir_path, "settings.json")
    write_json_locked(path, self.settings, encoding="utf-8-sig")

def save_worker(self, show_message=False):
    json_path = os.path.join(SETTINGS_DIR, "worker_data.json")
    write_json_locked(json_path, self.data, show_message=show_message)

def save_break(self):
    path = os.path.join(SETTINGS_DIR, "break_schedule.json")
    write_json_locked(path, self.break_schedules, encoding="utf-8-sig")

def save_cycletime1(self):
    dir_path = os.path.join(BASE_DIR,"サイクルタイム")
    os.makedirs(dir_path, exist_ok=True)
    path = os.path.join(dir_path, "cycletime1.json")
    ct_date = { "line": self.selected_line if self.selected_line else "未選択",
             "item": self.selected_item if self.selected_item else "未選択",
             "ct": self.cycle_time if self.cycle_time else 0,} 
    write_json_locked(path, ct_date, encoding="utf-8-sig")

def save_cycletime2(self):
    dir_path = os.path.join(BASE_DIR,"サイクルタイム")
    os.makedirs(dir_path, exist_ok=True)
    path = os.path.join(dir_path, "cycletime2.json")
    ct_date = { "line": self.selected_line if self.selected_line else "未選択",
             "item": self.selected_item if self.selected_item else "未選択",
             "ct": self.cycle_time if self.cycle_time else 0,} 
    write_json_locked(path, ct_date, encoding="utf-8-sig")

def save_delay(self):
        line = self.selected_line if self.selected_line else "no_line"
        item = self.selected_item if self.selected_item else "no_item"
        #フォルダの検索
        folder_path = os.path.join(BASE_DIR,"生産記録",line, item)
        os.makedirs(folder_path, exist_ok=True)

        #ファイル生成
        try:
            start_dt = datetime.datetime.strptime(self.start_day_str, "%Y-%m-%d")
            end_dt = datetime.datetime.strptime(self.end_day_str, "%Y-%m-%d")
        except ValueError as e:
            print(f"[日付エラー] 開始:{self.start_day_str} / 終了:{self.end_day_str} → {e}")
            return

        file_name = f"遅れ発生理由_{start_dt.strftime('%Y-%m-%d')}_{end_dt.strftime('%Y-%m-%d')}.json"
        file_path = os.path.join(folder_path, file_name)

        # ファイル読み込み・追記・保存
        data = []
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"読み込みエラー: {e}")

        data.append(self.entry)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return file_path   
        except Exception as e:
            print(f"保存エラー: {e}")
            return None