import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM

app = FastAPI()

MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float32,
    device_map="cpu"
)

class PromptRequest(BaseModel):
    prompt: str

# 🔒 MUCH STRICTER INSTRUCTIONS
SYSTEM_INSTRUCTION = """
You rewrite the user's message into a short, clear email.
HARD RULES:
- Use ONLY the facts and details that appear in the user's message.
- Do NOT invent or guess times, dates, locations, activities, benefits, or extra info.
- If the user does not mention something, do NOT mention it.
- Do NOT add examples, questions, or suggestions.
- Do NOT add a subject line, title, or “Re:” line.
- Output ONLY the email body: greeting + 1–4 sentences + sign-off.
- Keep it concise and friendly.
"""

@app.post("/generate")
async def generate(req: PromptRequest):
    user_text = (req.prompt or "").strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    prompt = f"{SYSTEM_INSTRUCTION}\n\nUser message:\n{user_text}\n\nEmail:\n"

    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_new_tokens=90,   # keep it short so it doesn't ramble
        do_sample=False,     # deterministic; less weirdness
    )

    text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    email_text = text.replace(prompt, "").strip()

    return {"email": email_text}
