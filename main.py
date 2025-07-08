from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import uvicorn
import os
import uuid
from datetime import datetime
import httpx
import google.generativeai as genai

app = FastAPI()

# CORS middleware (update allow_origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or "your-google-api-key"
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# Session memory
sessions = {}

# Upload PDF route
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        content = await file.read()
        doc = fitz.open(stream=content, filetype="pdf")
        full_text = ""
        for i, page in enumerate(doc.pages(), start=1):
            full_text += f"\n\n[Page {i}]\n" + page.get_text()
            if i >= 50:
                break
        doc.close()

        # Create session
        session_id = str(uuid.uuid4())
        chat = model.start_chat(history=[])

        # Store session
        sessions[session_id] = {
            "pdf_text": full_text,
            "chat": chat
        }

        return {
            "status": "success",
            "session_id": session_id
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Ask question route
@app.post("/query")
async def ask_question(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    query = data.get("query")
    user_email = data.get("user_email", "guest")
    pdf_file_name = data.get("pdf_file_name", "Unknown")

    if session_id not in sessions:
        return {"answer": "❌ Session not found. Please upload the PDF again."}

    pdf_text = sessions[session_id]["pdf_text"]
    chat = sessions[session_id]["chat"]

    prompt = f"""Use the following PDF content to answer the question.\n\nPDF:\n{pdf_text}\n\nQuestion: {query}"""

    try:
        response = chat.send_message(prompt)
        answer = response.text
    except Exception as e:
        answer = f"❌ Error from Gemini: {str(e)}"

    # Log to external system (n8n webhook)
    log_payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_email": user_email,
        "pdf_file_name": pdf_file_name,
        "query": query,
        "answer": answer,
        "status": "answered" if not answer.startswith("❌") else "error"
    }

    try:
        await httpx.post("https://gojo3110.app.n8n.cloud/webhook/chatbot_logs", json=log_payload)
    except Exception as log_error:
        print(f"❌ Log error: {str(log_error)}")

    return {"answer": answer}

# Local dev only
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
