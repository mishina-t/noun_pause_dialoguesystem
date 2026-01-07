"""メインアプリケーション"""
import sys
import time
import threading
from typing import Literal
import select
import tty
import termios

from config import Config, Mode
from audio_recorder import AudioRecorder
from stt import WhisperSTT
from llm import OpenAILLM
from text_processor import NounPauseProcessor
from tts import VoiceVoxTTS
from ui import ConsoleUI, Status

# グローバル状態
current_mode: Mode = Config.MODE_DEFAULT  # type: ignore
is_running = True
recording = False
last_user_text = ""
last_ai_text = ""
last_processed_text = ""


def main():
    """メインループ"""
    global current_mode, is_running, recording
    
    # 設定検証
    try:
        Config.validate()
    except ValueError as e:
        print(f"設定エラー: {e}")
        sys.exit(1)
    
    # コンポーネント初期化
    print("初期化中...")
    ui = ConsoleUI()
    
    # AudioRecorderの初期化（エラーハンドリング）
    try:
        recorder = AudioRecorder()
        print("✓ 音声録音モジュールを初期化しました")
    except RuntimeError as e:
        print(f"✗ 音声録音モジュールの初期化に失敗しました: {e}")
        print("\n対処方法:")
        print("1. PyAudioをインストール: pip install pyaudio")
        print("2. macOSの場合: brew install portaudio && pip install pyaudio")
        print("3. マイクのアクセス許可を確認")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 予期しないエラー: {e}")
        sys.exit(1)
    
    # STTの初期化（時間がかかる可能性がある）
    try:
        print("Whisperモデルを読み込み中...")
        stt = WhisperSTT(model_name="base")  # MVPはbaseモデル
        print("✓ STTモジュールを初期化しました")
    except Exception as e:
        print(f"✗ STTモジュールの初期化に失敗しました: {e}")
        sys.exit(1)
    
    # LLMの初期化
    try:
        llm = OpenAILLM()
        print("✓ LLMモジュールを初期化しました")
    except Exception as e:
        print(f"✗ LLMモジュールの初期化に失敗しました: {e}")
        sys.exit(1)
    
    # テキスト処理の初期化
    try:
        text_processor = NounPauseProcessor(pause_marker="、")
        print("✓ テキスト処理モジュールを初期化しました")
    except Exception as e:
        print(f"✗ テキスト処理モジュールの初期化に失敗しました: {e}")
        sys.exit(1)
    
    # TTSの初期化
    try:
        tts = VoiceVoxTTS()
        print("✓ TTSモジュールを初期化しました")
    except Exception as e:
        print(f"✗ TTSモジュールの初期化に失敗しました: {e}")
        sys.exit(1)
    
    # 初期表示
    ui.render(status="IDLE", mode=current_mode)
    
    print("\n準備完了！")
    print("操作:")
    print("  [Enter] 録音開始/停止")
    print("  [M] モード切替")
    print("  [Q] 終了")
    print("")
    
    # 録音ループ（別スレッド）
    def recording_loop():
        global recording
        while is_running:
            if recording:
                recorder.record_chunk()
            time.sleep(0.01)  # 10ms間隔
    
    recording_thread = threading.Thread(target=recording_loop, daemon=True)
    recording_thread.start()
    
    # メインループ（標準入力からキー入力を読み取る）
    try:
        # ターミナル設定を保存
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())
        
        try:
            while is_running:
                # 非ブロッキングでキー入力を読み取る
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    
                    if key == '\r' or key == '\n':  # Enterキー
                        if recording:
                            # 録音停止
                            stop_and_process(recorder, stt, llm, text_processor, tts, ui)
                        else:
                            # 録音開始
                            start_recording(recorder, ui)
                    elif key.lower() == 'm':  # Mキー
                        toggle_mode(ui)
                    elif key.lower() == 'q':  # Qキー
                        exit_app(recorder)
                        break
        finally:
            # ターミナル設定を復元
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    except KeyboardInterrupt:
        exit_app(recorder)
    except Exception as e:
        # エラー時もターミナル設定を復元
        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        except:
            pass
        print(f"\nエラーが発生しました: {e}")
        exit_app(recorder)


def start_recording(recorder: AudioRecorder, ui: ConsoleUI = None):
    """録音開始"""
    global recording, current_mode
    if not recording:
        recording = True
        recorder.start_recording()
        if ui:
            ui.render(status="REC", mode=current_mode)


def stop_and_process(
    recorder: AudioRecorder,
    stt: WhisperSTT,
    llm: OpenAILLM,
    text_processor: NounPauseProcessor,
    tts: VoiceVoxTTS,
    ui: ConsoleUI
):
    """録音停止して処理"""
    global recording, current_mode
    
    if not recording:
        return
    
    recording = False
    
    # 録音停止
    audio_data = recorder.stop_recording()
    if not audio_data:
        return
    
    # STT
    ui.render(status="STT", mode=current_mode)
    try:
        user_text, stt_time = stt.transcribe(audio_data)
    except Exception as e:
        print(f"STTエラー: {e}")
        ui.render(status="IDLE", mode=current_mode)
        return
    
    ui.render(user_text=user_text, status="GEN", mode=current_mode)
    
    # LLM
    try:
        ai_text, llm_time = llm.respond(user_text)
    except Exception as e:
        print(f"LLMエラー: {e}")
        ui.render(user_text=user_text, status="IDLE", mode=current_mode)
        return
    
    # テキスト処理
    if current_mode == "nounpause":
        processed_text = text_processor.process_text(ai_text)
    else:
        processed_text = ai_text
    
    ui.render(
        user_text=user_text,
        ai_text=ai_text,
        processed_text=processed_text if current_mode == "nounpause" else "",
        status="SPEAK",
        mode=current_mode
    )
    
    # TTS
    try:
        tts_time = tts.speak(processed_text)
    except Exception as e:
        print(f"TTSエラー: {e}")
        ui.render(
            user_text=user_text,
            ai_text=ai_text,
            processed_text=processed_text if current_mode == "nounpause" else "",
            status="IDLE",
            mode=current_mode
        )
        return
    
    # ログ出力
    log_turn(user_text, ai_text, processed_text, current_mode, stt_time, llm_time, tts_time)
    
    # グローバル状態を更新
    global last_user_text, last_ai_text, last_processed_text
    last_user_text = user_text
    last_ai_text = ai_text
    last_processed_text = processed_text if current_mode == "nounpause" else ""
    
    # 完了
    ui.render(
        user_text=user_text,
        ai_text=ai_text,
        processed_text=processed_text if current_mode == "nounpause" else "",
        status="IDLE",
        mode=current_mode
    )


def toggle_mode(ui: ConsoleUI):
    """モード切替"""
    global current_mode, recording, last_user_text, last_ai_text, last_processed_text
    current_mode = "nounpause" if current_mode == "normal" else "normal"
    status = "REC" if recording else "IDLE"
    # モード切替時は既存のテキストを再表示
    ui.render(
        user_text=last_user_text,
        ai_text=last_ai_text,
        processed_text=last_processed_text if current_mode == "nounpause" else "",
        status=status,
        mode=current_mode
    )


def exit_app(recorder: AudioRecorder):
    """アプリケーション終了"""
    global is_running, recording
    is_running = False
    recording = False
    recorder.cleanup()
    print("\n終了します...")
    sys.exit(0)


def log_turn(
    user_text: str,
    ai_text: str,
    processed_text: str,
    mode: Mode,
    stt_time: float,
    llm_time: float,
    tts_time: float
):
    """1ターンのログを保存"""
    import datetime
    
    timestamp = datetime.datetime.now().isoformat()
    log_entry = f"""
[{timestamp}]
mode: {mode}
user_text: {user_text}
ai_text: {ai_text}
processed_text: {processed_text}
latencies: STT={stt_time:.2f}s, LLM={llm_time:.2f}s, TTS={tts_time:.2f}s
---
"""
    
    try:
        with open(Config.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"ログ保存エラー: {e}")


if __name__ == "__main__":
    main()

