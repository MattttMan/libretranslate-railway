from fastapi import FastAPI
from googletrans import Translator
import uvicorn

app = FastAPI()
translator = Translator()

@app.get("/")
async def root():
    return {"message": "Lightweight Translation API", "status": "running"}

@app.post("/translate")
async def translate_text(data: dict):
    try:
        text = data.get("q", "")
        source = data.get("source", "auto")
        target = data.get("target", "en")
        
        if not text:
            return {"error": "No text provided"}
        
        # Translate using Google Translate (free)
        result = translator.translate(text, src=source, dest=target)
        
        return {
            "translatedText": result.text,
            "detectedLanguage": result.src if source == "auto" else source
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
