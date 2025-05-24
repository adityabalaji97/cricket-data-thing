#!/bin/bash

# Cricket Database Sync Helper
# Quick commands for database export/import

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPORT_DIR="$SCRIPT_DIR/data_exports"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}🏏 Cricket Database Sync Tool${NC}"
    echo "=================================="
}

export_db() {
    print_header
    echo -e "${YELLOW}📤 Exporting database from Heroku...${NC}"
    
    # Create exports directory
    mkdir -p "$EXPORT_DIR"
    
    # Generate timestamp
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    EXPORT_FILE="$EXPORT_DIR/cricket_db_dump_$TIMESTAMP.sql"
    
    # Export using pg_dump via Heroku
    echo "🔄 Running pg_dump..."
    heroku pg:backups:capture --app cricket-data-thing
    heroku pg:backups:download --app cricket-data-thing --output "$EXPORT_FILE"
    
    # Create latest symlink
    ln -sf "cricket_db_dump_$TIMESTAMP.sql" "$EXPORT_DIR/latest_dump.sql"
    
    echo -e "${GREEN}✅ Export complete: $EXPORT_FILE${NC}"
    echo "📁 Latest dump available at: $EXPORT_DIR/latest_dump.sql"
    
    # Compress for sharing
    gzip "$EXPORT_FILE"
    echo -e "${GREEN}📦 Compressed: ${EXPORT_FILE}.gz${NC}"
}

import_db() {
    print_header
    echo -e "${YELLOW}📥 Importing database to local PostgreSQL...${NC}"
    
    DUMP_FILE="$EXPORT_DIR/latest_dump.sql"
    
    if [ ! -f "$DUMP_FILE" ]; then
        echo -e "${RED}❌ No dump file found at $DUMP_FILE${NC}"
        echo "Run './db_sync.sh export' first, or specify a file with './db_sync.sh import /path/to/file.sql'"
        exit 1
    fi
    
    # Load environment variables
    if [ -f "$SCRIPT_DIR/.env" ]; then
        source "$SCRIPT_DIR/.env"
    fi
    
    # Default local database settings
    LOCAL_DB_NAME=${LOCAL_DB_NAME:-"cricket_db_local"}
    LOCAL_DB_USER=${LOCAL_DB_USER:-"postgres"}
    LOCAL_DB_HOST=${LOCAL_DB_HOST:-"localhost"}
    
    echo "🎯 Target database: $LOCAL_DB_NAME on $LOCAL_DB_HOST"
    
    # Check if database exists, create if not
    echo "🔍 Checking if database exists..."
    if ! psql -h "$LOCAL_DB_HOST" -U "$LOCAL_DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$LOCAL_DB_NAME"; then
        echo "🏗️  Creating database: $LOCAL_DB_NAME"
        createdb -h "$LOCAL_DB_HOST" -U "$LOCAL_DB_USER" "$LOCAL_DB_NAME"
    fi
    
    # Import the dump
    echo "📥 Importing data..."
    if [[ "$DUMP_FILE" == *.gz ]]; then
        gunzip -c "$DUMP_FILE" | psql -h "$LOCAL_DB_HOST" -U "$LOCAL_DB_USER" -d "$LOCAL_DB_NAME"
    else
        psql -h "$LOCAL_DB_HOST" -U "$LOCAL_DB_USER" -d "$LOCAL_DB_NAME" < "$DUMP_FILE"
    fi
    
    echo -e "${GREEN}✅ Import complete!${NC}"
    echo "🎯 Local database ready for development"
}

setup_local() {
    print_header
    echo -e "${YELLOW}🔧 Setting up local development environment...${NC}"
    
    # Create .env file if it doesn't exist
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        echo "📝 Creating .env file..."
        cat > "$SCRIPT_DIR/.env" << EOF
# Local Development Database Configuration
LOCAL_DB_NAME=cricket_db_local
LOCAL_DB_USER=postgres
LOCAL_DB_HOST=localhost
DATABASE_URL=postgresql://postgres:password@localhost:5432/cricket_db_local

# Development settings
READ_ONLY_MODE=false
DEBUG=true

# Last sync timestamp
LAST_DATA_SYNC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF
        echo -e "${GREEN}✅ Created .env file${NC}"
    else
        echo -e "${GREEN}✅ .env file already exists${NC}"
    fi
    
    # Create data exports directory
    mkdir -p "$EXPORT_DIR"
    
    echo ""
    echo -e "${BLUE}📋 Setup Instructions for Collaborators:${NC}"
    echo ""
    echo "1. 🐘 Install PostgreSQL:"
    echo "   macOS:   brew install postgresql"
    echo "   Ubuntu:  sudo apt-get install postgresql postgresql-contrib"
    echo "   Windows: Download from https://postgresql.org"
    echo ""
    echo "2. 🔑 Start PostgreSQL service:"
    echo "   macOS:   brew services start postgresql"
    echo "   Linux:   sudo systemctl start postgresql"
    echo ""
    echo "3. 📁 Get the latest database export from project maintainer"
    echo ""
    echo "4. 📥 Import the data:"
    echo "   ./db_sync.sh import"
    echo ""
    echo "5. 🚀 Start the development server:"
    echo "   uvicorn main:app --reload"
    echo ""
}

show_help() {
    print_header
    echo ""
    echo "Usage: ./db_sync.sh [command]"
    echo ""
    echo "Commands:"
    echo "  export    Export database from Heroku (maintainers only)"
    echo "  import    Import database to local PostgreSQL"
    echo "  setup     Set up local development environment"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./db_sync.sh export          # Export from Heroku"
    echo "  ./db_sync.sh import          # Import latest export"
    echo "  ./db_sync.sh setup           # First-time setup"
    echo ""
}

# Main script logic
case "${1:-help}" in
    export)
        export_db
        ;;
    import)
        import_db
        ;;
    setup)
        setup_local
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac
