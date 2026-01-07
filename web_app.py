"""Webアプリケーション（ブラウザでテキスト入力、音声で応答）"""
from flask import Flask, render_template_string, request, jsonify
import threading
import time
import sys
import base64
from config import Config, Mode
from llm import OpenAILLM
from text_processor import NounPauseProcessor
from tts import VoiceVoxTTS

app = Flask(__name__)

# グローバル状態
current_mode: Mode = Config.MODE_DEFAULT  # type: ignore
llm = None
text_processor = None
tts = None

# HTMLテンプレート
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NounPause Voice Assistant</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Yu Gothic', 'Meiryo', sans-serif;
            background: #000;
            color: #fff;
            display: flex;
            flex-direction: column;
            height: 100vh;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .mode-selector {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 30px;
        }
        .mode-btn {
            padding: 10px 30px;
            font-size: 1.2em;
            background: #333;
            color: #fff;
            border: 2px solid #666;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .mode-btn.active {
            background: #0066ff;
            border-color: #0066ff;
        }
        .mode-btn:hover {
            background: #555;
        }
        .mode-btn.active:hover {
            background: #0055dd;
        }
        .input-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            max-width: 800px;
            margin: 0 auto;
            width: 100%;
        }
        .input-box {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        textarea {
            flex: 1;
            padding: 20px;
            font-size: 1.2em;
            background: #1a1a1a;
            color: #fff;
            border: 2px solid #444;
            border-radius: 10px;
            resize: none;
            font-family: inherit;
        }
        textarea:focus {
            outline: none;
            border-color: #0066ff;
        }
        .button-area {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        button {
            flex: 1;
            padding: 15px;
            font-size: 1.2em;
            background: #0066ff;
            color: #fff;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }
        button:hover:not(:disabled) {
            background: #0055dd;
        }
        button:disabled {
            background: #333;
            cursor: not-allowed;
        }
        .status {
            text-align: center;
            margin-top: 20px;
            font-size: 1.1em;
            color: #888;
        }
        .history {
            margin-top: 30px;
            max-height: 300px;
            overflow-y: auto;
            padding: 20px;
            background: #1a1a1a;
            border-radius: 10px;
        }
        .history-item {
            margin-bottom: 20px;
            padding: 15px;
            background: #2a2a2a;
            border-radius: 5px;
        }
        .history-item .user {
            color: #66ff66;
            margin-bottom: 10px;
        }
        .history-item .ai {
            color: #66aaff;
        }
        .history-item .processed {
            color: #ffaa66;
            font-size: 0.9em;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>NounPause Voice Assistant</h1>
        <p>テキストを入力して、音声で応答を受け取ります</p>
    </div>
    
    <div class="mode-selector">
        <button class="mode-btn" id="normalBtn" onclick="setMode('normal')">Normal</button>
        <button class="mode-btn" id="nounpauseBtn" onclick="setMode('nounpause')">NounPause</button>
    </div>
    
    <div class="input-area">
        <div class="input-box">
            <textarea id="inputText" placeholder="ここにテキストを入力してください..." rows="5"></textarea>
            <div class="button-area">
                <button id="sendBtn" onclick="sendMessage()">送信（音声で応答）</button>
                <button onclick="clearInput()">クリア</button>
            </div>
        </div>
        <div class="status" id="status">待機中</div>
    </div>
    
    <div class="history" id="history"></div>
    
    <script>
        let currentMode = 'normal';
        
        function setMode(mode) {
            currentMode = mode;
            document.getElementById('normalBtn').classList.toggle('active', mode === 'normal');
            document.getElementById('nounpauseBtn').classList.toggle('active', mode === 'nounpause');
        }
        
        function clearInput() {
            document.getElementById('inputText').value = '';
        }
        
        function playAudio(base64Audio) {
            try {
                console.log('音声再生開始 - Base64データ長:', base64Audio.length);
                
                // Base64デコード
                const audioData = atob(base64Audio);
                console.log('Base64デコード成功 - バイナリデータ長:', audioData.length);
                
                const audioArray = new Uint8Array(audioData.length);
                for (let i = 0; i < audioData.length; i++) {
                    audioArray[i] = audioData.charCodeAt(i);
                }
                
                // Blobを作成
                const blob = new Blob([audioArray], { type: 'audio/wav' });
                console.log('Blob作成成功 - サイズ:', blob.size, 'bytes');
                const url = URL.createObjectURL(blob);
                console.log('Object URL作成:', url);
                
                // Audio要素で再生
                const audio = new Audio(url);
                
                // イベントリスナーを追加（デバッグ用）
                audio.addEventListener('loadstart', () => {
                    console.log('音声読み込み開始');
                });
                audio.addEventListener('loadeddata', () => {
                    console.log('音声データ読み込み完了');
                });
                audio.addEventListener('canplay', () => {
                    console.log('音声再生可能');
                });
                audio.addEventListener('play', () => {
                    console.log('音声再生開始');
                });
                audio.addEventListener('error', (e) => {
                    console.error('Audio要素エラー:', e);
                    console.error('エラー詳細:', audio.error);
                    document.getElementById('status').textContent = '音声再生エラー: ' + (audio.error ? audio.error.message : '不明なエラー');
                    URL.revokeObjectURL(url);
                });
                
                audio.play().then(() => {
                    console.log('play()成功');
                    // 再生終了時にURLを解放
                    audio.addEventListener('ended', () => {
                        console.log('音声再生終了');
                        URL.revokeObjectURL(url);
                        document.getElementById('status').textContent = '待機中';
                    });
                }).catch(error => {
                    console.error('play()エラー:', error);
                    console.error('エラー詳細:', error.message);
                    document.getElementById('status').textContent = '音声再生に失敗しました: ' + error.message;
                    URL.revokeObjectURL(url);
                });
            } catch (error) {
                console.error('音声処理エラー:', error);
                console.error('エラースタック:', error.stack);
                document.getElementById('status').textContent = '音声処理に失敗しました: ' + error.message;
            }
        }
        
        async function sendMessage() {
            const input = document.getElementById('inputText').value.trim();
            if (!input) {
                alert('テキストを入力してください');
                return;
            }
            
            const sendBtn = document.getElementById('sendBtn');
            const status = document.getElementById('status');
            const history = document.getElementById('history');
            
            // UI更新
            sendBtn.disabled = true;
            status.textContent = '処理中...';
            
            // ユーザー入力を履歴に追加
            const userItem = document.createElement('div');
            userItem.className = 'history-item';
            userItem.innerHTML = `<div class="user">[USER] ${input}</div>`;
            history.insertBefore(userItem, history.firstChild);
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        text: input,
                        mode: currentMode
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // AI応答を履歴に追加
                    const aiItem = document.createElement('div');
                    aiItem.className = 'history-item';
                    let html = `<div class="ai">[AI] ${data.ai_text}</div>`;
                    if (data.processed_text && data.processed_text !== data.ai_text) {
                        html += `<div class="processed">[AI - processed] ${data.processed_text}</div>`;
                    }
                    aiItem.innerHTML = html;
                    history.insertBefore(aiItem, history.firstChild);
                    
                    // 音声再生
                    if (data.audio_data) {
                        console.log('音声データを受信しました。サイズ:', data.audio_data.length, 'chars');
                        status.textContent = '音声再生中...';
                        playAudio(data.audio_data);
                    } else {
                        const errorMsg = data.audio_error || '音声生成に失敗しました';
                        console.error('音声生成エラー:', errorMsg);
                        status.textContent = '音声生成に失敗しました: ' + errorMsg;
                        alert('音声生成エラー: ' + errorMsg);
                    }
                } else {
                    status.textContent = 'エラー: ' + data.error;
                    alert('エラー: ' + data.error);
                }
            } catch (error) {
                status.textContent = 'エラーが発生しました';
                alert('エラー: ' + error.message);
            } finally {
                sendBtn.disabled = false;
                clearInput();
            }
        }
        
        // Enterキーで送信（Shift+Enterで改行）
        document.getElementById('inputText').addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // 初期モード設定
        setMode('normal');
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """メインページ"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/check_voicevox', methods=['GET'])
def check_voicevox():
    """VOICEVOXの接続確認"""
    global tts
    try:
        # 簡単なテストリクエスト
        test_text = "テスト"
        wav_data = tts.synthesize(test_text)
        return jsonify({
            'success': True,
            'message': 'VOICEVOXに接続できました',
            'audio_size': len(wav_data)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """チャットAPI"""
    global current_mode, llm, text_processor, tts
    
    try:
        data = request.json
        user_text = data.get('text', '').strip()
        mode = data.get('mode', 'normal')
        
        if not user_text:
            return jsonify({'success': False, 'error': 'テキストが空です'})
        
        # モードを更新
        current_mode = mode  # type: ignore
        
        # LLMで応答生成
        ai_text, llm_time = llm.respond(user_text)
        
        # テキスト処理
        if mode == "nounpause":
            processed_text = text_processor.process_text(ai_text)
        else:
            processed_text = ai_text
        
        # TTSで音声データを生成（ブラウザで再生するため）
        audio_data = None
        error_message = None
        try:
            print(f"TTS: 音声合成開始 - テキスト: {processed_text[:50]}...")
            print(f"TTS: テキスト全体: {processed_text}")
            print(f"TTS: テキスト長: {len(processed_text)} chars")
            wav_data = tts.synthesize(processed_text)
            print(f"TTS: 音声データ生成成功 - サイズ: {len(wav_data)} bytes")
            # Base64エンコードしてブラウザに送信
            audio_data = base64.b64encode(wav_data).decode('utf-8')
            print(f"TTS: Base64エンコード成功 - サイズ: {len(audio_data)} chars")
        except Exception as e:
            error_message = str(e)
            print(f"TTSエラー: {error_message}")
            print(f"TTSエラー詳細: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            # エラーメッセージをより分かりやすく
            if "500" in error_message or "Internal Server Error" in error_message:
                error_message = "VOICEVOXサーバーでエラーが発生しました。サーバー管理者に確認してください。"
            elif "Connection" in error_message or "接続" in error_message:
                error_message = "VOICEVOXサーバーに接続できません。サーバーが起動しているか確認してください。"
            # 音声生成に失敗してもテキストは返す
        
        return jsonify({
            'success': True,
            'ai_text': ai_text,
            'processed_text': processed_text if mode == "nounpause" else "",
            'mode': mode,
            'audio_data': audio_data,  # Base64エンコードされたWAVデータ
            'audio_error': error_message if error_message else None
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def init_components():
    """コンポーネントを初期化"""
    global llm, text_processor, tts
    
    print("コンポーネントを初期化中...")
    
    # LLM
    llm = OpenAILLM()
    print("✓ LLMモジュールを初期化しました")
    
    # テキスト処理
    text_processor = NounPauseProcessor(pause_marker="、")
    print("✓ テキスト処理モジュールを初期化しました")
    
    # TTS
    tts = VoiceVoxTTS()
    print("✓ TTSモジュールを初期化しました")
    
    # VOICEVOXの接続確認
    print("\nVOICEVOXの接続確認中...")
    try:
        import requests
        test_url = f"{Config.VOICEVOX_BASE_URL}/speakers"
        response = requests.get(test_url, timeout=3)
        if response.status_code == 200:
            print(f"✓ VOICEVOXに接続できました: {Config.VOICEVOX_BASE_URL}")
        else:
            print(f"⚠ VOICEVOXへの接続に問題があります (ステータスコード: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print(f"✗ VOICEVOXに接続できません: {Config.VOICEVOX_BASE_URL}")
        print("\n対処方法:")
        print("1. VOICEVOXを起動してください")
        print("2. VOICEVOX_SETUP.md を参照してセットアップしてください")
        print("3. ポート番号が正しいか確認してください（デフォルト: 50021）")
    except Exception as e:
        print(f"⚠ VOICEVOXの接続確認中にエラー: {e}")
    print()


if __name__ == '__main__':
    import os
    
    # コンポーネントを初期化
    init_components()
    
    # ポート番号を取得（環境変数またはデフォルト）
    port = Config.WEB_APP_PORT
    
    print("\n" + "=" * 60)
    print("Webアプリケーションを起動します")
    print("=" * 60)
    print(f"\nブラウザで以下のURLにアクセスしてください:")
    print(f"  http://localhost:{port}")
    print("\n終了するには Ctrl+C を押してください")
    print("=" * 60 + "\n")
    
    try:
        # Flaskアプリを起動
        app.run(host='0.0.0.0', port=port, debug=False)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n✗ エラー: ポート {port} はすでに使用されています。")
            print("別のプログラムがポートを使用しているか、AirPlay Receiverが有効になっている可能性があります。")
            print("対処方法:")
            print(f"1. ポート {port} を使用しているプログラムを特定して停止する。")
            print("2. macOSの場合、システム設定で「AirPlay Receiver」を検索して無効にする。")
            print(f"3. 環境変数 WEB_APP_PORT を設定して別のポートで起動する (例: export WEB_APP_PORT=5002)。")
        else:
            print(f"✗ Flask起動エラー: {e}")
        sys.exit(1)

