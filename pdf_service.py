from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import uvicorn
import os
import uuid
import google.generativeai as genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use specific domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or "your-google-api-key"
genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel("gemini-2.0-flash")

# Store session memory and PDF text
sessions = {}

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

        # Generate session ID
        session_id = str(uuid.uuid4())

        # Create a chat session with history
        chat = model.start_chat(history=[])

        # Save session
        sessions[session_id] = {
            "pdf_text": full_text,
            "chat": chat
        }

        return {"status": "success", "session_id": session_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/query")
async def ask_question(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    query = data.get("query")

    if session_id not in sessions:
        return {"answer": "❌ Session not found. Please upload the PDF again."}

    pdf_text = sessions[session_id]["pdf_text"]
    chat = sessions[session_id]["chat"]

    prompt = f"""Use the following PDF content to answer the question.\n\nPDF:\n{pdf_text}\n\nQuestion: {query}"""

    try:
        response = chat.send_message(prompt)
        return {"answer": response.text}
    except Exception as e:
        return {"answer": f"❌ Error from Gemini: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
