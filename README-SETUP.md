# Cricket Data Visualization Project

## Setup for Development

### Prerequisites
- Python 3.8+
- PostgreSQL (for local development)
- Node.js (for frontend)

### Backend Setup (cricket-data-thing)

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd cricket-viz/cricket-data-thing
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your local database credentials
   ```

5. **Database Setup**
   ```bash
   # Create local PostgreSQL database
   createdb cricket_db
   # The app will automatically create tables on first run
   ```

6. **Run the backend**
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
