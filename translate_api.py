from fastapi import FastAPI
import requests
import uvicorn

app = FastAPI()

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
        
        # Use LibreTranslate public API as fallback
        libre_url = "https://libretranslate.com/translate"
        libre_data = {
            "q": text,
            "source": source,
            "target": target,
            "format": "text"
        }
        
        response = requests.post(libre_url, json=libre_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return {
                "translatedText": result.get("translatedText", text),
                "detectedLanguage": source
            }
        else:
            # Fallback to MyMemory API
            mymemory_url = "https://api.mymemory.translated.net/get"
            mymemory_params = {
                "q": text,
                "langpair": f"{source}|{target}"
            }
            
            response = requests.get(mymemory_url, params=mymemory_params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                translated_text = result.get("responseData", {}).get("translatedText", text)
                return {
                    "translatedText": translated_text,
                    "detectedLanguage": source
                }
            else:
                return {"error": "Translation services unavailable"}
                
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
