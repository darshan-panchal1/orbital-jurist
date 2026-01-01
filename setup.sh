#!/bin/bash

# Setup script for Orbital Jurist
# This script sets up the complete environment

echo "=================================================="
echo "  Orbital Jurist Setup"
echo "=================================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.9+ required (found Python $python_version)"
    exit 1
fi
echo "✓ Python $python_version detected"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists"
    read -p "Remove and recreate? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        python3 -m venv venv
        echo "✓ Virtual environment recreated"
    fi
else
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create necessary directories
echo "Creating project directories..."
mkdir -p data
mkdir -p results
mkdir -p logs
echo "✓ Directories created"
echo ""

# Create __init__.py files
echo "Creating Python package files..."
touch agents/__init__.py
touch mcp_servers/__init__.py
touch workflow/__init__.py
touch utils/__init__.py
echo "✓ Package files created"
echo ""

# Setup environment variables
echo "Setting up environment variables..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Created .env file from template"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your GROQ_API_KEY"
    echo ""
    read -p "Do you have a Groq API key ready? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your Groq API key: " groq_key
        sed -i "s/your_groq_api_key_here/$groq_key/" .env
        echo "✓ Groq API key configured"
    else
        echo ""
        echo "📝 Get your Groq API key from: https://console.groq.com/"
        echo "   Then edit .env and replace 'your_groq_api_key_here' with your key"
    fi
else
    echo "⚠️  .env file already exists (not overwriting)"
fi
echo ""

# Test imports
echo "Testing imports..."
python3 -c "
import sys
try:
    from config import settings
    from utils.groq_client import GroqClient
    from utils.data_loader import CelesTrakClient, LegalDatabase
    print('✓ All imports successful')
except Exception as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"
echo ""

# Initialize legal database
echo "Initializing legal database..."
python3 -c "
from utils.data_loader import LegalDatabase
db = LegalDatabase()
print(f'✓ Legal database initialized with {len(db.precedents)} precedents')
"
echo ""

echo "=================================================="
echo "  Setup Complete! 🎉"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Activate environment: source venv/bin/activate"
echo "  2. Configure .env with your GROQ_API_KEY"
echo "  3. Run a test: python run_analysis.py --obj1 25544 --obj2 99999"
echo "  4. Start API server: python main.py"
echo ""
echo "Documentation: See README.md"
echo "=================================================="