# Cricket Data Visualization Project

## Setup for Development

### Prerequisites
- Python 3.8+
- PostgreSQL (for local development)
- Node.js (for frontend)

### Backend Setup (cricket-data-thing)

### For Project Maintainers

1. **Standard setup:**
   ```bash
   cd cricket-viz/cricket-data-thing
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Export data for collaborators:**
   ```bash
   ./db_sync.sh export
   # Share the generated .sql.gz file with collaborators
   ```

### For Collaborators

1. **Clone and setup:**
   ```bash
   git clone <repo-url>
   cd cricket-viz/cricket-data-thing
   chmod +x db_sync.sh
   ./db_sync.sh setup
   ```

2. **Install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Get database export:**
   - Request latest database export file from project maintainer
   - Place it in the `data_exports/` directory

4. **Import data:**
   ```bash
   ./db_sync.sh import
   ```

5. **Start developing:**
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd cricket-viz  # (root directory)
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Run the frontend**
   ```bash
   npm start
   ```

## Deployment

### Heroku Deployment (Backend)
- The app is configured for Heroku deployment with `Procfile`
- Heroku automatically sets `DATABASE_URL` environment variable
- Push to Heroku using git or CLI

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (automatically set by Heroku)

## Project Structure
- `cricket-data-thing/`: FastAPI backend
- `src/`: React frontend
- `api/`: Alternative API implementation
