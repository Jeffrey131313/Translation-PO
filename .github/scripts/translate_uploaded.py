import os
import polib
from openai import OpenAI
import json
import textwrap

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://api.siliconflow.cn/v1"
)

MODEL = "Qwen/Qwen3-235B-A22B"
BATCH_SIZE = 10

def translate_batch(texts):
    input_data = {f"line_{i}": text for i, text in enumerate(texts)}

    prompt = textwrap.dedent(f"""\ 
        请勿进行思考，直接翻译以下英文字符串为**简体中文**，并且仅以**JSON格式**返回结果。

        ⚠️ 注意事项：
        - 所有内容必须翻译为简体中文，**不得保留英文原文**，也**不得返回与原文意思相近的英文**。
        - 所有文本均为一款**科幻题材的电子游戏**中的界面文本或游戏内提示，请保持科幻氛围。
        - 输出必须是一个 JSON 对象，每一项对应翻译结果，不要包含额外说明或格式之外的内容。
        
        Input:
        {json.dumps(input_data, ensure_ascii=False, indent=2)}

        Output format:
        {{
          "line_0": "...",
          "line_1": "...",
          ...
        }}
    """)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a translation assistant. Only return JSON output."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return [result.get(f"line_{i}", texts[i]) for i in range(len(texts))]
    except Exception as e:
        print("Translation error:", e)
        return texts

input_dir = "uploaded"
print(os.listdir(input_dir))
for file in os.listdir(input_dir):
    if file.endswith(".txt"):
        path = os.path.join(input_dir, file)
        po = polib.pofile(path)
        entries = [e for e in po if e.msgid and not e.msgstr]

        for i in range(0, len(entries), BATCH_SIZE):
            batch = entries[i:i + BATCH_SIZE]
            texts = [e.msgid for e in batch]
            translations = translate_batch(texts)

            for e, t in zip(batch, translations):
                e.msgstr = t
                print(f"{e.msgid} => {t}")

        po.save(path)
        print(f"✔ Saved translated file: {path}")
