# pdf_service.py
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import uvicorn

app = FastAPI()

# Allow Cloudflare frontend to access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this to your domain
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        content = await file.read()
        doc = fitz.open(stream=content, filetype="pdf")
        full_text = ""
        for i, page in enumerate(doc.pages(), start=1):
            full_text += f"\n\n[Page {i}]\n" + page.get_text()
            if i >= 50:  # Limit to 50 pages
                break
        doc.close()
        return { "status": "success", "text": full_text }
    except Exception as e:
        return { "status": "error", "message": str(e) }

# For local testing
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
