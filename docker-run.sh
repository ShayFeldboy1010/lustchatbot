# Build and test Docker image locally

# Build the image
docker build -t lustbot .

# Run the container
docker run -p 8000:8000 --env-file .env lustbot

# Or run with environment variables
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  -e PINECONE_API_KEY=your-key \
  -e PINECONE_ENVIRONMENT=us-east-1-aws \
  -e PINECONE_INDEX_NAME=lust-products \
  -e GOOGLE_SHEETS_SPREADSHEET_ID=your-sheet-id \
  lustbot
