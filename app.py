import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM

app = FastAPI()

# Small, fully open chat model
MODEL_ID = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

print("Loading model:", MODEL_ID)
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float32,
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

    prompt = (
        "Write a clear, short, friendly email based on the description below.\n"
        "Do not explain what you're doing. Only output the email body.\n\n"
        f"Description:\n{user_description}\n\nEmail:\n"
    )

    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_new_tokens=200,
        temperature=0.7,
        do_sample=True,
        top_p=0.9,
    )

    text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    email_text = text.replace(prompt, "").strip()

    return {"email": email_text}
