import os
import requests # 追加: HTTP通信用ライブラリ
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 既存のスキャンツールのURL (ローカルの9800ポート)
SCANNER_API_URL = "http://127.0.0.1:9800/scan"

@app.route('/scan', methods=['POST'])
def scan_image():
    # 1. Unityから画像データを受け取る
    if 'image_file' not in request.files:
        return jsonify({'error': '画像データが見つかりません'}), 400

    file = request.files['image_file']
    if file.filename == '':
        return jsonify({'error': 'ファイル名が空です'}), 400

    # 2. 画像をローカルフォルダに保存し、絶対パスを取得する
    # スキャンツールが確実にファイルを見つけられるよう、フルパス（C:/...）に変換します
    save_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, file.filename))
    file.save(save_path)
    
    print(f"画像を保存しました: {save_path}")

    # 3. 保存したパスを使って、スキャンツール(9800番)へPOSTリクエストを送信 (curlコマンドの代わり)
    try:
        print(f"スキャンツールへリクエスト送信中... パス: {save_path}")
        
        # requestsを使って、curl -d "path=画像パス" と全く同じ通信を行います
        # proxyの設定をバイパスするために proxies={'http': None, 'https': None} を指定します
        response = requests.post(
            SCANNER_API_URL, 
            data={'path': save_path},
            proxies={'http': None, 'https': None}
        )

        # 4. スキャンツールからの返答を受け取る
        scan_result_text = response.text
        print(f"スキャン結果受信: {scan_result_text}")

        # Unityへスキャン結果をそのまま返す
        return jsonify({
            'status': 'success',
            'message': 'スキャン完了',
            'scan_result': scan_result_text
        })

    except requests.exceptions.RequestException as e:
        # スキャンツールが起動していない等のエラー処理
        print(f"スキャンツールとの通信エラー: {e}")
        return jsonify({'error': 'スキャンツールへの接続に失敗しました。ツールが起動しているか確認してください。'}), 500

if __name__ == '__main__':
    # ⚠️ 重要: 既存ツールが9800を使っているので、こちらは5000番で起動します
    app.run(host='127.0.0.1', port=5050, debug=True)