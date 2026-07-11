import os
import requests
import uuid
import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 絶対パスでuploadsフォルダとDBファイルを作成するように固定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SCANNER_API_URL = "http://127.0.0.1:9800/scan"
DB_FILE = os.path.join(BASE_DIR, 'scan_history.db')

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # ユーザーIDも含めた履歴テーブルを作成
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            player_name TEXT,
            scan_time TEXT,
            result_data TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/scan', methods=['POST'])
def scan_image():
    if 'image_file' not in request.files:
        return jsonify({'error': '画像データが見つかりません'}), 400

    file = request.files['image_file']
    if file.filename == '':
        return jsonify({'error': 'ファイル名が空です'}), 400

    # Unityから送られてきた「ユーザーID」と「プレイヤー名」を受け取る
    user_id = request.form.get('user_id', 'unknown_id')
    player_name = request.form.get('player_name', '名無しプレイヤー')

    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    save_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, unique_filename))
    
    file.save(save_path)
    print(f"画像を一時保存しました: {save_path}")

    try:
        print(f"スキャンツールへリクエスト送信中... パス: {save_path}")
        
        # ▼▼ ユーザー様の完璧な通信コード（curl -d "path=" と同じ） ▼▼
        response = requests.post(
            SCANNER_API_URL, 
            data={'path': save_path},
            proxies={'http': None, 'https': None}
        )

        print(f"スキャン結果受信(生データ): {response.text}")

        # ▼▼ ユーザー様の完璧なJSONパース処理 ▼▼
        try:
            scan_result_data = json.loads(response.text)
            if isinstance(scan_result_data, str):
                scan_result_data = json.loads(scan_result_data)
        except:
            scan_result_data = {"is_succsess": "NO", "error_info": response.text}

        # 結果をデータベースに記録する
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('INSERT INTO history (user_id, player_name, scan_time, result_data) VALUES (?, ?, ?, ?)',
                  (user_id, player_name, current_time, json.dumps(scan_result_data, ensure_ascii=False)))
        conn.commit()
        conn.close()
        print(f"★ DBに保存しました: {player_name} ({current_time})")

        return jsonify({
            'status': 'success',
            'message': 'スキャン完了',
            'scan_result': scan_result_data 
        })

    except requests.exceptions.RequestException as e:
        print(f"スキャンツールとの通信エラー: {e}")
        return jsonify({'error': 'スキャンツールへの接続に失敗しました。'}), 500

    finally:
        # スキャンが終わった画像を削除する
        if os.path.exists(save_path):
            os.remove(save_path)
            print(f"不要になった一時ファイルを削除しました: {save_path}")

@app.route('/history', methods=['GET'])
def get_history():
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM history ORDER BY id DESC LIMIT 20')
        rows = c.fetchall()
        conn.close()
        
        history_list = []
        for row in rows:
            history_list.append({
                'id': row['id'],
                'player_name': row['player_name'],
                'scan_time': row['scan_time'],
                'result_data': json.loads(row['result_data'])
            })
            
        return jsonify({'status': 'success', 'history': history_list})
    except Exception as e:
        print(f"履歴取得エラー: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/my_history', methods=['GET'])
def get_my_history():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'status': 'error', 'message': 'user_idがありません'}), 400

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        # WHERE句を使って user_id が一致するものだけを抽出
        c.execute('SELECT * FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 20', (user_id,))
        rows = c.fetchall()
        conn.close()
        
        history_list = []
        for row in rows:
            history_list.append({
                'id': row['id'],
                'player_name': row['player_name'],
                'scan_time': row['scan_time'],
                'result_data': json.loads(row['result_data'])
            })
            
        return jsonify({'status': 'success', 'history': history_list})
    except Exception as e:
        print(f"個人の履歴取得エラー: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)