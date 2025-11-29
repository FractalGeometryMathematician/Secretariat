import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM

app = FastAPI()

# Stronger but still small, fully open chat model
MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

print("Loading model:", MODEL_ID)
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float32,   # keep CPU-friendly
    device_map="cpu"
)
print("Model loaded.")


class PromptRequest(BaseModel):
    prompt: str


@app.post("/generate")
async def generate(req: PromptRequest):
    user_description = (req.prompt or "").strip()
    if not user_description:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    # Much stricter instructions: no subject, no extra info
    prompt = (
        "You are an email-drafting assistant.\n"
        "Write a short, concise email BODY only.\n"
        "- Do NOT add a subject line or greeting like 'Subject:'\n"
        "- Do NOT invent extra details (time, place, food, etc.)\n"
        "- Only use the information given in the description.\n"
        "- Keep it 3–6 sentences.\n\n"
        f"Description:\n{user_description}\n\n"
        "Email body:\n"
    )

    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_new_tokens=160,   # enough for a short email
        temperature=0.4,      # lower temperature → less hallucination
        top_p=0.9,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
    )

    full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Strip the prompt back off if it's echoed
    if full_text.startswith(prompt):
        email_text = full_text[len(prompt):].strip()
    else:
        email_text = full_text.strip()

    return {"email": email_text}
