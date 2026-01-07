"""NounPauseテキスト処理"""
from typing import List, Tuple
import sys
import signal

# Bus Errorをキャッチするための設定
JANOME_AVAILABLE = False
Tokenizer = None

def _safe_import_janome():
    """janomeを安全にインポート（bus error対策）
    janomeのインポートがうまくできず、bus errorが発生した
    それを防ぐためにAIでこの関数を実装した
    """
    global JANOME_AVAILABLE, Tokenizer
    
    if JANOME_AVAILABLE:
        return True
    
    try:
        # 子プロセスでインポートを試みる（bus errorを分離）
        import subprocess
        result = subprocess.run(
            [sys.executable, '-c', 'from janome.tokenizer import Tokenizer; print("OK")'],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # インポート成功した場合のみ、直接インポート
            from janome.tokenizer import Tokenizer
            JANOME_AVAILABLE = True
            return True
        else:
            print(f"警告: janomeのインポートに失敗しました（bus errorの可能性）")
            print("インストール方法: pip install janome")
            return False
    except (subprocess.TimeoutExpired, Exception) as e:
        # 直接インポートを試みる（フォールバック）
        try:
            from janome.tokenizer import Tokenizer
            JANOME_AVAILABLE = True
            return True
        except (ImportError, OSError, RuntimeError) as e:
            print(f"警告: janomeのインポートに失敗しました: {type(e).__name__}")
            print("インストール方法: pip install janome")
            # ダミークラス（エラー時に使用）
            class Tokenizer:
                def tokenize(self, text):
                    return []
            return False


class NounPauseProcessor:
    """名詞直前にポーズを挿入するテキスト処理"""
    
    def __init__(self, pause_marker: str = "、", max_pauses_per_sentence: int = 3):
        """
        Args:
            pause_marker: ポーズマーカー（テキスト方式の場合）
            max_pauses_per_sentence: 1文あたりの最大ポーズ数
        """
        # 安全にjanomeをインポート
        if not _safe_import_janome():
            raise RuntimeError(
                "janomeがインストールされていないか、bus errorが発生しています。\n"
                "対処方法:\n"
                "1. pip install janome\n"
                "2. 仮想環境を使用: python -m venv venv && source venv/bin/activate\n"
                "3. Pythonのバージョンを変更: pyenv install 3.11.0 && pyenv local 3.11.0"
            )
        self.tokenizer = Tokenizer()
        self.pause_marker = pause_marker
        self.max_pauses_per_sentence = max_pauses_per_sentence
    
    def process_text(self, text: str) -> str:
        """
        テキストに名詞前ポーズを挿入（テキスト記号方式）
        
        Args:
            text: 元のテキスト
            
        Returns:
            加工後のテキスト
        """
        # 文単位で分割（。、！、？で分割）
        
        sentences = self._split_sentences(text)
        # 加工後の文を格納するリスト
        processed_sentences = []
        
        # 各文を処理
        for sentence in sentences:
            # 文が空の場合はスキップ
            if not sentence.strip():
                processed_sentences.append(sentence)
                continue
            
            # 名詞前に句点を挿入する関数を呼び出す
            processed = self._process_sentence(sentence)
            # 加工後の文をリストに追加
            processed_sentences.append(processed)
        
        # 加工後の文を結合して返す
        return "".join(processed_sentences)
    
    def process_text_for_split(self, text: str) -> List[str]:
        """
        テキストを名詞前で分割（分割合成方式用）
        
        Args:
            text: 元のテキスト
            
        Returns:
            分割されたテキストのリスト
        """
        sentences = self._split_sentences(text)
        all_parts = []
        
        for sentence in sentences:
            if not sentence.strip():
                continue
            
            parts = self._split_sentence(sentence)
            all_parts.extend(parts)
        
        return all_parts
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        文単位で分割
        
        Args:
            text: 元のテキスト
            
        Returns:
            分割されたテキストのリスト
        """
        import re
        # 句点、感嘆符、疑問符で分割
        pattern = r'([。！？])'
        parts = re.split(pattern, text)
        # 文を格納するリスト
        sentences = []
        # 2つずつペアにして結合（文 + 句点）
        for i in range(0, len(parts) - 1, 2):
            # 2つ目の文がある場合
            if i + 1 < len(parts):
                sentences.append(parts[i] + parts[i + 1])
            else:
                sentences.append(parts[i])
        if len(parts) % 2 == 1:
            sentences.append(parts[-1])
        return sentences
    
    def _process_sentence(self, sentence: str) -> str:
        """
        1文を処理（テキスト記号方式）
        
        Args:
            sentence: 元のテキスト
            
        Returns:
            加工後のテキスト
        """
        # 形態素解析
        tokens = list(self.tokenizer.tokenize(sentence))
        # 加工後の文を格納するリスト
        # 初期化
        result = []
        pause_count = 0
        last_was_noun = False
        
        for i, token in enumerate(tokens):
            # 名詞を検出
            # 名詞だとTrueになる
            is_noun = token.part_of_speech.startswith("名詞")
            
            # 連続する名詞は最初の1つだけにポーズ
            if is_noun and not last_was_noun and pause_count < self.max_pauses_per_sentence:
                result.append(self.pause_marker)
                pause_count += 1
                last_was_noun = True
            else:
                last_was_noun = is_noun
            
            result.append(token.surface)
        
        # 加工後の文を結合して返す
        return "".join(result)
    
    def _split_sentence(self, sentence: str) -> List[str]:
        """
        1文を名詞前で分割（分割合成方式）
        
        Args:
            sentence: 元のテキスト
            
        Returns:
            分割されたテキストのリスト
        """
        tokens = list(self.tokenizer.tokenize(sentence))
        parts = []
        current_part = []
        pause_count = 0
        last_was_noun = False
        
        for token in tokens:
            is_noun = token.part_of_speech.startswith("名詞")
            
            # 名詞の直前で分割
            if is_noun and not last_was_noun and pause_count < self.max_pauses_per_sentence:
                if current_part:
                    parts.append("".join(current_part))
                    current_part = []
                pause_count += 1
                last_was_noun = True
            else:
                last_was_noun = is_noun
            
            current_part.append(token.surface)
        
        if current_part:
            parts.append("".join(current_part))
        
        return parts if parts else [sentence]

