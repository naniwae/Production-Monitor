# Production-Monitor

生産ラインの稼働監視・実績記録用デスクトップアプリケーション（Raspberry Pi 向け想定）

このリポジトリは、現場のラインで生産実績をリアルタイム表示・記録するための GUI アプリケーション群です。主に wxPython で UI を実装し、GPIO（物理ボタン）入力、JSON 設定管理、CSV 形式での生産記録出力、外部 API 送信（モジュール化）などの機能を提供します。緊急用のビジュアル演出は PySide6 を使った別プロセスで表示します。

---  

主な取得済みファイル（該当ファイルへのリンク）
- RPY_Monitor.py — https://github.com/naniwae/Production-Monitor/blob/main/RPY_Monitor.py
- RPY_Json_edit.py — https://github.com/naniwae/Production-Monitor/blob/main/RPY_Json_edit.py
- RPY_prodcsv.py — https://github.com/naniwae/Production-Monitor/blob/main/RPY_prodcsv.py
- SecretEffect.py — https://github.com/naniwae/Production-Monitor/blob/main/SecretEffect.py

（リポジトリ全体は上記リンクから参照してください）

---

目次
- 概要
- 必須環境・依存ライブラリ
- ディレクトリ・ファイル構成（主要）
- 設定とデータ保存先
- 実行方法（起動／開発）
- 主要な操作フロー
- CSV / ログの仕様
- 注意点・既知の問題
- 開発・寄稿（Contributing）
- ライセンス

概要
- 生産計画を選択して「生産開始」→ 製品実績のカウント（GPIOボタン、手動入力）→ 不良の記録 → 定期的にAPIへ送信・CSVへ追記 → 「生産終了」で最終処理（CSV出力・遅延理由入力など）。
- テンキーに登録された裏コード（例: 2999）を入力すると SecretEffect（フルスクリーン演出）を別プロセスで起動します（"裏コード" 演出）。

必須環境・依存ライブラリ
- Python 3.8+(3.11が1番望ましい)
- GUI: wxPython
- 緊急表示（任意）: PySide6
- ハードウェア入出力: gpiozero（Raspberry Pi での物理ボタン読み取り）
- ファイルロック: filelock
- 標準ライブラリ: csv, os, datetime, multiprocessing など

推奨インストール（例）
- 仮想環境を作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate
- 必要パッケージをインストール
  - pip install wxPython PySide6 gpiozero filelock

（注）wxPython のインストールは環境によって追加手順が必要な場合があります（特に Raspbian / Raspberry Pi）。OS パッケージやホイールを確認してください。

ディレクトリ・ファイル構成（主要）
- RPY_Monitor.py — メイン GUI アプリ。生産開始/終了管理、タイマー、UI更新、GPIO ハンドリング、API呼び出しのタイミング管理等。
- RPY_Json_edit.py — 設定（JSON）読み書きユーティリティ。ファイルロックを使って安全に保存／読み込み。
- RPY_prodcsv.py — CSV 収集（collect_csv_row）とエクスポート（export_csv）処理。生産記録の書き出しを行う。
- SecretEffect.py — 「裏イベント」表示用の PySide6 ベースのフルスクリーン演出モジュール。別プロセスで実行される想定。
- RPY_prodAPI.py — RPY_Monitor.py から import されている API 関係モジュール（送信処理など）。リポジトリで削除されている場合、API 通信は失敗します（注意）。
- ※RPY_prodAPI.pyはBIツールに対してデータの送信を行うモジュールの為、今回は削除されています。

設定とデータ保存先
- 環境変数 BASE_DIR が必須（全ファイル共通）
  - 例: export BASE_DIR=/home/pi/production_data
  - RPY_Json_edit.py / RPY_prodcsv.py 等は BASE_DIR を起点に "設定" や "生産記録" ディレクトリを作成します。
- JSON 設定
  - BASE_DIR/設定/line_date.json（ラインと日付の情報）
  - BASE_DIR/設定/<line>/settings.json（ラインごとの設定）
  - BASE_DIR/設定/worker_data.json（作業者データ）
  - BASE_DIR/設定/break_schedule.json（休憩スケジュール）
  - BASE_DIR/サイクルタイム/cycletime1.json, cycletime2.json
- 生産記録（CSV）
  - BASE_DIR/生産記録/<ライン>/<品番>/期間_<start>_<end>.csv
  - CSV は追記形式で、ヘッダー、追記行、最後に補足情報（開始/終了時刻、稼働時間、累積実績数など）を追記します。

実行方法（起動／開発）
1. 環境変数を設定
   - Linux / macOS:
     - export BASE_DIR=/path/to/data
   - Windows (PowerShell):
     - $env:BASE_DIR = 'C:\path\to\data'
2. 必要パッケージをインストール（上記を参照）
3. アプリ起動
   - python RPY_Monitor.py
   - 本アプリはフルスクリーン表示の UI を生成します（ディスプレイに合わせてウィンドウを拡大）。
4. 開発で GPIO を無効化したい場合は、gpiozero の Button をモック／差し替え、もしくは該当コードの呼び出しをコメントアウトしてください（Raspberry Pi 以外の環境での起動対策）。

主要な操作フロー（ユーザー向け）
1. 「設定」ボタンで生産計画を選択（SettingsDialog）
2. 生産指示数をテンキーで入力
3. 「生産開始」ボタンで生産を開始 → タイマー開始、CSV収集やAPI送信を開始
4. 実績は GPIO ボタンでカウント（あるいはソフト側で追加）
5. 不良はテンキーで数を入力して「不良数追加」
6. 定期的（5秒間隔でステータス送信、20分でログ送信）に API に送信（RPY_prodAPI が正しく実��されている場合）
7. 生産終了時に CSV 出力、必要であれば遅延理由入力ダイアログ（ReasonDialog）が表示される

CSV / ログの仕様（RPY_prodcsv.py）
- collect_csv_row() により時点ごとの行を self.csv_rows に追加
- export_csv() によりファイルに追記
  - 行内容（日時, 作業者, ライン, 品番, 指示数, 実績数, 進捗数, 不良数, 差, 達成率, 可動率）
  - 補足行に生産開始・終了時刻、稼働時間、累積実績数、計画数などを追記
- CSV は UTF-8-sig で出力（Excel 互換）

注意点・既知の問題
- 環境変数 BASE_DIR が未設定だと起動時に例外を投げます（EnvironmentError が発生）。
- RPY_Monitor.py は RPY_prodAPI モジュールを import していますが、リポジトリ内で削除されている場合は ImportError となり、API 関連の呼び出しで失敗します。API を有効にするには RPY_prodAPI.py を追加し、send_status / finish_status / send_log / product_log / finish_log の関数を実装してください。
- SecretEffect.py は PySide6 を使うため、PySide6 をインストールしておく必要があります。SecretEffect は別プロセスで実行され、フルスクリーンで派手な演出を行います。運用で誤って起動されないよう管理してください（テンキーに裏コードが設定されています）。
- GPIO（gpiozero）依存：Raspberry Pi 以外での実行時はモックするか、Button 部分を無効化してください。
- 多重プロセス起動時の互換性・エラーハンドリングは限定的です。特にファイルI/Oの競合を避けるため filelock を使用していますが、運用環境での動作確認を推奨します。
- UI の一部（フォントサイズ等）はハードウェアに依存して見切れることがあるため、解像度に合わせて調整が必要です。

開発・寄稿（Contributing）
- バグ報告や機能追加の提案は GitHub Issues を使ってください。
- 変更する場合は、まず Issue を立ててから Pull Request を送ってください。PR には変更点の概要、動作確認手順、影響範囲を明記してください。
- 他者が実行できるよう、可能であれば requirements.txt やインストール手順のドキュメント化を追加してください。

運用上のセキュリティ注意
- テンキーの「裏コード」は意図せず秘密機能を呼び出す恐れがあります。SecretEffect や他の秘密機能を使う場合は運用ルールを定め、管理者以外が誤って起動しないようにしてください。
- 外部 API への送信機能を追加する場合、認証情報やエンドポイントを安全に管理してください（リポジトリに平文で置かない）。

開発者向けヒント・デバッグ
- API 実装が未整備なら、RPY_prodAPI.py の代わりにダミー関数を定義して import する（send_status 等を no-op にする）とアプリ本体の動作検証が可能です。
- BASE_DIR を一時的にホームディレクトリ等に向ければローカル環境でのテストが容易です。
- GUI のテストは手動が主になります。ログ出力（print）や CSV 出力を使って動作確認してください。
