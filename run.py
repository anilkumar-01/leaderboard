# run.py - Script to run the application or setup database
import sys
import uvicorn
from pathlib import Path

# Add the project directory to the Python path
root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir))

def setup_database():
    """Run database setup script"""
    try:
        from scripts.db_setup import setup_database, add_indexes
        
        print("Setting up database...")
        setup_database()
        add_indexes()
        print("Database setup completed successfully!")
    except Exception as e:
        print(f"Error setting up database: {e}")
        sys.exit(1)

def run_server():
    """Run the FastAPI server"""
    print("Starting server...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "setup-db":
            setup_database()
        elif sys.argv[1] == "run":
            run_server()
        else:
            print("Unknown command. Use 'setup-db' or 'run'")
    else:
        print("Usage: python run.py [setup-db|run]")
        print("  setup-db: Initialize the database")
        print("  run: Start the API server")