FROM python:3.11-slim

WORKDIR /app

# لا تبعيات خارجية: البايثون القياسي يكفي
COPY studio/server.py /app/server.py
COPY studio/static /app/static
COPY ai_builder /app/ai_builder

ENV PORT=8000
ENV HOST=0.0.0.0
ENV PLATFORM_GENERATED_DIR=/app/generated

RUN mkdir -p /app/generated /app/data

EXPOSE 8000
CMD ["python3", "server.py"]
