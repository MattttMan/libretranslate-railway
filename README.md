# LibreTranslate Deployment

This repository contains a LibreTranslate deployment for Railway.

## What is LibreTranslate?

LibreTranslate is a free and open-source machine translation API, entirely self-hosted.

## Deployment

This is configured to deploy on Railway with the following settings:

- **API Keys**: Disabled (public access)
- **Web UI**: Disabled (API only)
- **Port**: 8080
- **Host**: 0.0.0.0

## Usage

Once deployed, you can use the translation API at:

```
POST /translate
Content-Type: application/json

{
  "q": "Hello world",
  "source": "en",
  "target": "es",
  "format": "text"
}
```

## Supported Languages

LibreTranslate supports 100+ languages including:
- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Chinese (zh)
- Japanese (ja)
- Korean (ko)
- Arabic (ar)
