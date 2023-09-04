FROM python:3.10.13

# Path: /app
WORKDIR /app

# Copy requirements.txt
COPY requirements.txt ./requirements.txt

# Install requirements
RUN pip install -r requirements.txt

# Copy the rest of the files
COPY . /app

EXPOSE 8090

# Run the app
CMD ["python", "/app/application.py"]
