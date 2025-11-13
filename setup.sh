#!/bin/bash

echo "🎵 Vibeflow Setup Script"
echo "======================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

echo "✓ Node.js version: $(node --version)"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✓ Dependencies installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f backend/.env ]; then
    echo "📝 Creating backend/.env file..."
    cp backend/.env.example backend/.env
    echo "✓ Created backend/.env"
    echo ""
    echo "⚠️  IMPORTANT: Edit backend/.env and add your API credentials:"
    echo "   - Spotify Client ID and Secret"
    echo "   - Tidal Client ID and Secret"
    echo "   - Change the SESSION_SECRET to a random string"
    echo ""
else
    echo "✓ backend/.env already exists"
    echo ""
fi

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit backend/.env with your API credentials"
echo "2. Run 'npm run dev' to start the application"
echo ""
