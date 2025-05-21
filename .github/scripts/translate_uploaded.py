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
        不要思考: Please translate the following English strings into Simplified Chinese, and respond only in JSON format.
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
