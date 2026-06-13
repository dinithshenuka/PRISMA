import json
from tqdm import tqdm
import pandas as pd
from groq import Groq
import os


def build_prompt(title, abstract, config):
    inc_criteria = "\n- ".join(config.get("inclusion_criteria", []))
    exc_criteria = "\n- ".join(config.get("exclusion_criteria", []))

    prompt = f"""
You are an expert academic researcher assisting with a systematic review.
Your task is to screen the following research paper abstract based strictly on the provided criteria.

INCLUSION CRITERIA:
- {inc_criteria}

EXCLUSION CRITERIA:
- {exc_criteria}

PAPER TITLE: {title}
PAPER ABSTRACT: {abstract}

Evaluate if the paper meets ALL inclusion criteria and NO exclusion criteria. 
Respond ONLY with a valid JSON object matching this schema exactly:
{{
    "decision": "INCLUDE" or "EXCLUDE",
    "reason": "A one-sentence explanation of why it was included or excluded."
}}
"""
    return prompt


def screen_papers(df, config):
    if df.empty:
        return df

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key == "YOUR_GROQ_API_KEY_HERE":
        api_key = config.get("api_key")

    if not api_key or api_key == "YOUR_GROQ_API_KEY_HERE":
        print("ERROR: Please provide a valid Groq API Key in .env or config.yaml")
        return df

    client = Groq(api_key=api_key)
    model_name = config.get("llm_model", "llama3-8b-8192")
    print(
        f"Starting Cloud AI screening for {len(df)} papers using Groq ({model_name})..."
    )

    decisions = []
    reasons = []

    for index, row in tqdm(df.iterrows(), total=len(df)):
        prompt = build_prompt(row["title"], row["abstract"], config)

        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model_name,
                response_format={"type": "json_object"},
            )

            result = json.loads(chat_completion.choices[0].message.content)
            decisions.append(result.get("decision", "ERROR"))
            reasons.append(result.get("reason", "Parsing error"))

        except Exception as e:
            print(f"Error screening paper {index}: {e}")
            decisions.append("ERROR")
            reasons.append(str(e))

    df["ai_decision"] = decisions
    df["ai_reason"] = reasons

    return df
