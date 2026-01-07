"""UI表示モジュール"""
import os
from typing import Literal, Optional

Status = Literal["IDLE", "REC", "STT", "GEN", "SPEAK"]
Mode = Literal["normal", "nounpause"]


class ConsoleUI:
    """コンソール全画面風UI"""
    
    def __init__(self):
        self.clear_screen()
    
    def clear_screen(self):
        """画面をクリア"""
        os.system("clear" if os.name != "nt" else "cls")
    
    def render(
        self,
        user_text: str = "",
        ai_text: str = "",
        processed_text: str = "",
        status: Status = "IDLE",
        mode: Mode = "normal"
    ):
        """
        画面を描画
        
        Args:
            user_text: ユーザー発話
            ai_text: AI応答（元）
            processed_text: 加工後テキスト（NounPause時）
            status: 現在の状態
            mode: 現在のモード
        """
        self.clear_screen()
        
        # ヘッダー
        print("=" * 80)
        print(" " * 30 + "NounPause Voice Assistant")
        print("=" * 80)
        print()
        
        # USERセクション
        print("[USER]")
        print("-" * 80)
        if user_text:
            print(f"  {user_text}")
        else:
            print("  (待機中...)")
        print()
        
        # AIセクション
        print("[AI]")
        print("-" * 80)
        if ai_text:
            print(f"  {ai_text}")
        else:
            print("  (待機中...)")
        print()
        
        # AI (processed)セクション（NounPause時のみ）
        if mode == "nounpause":
            print("[AI - processed]")
            print("-" * 80)
            if processed_text:
                print(f"  {processed_text}")
            else:
                print("  (待機中...)")
            print()
        
        # ステータスとモード
        print("-" * 80)
        status_display = {
            "IDLE": "待機中",
            "REC": "録音中",
            "STT": "文字起こし中",
            "GEN": "応答生成中",
            "SPEAK": "音声再生中"
        }
        mode_display = {
            "normal": "Normal",
            "nounpause": "NounPause"
        }
        
        print(f"Status: {status_display.get(status, status)}  |  Mode: {mode_display.get(mode, mode)}")
        print()
        print("=" * 80)
        print("操作: [Enter] 録音開始/停止  |  [M] モード切替  |  [Q] 終了")
        print("=" * 80)

