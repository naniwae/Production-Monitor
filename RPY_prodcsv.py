import csv
import os
import datetime
BASE_DIR = os.environ.get("BASE_DIR")

#csv関連の処理
def collect_csv_row(self):
    self.planday_num = self.planday_num if self.planday_num > 0 else 1
    total = self.total_production - self.total_defproduction
    ct = int(self.cycle_time) if int(self.cycle_time) > 0 else 1 
    #ctl = ct*1.25    
    target_progress =int(self.elapsed_seconds/ct)
    target =int(self.elapsed_seconds/ct)
    target_progress = min(target_progress, self.planday_num)
    diff = total - target_progress
    rate = (total / self.planday_num) * 100
    utilization = (total / target) * 100 if target > 0 else 0.0
        
    row = [
        self.now.strftime("%Y-%m-%d %H:%M:%S"),
        self.worker_name or "未登録",
        self.selected_line or "no_line",
        self.selected_item or "no_item",
        self.planday_num, 
        total,
        target_progress,
        self.total_defproduction,
        diff,
        round(rate, 2),
        round(utilization, 2),
    ]
    
    self.csv_rows.append(row)
        
#データのファイルへの出力
def export_csv(self):
    if not self.csv_rows:
        return

    now = datetime.datetime.now()
    self.last_csv_export_time = now

    line = self.selected_line if self.selected_line else "no_line"
    item = self.selected_item if self.selected_item else "no_item"
    
    start_day_dt = datetime.datetime.strptime(self.start_day_str, "%Y-%m-%d")
    start_str = start_day_dt.strftime("%Y-%m-%d")
    end_day_dt = datetime.datetime.strptime(self.end_day_str, "%Y-%m-%d")
    end_str = end_day_dt.strftime("%Y-%m-%d")
    
    folder = os.path.join(BASE_DIR,"生産記録",line,item)
    os.makedirs(folder, exist_ok=True)
        
    file_path = os.path.join(folder, f"期間_{start_str}_{end_str}.csv")

    file_exists = os.path.exists(file_path)
        
    # 累積生産数読み込み
    cumulative = 0
    if file_exists:
        with open(file_path, encoding="utf-8-sig") as f:
            lines = f.readlines()
        for line in reversed(lines):
            if "累積実績数" in line:
                try:
                    cumulative = int(line.strip().split(",")[1])
                except:
                    cumulative = 0
                break

    # 今回分の実績数を加算
    latest_row = self.csv_rows[-1] if self.csv_rows else None
    session_total = int(latest_row[5]) if latest_row else 0
    cumulative += session_total

    with open(file_path, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        if not file_exists:
            # 新規ファイルならヘッダー
            writer.writerow([
                "日時","作業者","ライン","品番",
                "指示数","実績数","進捗数","不良数","差","達成率(%)","可動率(%)"
            ])
        else:
            # 追記時は空行挿入
            writer.writerow([])

        for row in self.csv_rows:
            writer.writerow(row)

        # 生産開始～終了時間や累積数を補足情報として追記
        start_time = self.production_start_time or now
        total_hours = round(self.elapsed_seconds / 3600, 2)
        total = self.total_production - self.total_defproduction
        
        writer.writerow([])
        writer.writerow(["生産開始", start_time.strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow(["生産終了", now.strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow(["稼働時間（h）", total_hours])
        writer.writerow(["累積実績数", cumulative])
        writer.writerow(["計画数", self.plan_num])
        writer.writerow(["残り計画数", max(self.plan_num - total, 0)])

    self.csv_rows.clear()
    print(f"CSVファイルに追記しました: {file_path}")