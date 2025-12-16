import requests

SERVER_URL = "http://192.168.11.109:8000/monitor/status"
LOG_URL = "http://192.168.11.150:8100/log"
CLEAR_URL = "http://192.168.11.150:8100/log/line/clear"

#時間ごとのグラフ用のディクト生成
def product_log(self):
    self.planday_num = self.planday_num if self.planday_num > 0 else 1
    total = self.total_production - self.total_defproduction
    ct = int(self.cycle_time) if int(self.cycle_time) > 0 else 1 
    #ctl = ct*1.25    
    target_progress =int(self.elapsed_seconds/ct)
    target =int(self.elapsed_seconds/ct)
    target_progress = min(target_progress, self.planday_num)
    utilization = (total / target) * 100 if target > 0 else 0.0
    
    row = [
        self.now.strftime("%Y-%m-%d %H:%M:%S"),
        self.worker_name or "未登録",
        self.selected_line or "no_line",
        self.selected_item or "no_item",
        round(utilization, 2),
    ]
    self.log_rows = row
#時間毎のデータをAPIに送信
def send_log(self):
    try:
        res = requests.post(LOG_URL,json=self.log_rows,timeout=2)
        res.raise_for_status()
    except Exception as e:
        print("送信失敗",e)    

#時間毎データの終了用
def finish_log(self):
    try:
        data = {"line": self.selected_line}
        requests.post(CLEAR_URL, json=data, timeout=2)
    except Exception as e:
        print("送信失敗:", e)

#生産中のAPI
def send_status(self):

    total = int(self.total_value.GetLabel()) if self.total_value.GetLabel() else 0
    diff = int(self.diff_value.GetLabel()) if self.diff_value.GetLabel() else 0
    target = total-diff
    achievement = (total/self.planday_num)*100 if self.planday_num > 0 else 0
    utiliz = (total/self.progress)*100 if self.progress > 0 else 0

    try:
        data = {"line":self.selected_line if self.selected_line else "未選択",
                "item":self.selected_item if self.selected_item else "未選択",
                "worker":self.worker_name if self.worker_name else "未登録",
                "plan":self.planday_num if self.planday_num else 0,
                "count":total,
                "diff":diff,
                "target":target if target > 0 else 0,
                "achievement":round(achievement,2),
                "utilization":round(utiliz ,2),
                "status":self.status_str if self.status_str else "停止中"
        }
        requests.post(SERVER_URL, json=data, timeout=2)
    except Exception as e:
        print("送信失敗:", e)

#生産終了時のAPI
def finish_status(self):

    try:
        data = {"line":self.selected_line if self.selected_line else "未選択",
                "item":"未選択",
                "worker":"未登録",
                "plan":0,
                "count":0,
                "diff":0,
                "target":0,
                "achievement":0,
                "utilization":0,
                "status":"停止中"
        }
        requests.post(SERVER_URL, json=data, timeout=2)
    except Exception as e:
        print("送信失敗:", e)