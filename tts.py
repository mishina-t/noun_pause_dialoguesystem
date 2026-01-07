"""VOICEVOX TTS実装"""
import io
import time
from typing import Optional
import numpy as np
import soundfile as sf

try:
    import requests
    REQUESTS_AVAILABLE = True
except (ImportError, PermissionError, OSError) as e:
    REQUESTS_AVAILABLE = False
    print(f"警告: requestsのインポートに失敗しました: {type(e).__name__}")
    print("インストール方法: pip install requests")

try:
    from pydub import AudioSegment
    from pydub.playback import play
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("警告: pydubがインストールされていません。")
    print("インストール方法: pip install pydub")

from config import Config


class VoiceVoxTTS:
    """VOICEVOX HTTP APIを使用したTTS"""
    
    def __init__(self, base_url: str = None, speaker_id: int = None):
        # base_urlの末尾のスラッシュを削除（URL構築時に追加するため）
        raw_url = base_url or Config.VOICEVOX_BASE_URL
        self.base_url = raw_url.rstrip('/')
        self.speaker_id = speaker_id or Config.VOICEVOX_SPEAKER_ID
    
    def synthesize(self, text: str) -> bytes:
        """
        テキストを音声に変換
        
        Args:
            text: 合成するテキスト
            
        Returns:
            WAV形式の音声データ（bytes）
        """
        if not REQUESTS_AVAILABLE:
            raise RuntimeError(
                "requestsがインストールされていません。"
                "インストール方法: pip install requests"
            )
        
        # audio_query取得
        query_url = f"{self.base_url}/audio_query"
        # パラメータの設定(text: 合成するテキスト, speaker: 話者ID)ここではずんだもん
        params = {
            "text": text,
            "speaker": self.speaker_id
        }
        
        print(f"TTS: audio_queryリクエスト - URL: {query_url}, params: {params}")
        try:
            # HTTP POSTリクエストを送信
            response = requests.post(
                query_url, 
                params=params, 
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            print(f"TTS: audio_queryレスポンス - ステータス: {response.status_code}")
            if response.status_code != 200:
                print(f"TTS: エラーレスポンス内容: {response.text[:500]}")
            response.raise_for_status()
            # JSON形式でレスポンスを取得
            audio_query = response.json()
            print(f"TTS: audio_query取得成功")
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            if hasattr(e, 'response') and e.response is not None:
                error_detail = f" - レスポンス: {e.response.text[:200]}"
            print(f"TTS: audio_query HTTPエラー - {e}{error_detail}")
            raise RuntimeError(f"VOICEVOXサーバーエラー (audio_query): {e}{error_detail}") from e
        except requests.exceptions.RequestException as e:
            print(f"TTS: audio_queryエラー - {type(e).__name__}: {e}")
            raise RuntimeError(f"VOICEVOXサーバーへの接続エラー (audio_query): {e}") from e
        
        # synthesisで
        synthesis_url = f"{self.base_url}/synthesis"
        params = {"speaker": self.speaker_id}
        
        print(f"TTS: synthesisリクエスト - URL: {synthesis_url}, params: {params}")
        print(f"TTS: audio_queryデータサイズ: {len(str(audio_query))} chars")
        try:
            response = requests.post(
                synthesis_url,
                params=params,
                json=audio_query,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            print(f"TTS: synthesisレスポンス - ステータス: {response.status_code}")
            if response.status_code != 200:
                print(f"TTS: エラーレスポンス内容: {response.text[:500]}")
            response.raise_for_status()
            print(f"TTS: synthesis取得成功 - データサイズ: {len(response.content)} bytes")
            return response.content
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            if hasattr(e, 'response') and e.response is not None:
                error_detail = f" - レスポンス: {e.response.text[:200]}"
            print(f"TTS: synthesis HTTPエラー - {e}{error_detail}")
            raise RuntimeError(f"VOICEVOXサーバーエラー (synthesis): {e}{error_detail}") from e
        except requests.exceptions.RequestException as e:
            print(f"TTS: synthesisエラー - {type(e).__name__}: {e}")
            raise RuntimeError(f"VOICEVOXサーバーへの接続エラー (synthesis): {e}") from e
    
    def speak(self, text: str) -> float:
        """
        テキストを音声合成して再生
        
        Args:
            text: 再生するテキスト
            
        Returns:
            処理時間（秒）
        """
        if not PYDUB_AVAILABLE:
            raise RuntimeError(
                "pydubがインストールされていません。"
                "インストール方法: pip install pydub"
            )
        
        start_time = time.time()
        
        wav_data = self.synthesize(text)
        
        # WAVデータを再生
        audio = AudioSegment.from_wav(io.BytesIO(wav_data))
        play(audio)
        
        elapsed = time.time() - start_time
        return elapsed
    
    def synthesize_with_pause(self, text_parts: list[str], pause_sec: float = 0.8) -> bytes:
        """
        複数のテキストを無音を挟んで合成
        
        Args:
            text_parts: 分割されたテキストのリスト
            pause_sec: 無音の秒数
            
        Returns:
            結合されたWAV形式の音声データ
        """
        if not PYDUB_AVAILABLE:
            raise RuntimeError(
                "pydubがインストールされていません。"
                "インストール方法: pip install pydub"
            )
        
        audio_segments = []
        
        for i, part in enumerate(text_parts):
            if part.strip():
                wav_data = self.synthesize(part.strip())
                segment = AudioSegment.from_wav(io.BytesIO(wav_data))
                audio_segments.append(segment)
            
            # 最後の部分以外は無音を追加
            if i < len(text_parts) - 1:
                silence = AudioSegment.silent(duration=int(pause_sec * 1000))
                audio_segments.append(silence)
        
        # 結合
        if audio_segments:
            combined = sum(audio_segments)
            wav_io = io.BytesIO()
            combined.export(wav_io, format="wav")
            return wav_io.getvalue()
        else:
            return b""

