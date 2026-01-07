"""設定管理モジュール"""
import os
import re
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv

# .envファイルを読み込む（プロジェクトルートを探す）
# .envファイルが存在しない場合やアクセスできない場合はエラーにしない
env_path = Path(__file__).parent / ".env"
try:
    if env_path.exists() and env_path.is_file():
        load_dotenv(env_path, override=False)
except (PermissionError, OSError):
    # ファイルへのアクセス権限がない場合は環境変数のみを使用
    pass

Mode = Literal["normal", "nounpause"]


def normalize_azure_endpoint(endpoint: str) -> str:
    """
    Azure OpenAI Serviceのエンドポイントを正規化
    
    完全なAPI URLからベースURLを抽出します。
    例:
    - https://resource.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=...
      -> https://resource.openai.azure.com/
    - https://resource.cognitiveservices.azure.com/openai/deployments/...
      -> https://resource.cognitiveservices.azure.com/
    """
    if not endpoint:
        return endpoint
    
    # 末尾のスラッシュと空白を削除
    endpoint = endpoint.strip().rstrip('/')
    
    # 完全なAPI URLの場合、ベースURLを抽出
    # パターン1: /openai/deployments/ 以降を削除
    match = re.search(r'^(https?://[^/]+)', endpoint)
    if match:
        base_url = match.group(1)
        # 末尾にスラッシュを追加
        return base_url + '/'
    
    # 既にベースURLの形式の場合
    if endpoint.endswith('/'):
        return endpoint
    else:
        return endpoint + '/'


class Config:
    """アプリケーション設定"""
    
    # OpenAI / Azure OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Azure OpenAI Service設定（Azureを使用する場合）
    _AZURE_OPENAI_ENDPOINT_RAW: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_ENDPOINT: str = normalize_azure_endpoint(_AZURE_OPENAI_ENDPOINT_RAW) if _AZURE_OPENAI_ENDPOINT_RAW else ""
    AZURE_OPENAI_DEPLOYMENT_NAME: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    
    # 使用するサービス（"openai" または "azure"）
    OPENAI_SERVICE_TYPE: str = os.getenv("OPENAI_SERVICE_TYPE", "openai")
    
    # VOICEVOX
    VOICEVOX_BASE_URL: str = os.getenv("VOICEVOX_BASE_URL", "http://localhost:50021")
    VOICEVOX_SPEAKER_ID: int = int(os.getenv("VOICEVOX_SPEAKER_ID", "1"))
    
    # Mode
    MODE_DEFAULT: Mode = os.getenv("MODE_DEFAULT", "normal")  # type: ignore
    
    # NounPause settings
    PAUSE_STRENGTH: str = os.getenv("PAUSE_STRENGTH", "strong")
    PAUSE_SEC: float = float(os.getenv("PAUSE_SEC", "1.2"))  # 無音秒数（1.5倍に変更: 0.8 → 1.2）
    
    # Logging
    LOG_FILE: str = os.getenv("LOG_FILE", "dialogue_log.txt")
    
    # Web App
    WEB_APP_PORT: int = int(os.getenv("WEB_APP_PORT", "5001"))
    
    @classmethod
    def validate(cls) -> None:
        """設定の妥当性チェック"""
        if not cls.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEYが設定されていません。"
                ".envファイルまたは環境変数で設定してください。"
            )
        
        # Azure OpenAI Serviceを使用する場合の検証
        if cls.OPENAI_SERVICE_TYPE.lower() == "azure":
            if not cls.AZURE_OPENAI_ENDPOINT:
                raise ValueError(
                    "Azure OpenAI Serviceを使用する場合、AZURE_OPENAI_ENDPOINTが設定されていません。"
                    ".envファイルまたは環境変数で設定してください。"
                )
            if not cls.AZURE_OPENAI_DEPLOYMENT_NAME:
                raise ValueError(
                    "Azure OpenAI Serviceを使用する場合、AZURE_OPENAI_DEPLOYMENT_NAMEが設定されていません。"
                    ".envファイルまたは環境変数で設定してください。"
                )
        
        if not cls.VOICEVOX_BASE_URL:
            raise ValueError(
                "VOICEVOX_BASE_URLが設定されていません。"
                ".envファイルまたは環境変数で設定してください。"
            )

