# LEO-Chat (Law Enforcement Operations Chat)

A secure, local intelligence tool that enables law enforcement personnel to efficiently query and analyze press releases from the U.S. Attorney's Office (Central District of California)—fully on their local machine.

## Deployment Options

### Option 1: Docker (Recommended)
1. **Prerequisites**
   - Docker installed

2. **Clone the repository**
  - `git clone https://github.com/bo-bits/leo-chat.git`
  - `cd leo-chat`

3. **Build and start the containers**
  - `docker-compose up --build`

### Option 2: Manual Setup

1. **Prerequisites**
   - Docker installed
   - Python 3.11+
   - MongoDB installed and running locally

2. **Setup**
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Run the application
   streamlit run src/ui/Hello.py
   ```

## Basic Usage
1. **Initial Data Load**
   - Go to the Library page
   - Click "Scrape Articles" to fetch USAO press releases
   - (COMING SOON) Use "Upload Local Files" to add your own documents

2. **Search**
   - Enter your query in the search box
   - View results sorted by relevance
   - Click article links to read full text


## Security Note

This tool runs entirely locally:
- No external API calls
- All processing happens on your machine
- Follow your organization's security policies

## Support

For issues:
1. Check existing GitHub issues
2. Create new issue with:
   - Description
   - Steps to reproduce
   - System information

## License

[Your chosen license]