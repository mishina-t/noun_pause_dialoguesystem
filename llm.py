"""LLM（OpenAI API / Azure OpenAI Service）実装"""
import time
from openai import OpenAI, AzureOpenAI

from config import Config


class OpenAILLM:
    """OpenAI API / Azure OpenAI Serviceを使用したLLM"""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.service_type = Config.OPENAI_SERVICE_TYPE.lower()
        
        if self.service_type == "azure":
            # Azure OpenAI Serviceを使用
            if not Config.AZURE_OPENAI_ENDPOINT or not Config.AZURE_OPENAI_DEPLOYMENT_NAME:
                raise ValueError(
                    "Azure OpenAI Serviceを使用する場合、"
                    "AZURE_OPENAI_ENDPOINTとAZURE_OPENAI_DEPLOYMENT_NAMEが必要です。"
                )
            
            self.client = AzureOpenAI(
                api_key=api_key or Config.OPENAI_API_KEY,
                api_version=Config.AZURE_OPENAI_API_VERSION,
                azure_endpoint=Config.AZURE_OPENAI_ENDPOINT
            )
            # Azureではデプロイメント名をモデル名として使用
            self.model = model or Config.AZURE_OPENAI_DEPLOYMENT_NAME
        else:
            # 通常のOpenAI APIを使用
            self.client = OpenAI(api_key=api_key or Config.OPENAI_API_KEY)
            self.model = model or Config.OPENAI_MODEL
    
    
    def respond(self, user_text: str, system_prompt: str = None) -> tuple[str, float]:
        """
        ユーザーのテキストに対して応答を生成
        API呼び出しからの文章生成を行う
        
        Args:
            user_text: ユーザーの発話
            system_prompt: システムプロンプト（オプション）
            
        Returns:
            (応答テキスト, 処理時間（秒）)のタプル
            
        Raises:
            Exception: APIキーエラーやその他のエラー
        """
        start_time = time.time()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        # ユーザーの入力を追加
        # contentのところに入力が格納される
        messages.append({"role": "user", "content": user_text})
        
        try:
            # API呼び出し
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
        except Exception as e:
            # エラーメッセージを改善
            error_msg = str(e)
            if '401' in error_msg or 'invalid_api_key' in error_msg.lower() or 'incorrect api key' in error_msg.lower():
                raise ValueError(
                    "OpenAI APIキーが正しくありません。\n"
                    "1. .envファイルのOPENAI_API_KEYを確認してください\n"
                    "2. APIキーが有効か確認してください: https://platform.openai.com/account/api-keys"
                ) from e
            else:
                raise
        # 生成された文章を取得
        # strip()は文字列の両端の空白を削除する関数
        ai_text = response.choices[0].message.content.strip()
        elapsed = time.time() - start_time
        
        return ai_text, elapsed

