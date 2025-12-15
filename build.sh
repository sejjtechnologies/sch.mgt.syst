#!/bin/bash
# Custom build script for Vercel to avoid pip root warnings

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Deactivate virtual environment
deactivate

echo "Build completed successfully"