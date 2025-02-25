# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Ensure we're using pymongo's bson, not the standalone package
RUN pip uninstall -y bson

# Copy the current directory contents into the container
COPY . .

# Create necessary directories
RUN mkdir -p data/models

# Expose the port the app runs on
EXPOSE 8501

# Update the config to use the MongoDB container
RUN sed -i 's/mongodb:\/\/localhost:27017/mongodb:\/\/mongo:27017/g' config/config.py

# Run the Streamlit app
CMD ["streamlit", "run", "src/ui/Hello.py"]
