from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import uvicorn
import google.generativeai as genai
import os

app = FastAPI()

# CORS: Allow frontend (e.g. Cloudflare Worker) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set your Google API Key (from Google AI Studio)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or "your-google-api-key"
genai.configure(api_key=GOOGLE_API_KEY)

# Load the Gemini 2.0 Flash model
model = genai.GenerativeModel("gemini-2.0-flash")  # or gemini-1.5-pro if needed

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        content = await file.read()
        doc = fitz.open(stream=content, filetype="pdf")
        full_text = ""
        for i, page in enumerate(doc.pages(), start=1):
            full_text += f"\n\n[Page {i}]\n" + page.get_text()
            if i >= 50:  # Optional page limit
                break
        doc.close()
        return {"status": "success", "text": full_text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/query")
async def ask_question(request: Request):
    data = await request.json()
    query = data.get("query")
    pdf_text = data.get("pdf_text", "")

    prompt = f"""You are a helpful assistant. Use only the following PDF content to answer the question.\n\nPDF Content:\n{pdf_text}\n\nQuestion: {query}"""

    try:
        response = model.generate_content(prompt)
        return {"answer": response.text}
    except Exception as e:
        return {"answer": f"❌ Error using Gemini API: {str(e)}"}

# Local run
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
