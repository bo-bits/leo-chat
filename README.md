# LEO-Chat (Law Enforcement Operations Chat)

A secure, local intelligence tool that enables law enforcement personnel to efficiently query and analyze press releases from the U.S. Attorney's Office (Central District of California)—fully on their local machine.

## Overview

LEO-Chat uses semantic search and local processing to help law enforcement personnel quickly find relevant information in press releases and case documents. The system operates entirely offline, ensuring data security and privacy.

## Features

- **Semantic Search**: Find relevant documents based on meaning, not just keywords
- **Multiple Data Sources**: Search across USAO press releases and other supported sources
- **Local Processing**: All data processing and search happens on your machine
- **Document Upload**: Support for PDF, DOCX, and TXT files
- **Configurable Search**: Adjust relevance scores and number of results
- **Secure**: No external API calls or data transmission

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run src/ui/app.py
```

## Dependencies

- Python 3.11+
- Streamlit
- Sentence-Transformers
- FAISS
- PyPDF2
- python-docx
- BeautifulSoup4
- See `requirements.txt` for full list

## Project Structure

```
leo_chat/
├── src/
│   ├── scraping/          # Web scraping and document ingestion
│   ├── processing/        # Text processing and chunking
│   ├── indexing/          # Vector embeddings and FAISS indexing
│   ├── retrieval/         # Semantic search functionality
│   └── ui/               # Streamlit user interface
├── data/                 # Local data storage
│   ├── articles/         # Raw article storage
│   ├── chunks/           # Processed text chunks
│   ├── embeddings/       # Vector embeddings
│   └── models/          # Local ML models
├── config/              # Configuration files
└── tests/              # Test suite
```

## Architecture

### 1. Data Ingestion
- Web scraping of USAO press releases
- Local file ingestion (PDF, DOCX, TXT)
- Data cleaning and validation

### 2. Text Processing
- Document chunking with overlap
- Metadata extraction
- Text normalization

### 3. Vector Search
- Sentence transformer embeddings
- FAISS similarity search
- Source-specific filtering

### 4. User Interface
- Streamlit-based web interface
- Real-time search results
- Configurable search parameters

## Usage

### Basic Search
1. Enter your query in the search box
2. Press Enter or click "Search"
3. View results with relevance scores

### Advanced Features
- **Adjust Results**: Use sidebar sliders to modify:
  - Number of results (1-10)
  - Minimum relevance score (0.0-1.0)
- **Source Selection**: Enable/disable specific data sources
- **File Upload**: Add local documents to the search index
- **Example Questions**: Click pre-written queries for quick searches

### Document Upload
1. Use the sidebar's "Upload Local Files" section
2. Select one or more supported files
3. Click "Reprocess Database" after upload
4. Wait for indexing to complete

## Security

This tool is designed to run entirely locally. No data is sent to external services, making it suitable for handling sensitive information. However, users should follow their organization's security policies when handling case-related documents.

Key security features:
- Offline operation
- Local model inference
- No external API calls
- Temporary file cleanup
- Source data validation

## Maintenance

### Reset Database
To clear all indexed data:

## Usage

### Basic Search
1. Enter your query in the search box
2. Press Enter or click "Search"
3. View results with relevance scores

### Advanced Features
- **Adjust Results**: Use sidebar sliders to modify:
  - Number of results (1-10)
  - Minimum relevance score (0.0-1.0)
- **Source Selection**: Enable/disable specific data sources
- **File Upload**: Add local documents to the search index
- **Example Questions**: Click pre-written queries for quick searches

### Document Upload
1. Use the sidebar's "Upload Local Files" section
2. Select one or more supported files
3. Click "Reprocess Database" after upload
4. Wait for indexing to complete

## Security

This tool is designed to run entirely locally. No data is sent to external services, making it suitable for handling sensitive information. However, users should follow their organization's security policies when handling case-related documents.

Key security features:
- Offline operation
- Local model inference
- No external API calls
- Temporary file cleanup
- Source data validation

## Maintenance

### Reset Database
To clear all indexed data:
```bash
python src/reset_db.py
```

### Update Source Data
To refresh press releases:
```bash
python src/scraping/scraper.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Your chosen license]

## Troubleshooting

### Common Issues
1. **Initialization Error**: Check if all required directories exist
2. **Search Not Working**: Ensure the FAISS index is properly built
3. **File Upload Fails**: Verify file format and permissions

### Logs
- Check the application logs for detailed error messages
- Log files are stored in the `data` directory

## Support

For issues or feature requests:
1. Check existing GitHub issues
2. Create a new issue with:
   - Detailed description
   - Steps to reproduce
   - System information