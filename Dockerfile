# Use the official Python slim image.
FROM python:3.12-slim

# Set environment variables to ensure Python output is sent straight to terminal
# and to prevent Python from writing .pyc files.
ENV PYTHONUNBUFFERED=True
ENV PYTHONDONTWRITEBYTECODE=True

# Set the working directory in the container.
WORKDIR /app

# Copy the requirements file first to leverage Docker cache.
COPY requirements.txt .

# Install dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and the law library.
COPY . .

# Expose the port used by Cloud Run (default is 8080).
EXPOSE 8080

# Run Streamlit.
# We bind to 0.0.0.0 and use the PORT environment variable provided by Cloud Run.
CMD streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false
