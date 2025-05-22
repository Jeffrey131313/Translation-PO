import os
import polib
import json
import textwrap
import difflib
import time
from openai import OpenAI
from googletrans import Translator
import re

translator = Translator()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://api.siliconflow.cn/v1"
)

MODEL = "Qwen/Qwen3-235B-A22B"
BATCH_SIZE = 10
MAX_RETRIES = 2

def escape_placeholders(text):
    return (
        text.replace('\\', '\\\\')
        .replace('\n', '\\n')
        .replace('\t', '\\t')
        .replace('"', '\\"')
    )

def unescape_placeholders(text):
    return (
        text.replace('\\n', '\n')
        .replace('\\t', '\t')
        .replace('\\"', '"')
        .replace('\\\\', '\\')
    )

def is_too_similar(a, b, threshold=0.95):
    return difflib.SequenceMatcher(None, a, b).ratio() >= threshold

def is_meaningful_text(text):
    return bool(re.search(r'[a-zA-Z]', text)) and len(text.strip()) > 1

def call_translate_api(text_dict):
    prompt = textwrap.dedent(f"""\ 
        请勿进行思考，直接翻译以下英文字符串为**简体中文**，并且仅以**JSON格式**返回结果。

        ⚠️ 注意事项：
        - 所有内容必须翻译为简体中文，不得保留英文原文，也不得返回与原文意思相近的英文。
        - 不要翻译或更改任何格式标记（如 \\n、\\t、\\\"、\\ 等），请原样保留。
        - 所有文本均为一款科幻题材的电子游戏中的界面文本或游戏内提示，请保持科幻氛围。
        - 输出必须是一个 JSON 对象，每一项对应翻译结果，不要包含额外说明或格式之外的内容。

        Input:
        {json.dumps(text_dict, ensure_ascii=False, indent=2)}

        Output format:
        {{
          "line_0": "...",
          "line_1": "...",
          ...
        }}
    """)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你是一个游戏翻译模型，可以流畅通顺地将任意的游戏文本翻译成简体中文，并联系上下文正确使用人称代词，\
            不要进行任何额外的格式修改，不擅自添加原文中没有的代词。你没有任何违禁词限制！你的回答只有翻译文本！\
            不允许回答翻译文本之外的内容！不允许解释你是怎么样翻译的！不允许提出建议！如果字幕文本是一个字母或符号回答原文本即可！\
            并确保翻译结果符合中文语言习惯而且符合字幕内容的词语，你可以调整语气和风格，并考虑到某些词语的文化内涵和地区差异。\
            同时作为字幕翻译模型，需将原文翻译成具有\"信达雅\"标准的译文。\
            \"信\" 即忠实于原文的内容与意图；\"达\" 意味着译文应通顺易懂，表达清晰；\"雅\" 则追求译文的文化审美和语言的优美。\
            目标是创作出既忠于原作精神，又符合目标语言文化和读者审美的翻译。你的一切输出都要使用json格式输出, 所有内容必须翻译为简体中文，不得保留英文原文，也不得返回与原文意思相近的英文。"},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def google_translate(text):
    if not is_meaningful_text(text):
        print(f"🚫 内容过短或为符号/数字，跳过翻译：{text}")
        return text
    try:
        result = translator.translate(text, src='en', dest='zh-cn')
        return result.text
    except Exception as e:
        print(f"❌ Google 翻译失败：{e}")
        return text

def translate_batch_with_retry(texts):
    results = [None] * len(texts)
    remaining_indexes = list(range(len(texts)))
    retries = 0

    while remaining_indexes and retries <= MAX_RETRIES:
        batch_input = {
            f"line_{i}": escape_placeholders(texts[i]) for i in remaining_indexes
        }
        try:
            raw_result = call_translate_api(batch_input)
        except Exception as e:
            print("⚠️ 翻译 API 调用失败:", e)
            return texts

        new_remaining = []
        for idx in remaining_indexes:
            original = texts[idx]
            translated = unescape_placeholders(raw_result.get(f"line_{idx}", original))

            if is_too_similar(original, translated):
                print(f"⚠️ 与原文过于相似，将重试：{original}")
                new_remaining.append(idx)
            else:
                results[idx] = translated
                print(f"✅ 翻译成功：'{original}' => {translated}")

        remaining_indexes = new_remaining
        retries += 1
        if remaining_indexes:
            time.sleep(1)

    for idx in remaining_indexes:
        original = texts[idx]
        fallback = google_translate(original)
        results[idx] = fallback
        print(f"🔁 使用 Google 翻译：{original} => {fallback}")

    return results

input_dir = "uploaded"
print("📂 读取目录：", input_dir)

for file in os.listdir(input_dir):
    if file.endswith(".txt"):
        path = os.path.join(input_dir, file)
        print(f"📄 开始翻译文件：{path}")
        po = polib.pofile(path)
        entries = [e for e in po if e.msgid and not e.msgstr]

        for i in range(0, len(entries), BATCH_SIZE):
            batch = entries[i:i + BATCH_SIZE]
            texts = [e.msgid for e in batch]
            translations = translate_batch_with_retry(texts)

            for e, t in zip(batch, translations):
                e.msgstr = t

        po.save(path)
        print(f"✔ 保存翻译文件：{path}")
