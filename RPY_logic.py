import datetime
def progress_logic(self):
    now = datetime.datetime.now()
    try:
        ctl = int(self.cycle_time)
    except (ValueError, TypeError):
        ctl = 1

    ct = ctl if  ctl > 0 else 1
    elapsed = max(0, self.elapsed_seconds)
                    
    #実績数の計算
    self.total= self.total_production-self.total_defproduction
    self.remaining=self.planday_num - self.total
    #ctr = ct*1.25
                    
    #残りの予想作業時間
    self.worktime=(self.remaining*ct)/3600
    
    #目標進捗数の計算
    self.progress = int(elapsed/ct)
    self.progress = min(self.progress, self.planday_num)

    #進捗との差分計算
    self.diff = self.total - self.progress