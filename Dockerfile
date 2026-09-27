# HF Spaces (Docker): bake the RAG store into the image at build time.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt
COPY . .
# Build the vector store now so the running Space needs no rebuild.
RUN python build_all.py

ENV PORT=7860
EXPOSE 7860
# GROQ_API_KEY comes from the Space's Secrets settings (never in the image).
CMD ["python", "app.py"]
