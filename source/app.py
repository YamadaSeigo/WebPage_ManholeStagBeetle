import os
import requests # 追加: HTTP通信用ライブラリ
import uuid # 追加: 複数同時アクセス用にランダムなファイル名を作るため
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

    # 【変更】複数アプリからの同時アクセスでファイルが上書きされないよう、
    # uuidを使って「絶対に被らないランダムなファイル名」を生成します。
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    save_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, unique_filename))
    
    file.save(save_path)
    
    print(f"画像を一時保存しました: {save_path}")

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

    finally:
        # 【追加】成功・失敗に関わらず、最後に必ず実行される処理
        # スキャンが終わった画像を削除して、PCの容量を圧迫しないようにします
        if os.path.exists(save_path):
            os.remove(save_path)
            print(f"不要になった一時ファイルを削除しました: {save_path}")

if __name__ == '__main__':
    # ⚠️ 5000番は他のアプリと衝突しやすいため、安全な5050番に変更しています
    # 外部(ngrok)から確実につながるように host を '0.0.0.0' にしています
    app.run(host='0.0.0.0', port=5050, debug=True)