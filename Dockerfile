# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install MongoDB
RUN apt-get update && apt-get install -y gnupg wget
RUN wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | apt-key add -
RUN echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list
RUN apt-get update && apt-get install -y mongodb-org

# Create directory for MongoDB data
RUN mkdir -p /data/db

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . .

# Create necessary directories
RUN mkdir -p data/models

# Expose the port the app runs on
EXPOSE 8501

# Create a startup script
RUN echo '#!/bin/bash\n\
# Start MongoDB in the background\n\
mongod --fork --logpath /var/log/mongodb.log\n\
\n\
# Run the Streamlit app\n\
streamlit run src/ui/Hello.py\n\
' > /app/start.sh

RUN chmod +x /app/start.sh

# Run the startup script when the container launches
CMD ["/app/start.sh"]
