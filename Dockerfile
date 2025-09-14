# Use the official LibreTranslate Docker image
FROM libretranslate/libretranslate:latest

# Set environment variables for production
ENV LT_API_KEYS=false
ENV LT_DISABLE_WEB_UI=true
ENV LT_HOST=0.0.0.0
ENV LT_PORT=8080

# Expose the port
EXPOSE 8080

# The LibreTranslate image already has the correct CMD
# No need to override it
