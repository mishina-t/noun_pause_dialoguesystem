# 対話システム実装備忘録_mishina
コードの内容を説明するためのものではあんまりない

http://localhost:5001 

python web_app.pyを実行

音声認識と統合させた時のおおまかな流れを理解する
プロンプト制御のやり方を学ぶ

ポイント
- API呼び出しから文章生成の流れ
- voice voxどこで使ってるか、TTSの実装
- 句読点挿入のロジック

全体像
> ユーザーの入力テキスト  
>     ↓  
> OpenAI API / Azure OpenAI API に送信  
>     ↓  
> LLM（大規模言語モデル）が文章を生成  
>     ↓  
> 生成された文章を返す  

ファイル
1. main.py - 
2. llm.py - 文章生成
3. text_processor.py - 名詞前に読点を入れる
4. tts.py - voicevoxを用いた音声合成
5. config.py - 設定管理
6. .env - 環境変数
7. ui.py - UI表示

前提
- UI関連(HTML)はAIに任せたので理解できていない、今後改善したい
- 型を作ってみてそれをAIに繋げてもらったイメージ
- コピペばかりなので出典を整理して、それぞれ理解する
- CSは初学者のため何で動いているか、安全かどうかは無視している(勉強中)


# API呼び出しから文章生成
---
- llm.pyのrespond関数で呼び出している
- システムプロンプトはここで追記できるらしい

```python
def respond(self, user_text: str) -> tuple[str, float]:
    """
    ユーザーのテキストに対して応答を生成
    
    Args:
        user_text: ユーザーの発話（例: "今日は何をしますか？"）
    """
    # ステップ1: メッセージリストを準備
    messages = []
    # ユーザーの入力を追加
    messages.append({"role": "user", "content": user_text})
    # → messages = [
    #     {"role": "user", "content": "今日は何をしますか？"}
    # ]
    
    # ステップ2: OpenAI APIを呼び出し
    response = self.client.chat.completions.create(
        model=self.model,           # 使用するモデル（例: "gpt-4o-mini"）
        messages=messages,          # 上で準備したメッセージリスト
        temperature=0.7,            # 応答のランダム性（0.0〜1.0）
        max_tokens=500              # 最大トークン数（応答の長さの上限）
    )
    
    # ステップ3: 生成された文章を取得
    
    ai_text = response.choices[0].message.content.strip()
    # → ai_text = "今日は天気がいいので、散歩に行く予定です。"
    
    return ai_text, elapsed
```

`response = self.client.chat.completions.create(...)`
でAPI呼び出しが大事らしい

ポイント(llm.py)
- 

# TTSの実装
---
- VOICEVOXという日本語のTTSエンジンを使用
	- テキストをWAVに変換する
	- Pythonのrequestsライブラリが必要

主な使用点(tts.py)
- audio_query
- synthesis
- 渡したいURL/〇〇で機能を利用できる
- `/audio_query`で音声合成用のクエリを取得し、テキストがJSONに変換、その結果を`/synthesis`にPOSTすることでwavファイルを取得

注意点
- VOICEVOXのサーバー起動：  
	- VOICEVOXのサーバーがローカルで起動している必要がある。サーバーが起動していない場合、APIにアクセスできない。
- pyaudioはできなかった


読んだ記事
- [Python経由でVoiceVoxの音声ファイルを作成する方法](https://zenn.dev/zenn24yykiitos/articles/fff3c954ddf42c)
- [Whisper API, ChatGPT API, VOICEVOXを使ってAIと会話する](https://zenn.dev/umyomyomyon/articles/5f07abe67a289b)
	- わかりやすい
- [APIの詳しい仕様](https://platform.openai.com/docs/guides/text)
	- いずれちゃんと読んだ方がいいかも



# 句読点挿入のロジック
---

秒数指定でポーズを開けるのは分からなかった
名詞を抽出してその前に句点を入れた

全体像
> 生成された文章
>     ↓
> 文単位に分割（。！？で分割）
>     ↓
> 各文を形態素解析（単語に分解）
>     ↓
> 名詞を検出
>     ↓
> 名詞の直前に「、」を挿入
>     ↓
> 処理済みの文章

```python
def __init__(self, pause_marker: str = "、", max_pauses_per_sentence: int = 3):
    self.pause_marker = pause_marker
```


ポイント
- janomeのTokenizerを使用
	- janomeの方が簡単で速いと勘違いしていたが普通にMecabの方が早いらしい
	- 今後の手法検討も兼ねて再実装したい
- pause_markerを __ init __ でデフォルト引数で読点として指定 & 一文のmax読点数も指定 → `_process_sentence`関数で呼び出している
- 名詞が連続しているところに過度にポーズが入らないよう、この関数で`last_was_noun`で防いでいる

```text
前が名詞だったか = False
読点回数 = 0
結果 = 空

単語を左から順に1個ずつ見る:
    もし 今が名詞 かつ 前が名詞じゃない かつ 読点回数が上限未満:
        結果に「、」を追加
        読点回数を+1

    結果に単語を追加
    「前が名詞だったか」を今の単語に合わせて更新
```


# 疑問
---
- 実行環境とは
