#!/bin/bash
# Quick deployment script for Caption Colorizer
# This script helps you deploy to Render in one command

echo "🎨 Caption Colorizer - Quick Deploy Script"
echo "=========================================="
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install git first."
    echo "   Mac: brew install git"
    echo "   Ubuntu: sudo apt-get install git"
    exit 1
fi

# Check if this is already a git repo
if [ ! -d .git ]; then
    echo "📦 Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit - Caption Colorizer"
else
    echo "✅ Git repository already initialized"
fi

# Check if remote exists
if ! git remote | grep -q "origin"; then
    echo ""
    echo "📝 Next steps:"
    echo "1. Create a new repository on GitHub:"
    echo "   https://github.com/new"
    echo ""
    echo "2. Name it: caption-colorizer"
    echo ""
    echo "3. Run these commands:"
    echo "   git remote add origin https://github.com/YOUR_USERNAME/caption-colorizer.git"
    echo "   git branch -M main"
    echo "   git push -u origin main"
    echo ""
    echo "4. Sign up for Render (free):"
    echo "   https://render.com"
    echo ""
    echo "5. Click 'New+' → 'Web Service' → Connect your GitHub repo"
    echo ""
    echo "6. Render will auto-configure everything from render.yaml"
    echo ""
    echo "7. Your app will be live in ~10 minutes! 🚀"
else
    echo "✅ Git remote already configured"
    echo ""
    echo "📤 Pushing to GitHub..."
    git add .
    git commit -m "Update Caption Colorizer" 2>/dev/null || echo "No changes to commit"
    git push origin main
    echo ""
    echo "✅ Code pushed to GitHub!"
    echo ""
    echo "🚀 Now go to https://render.com and:"
    echo "1. Click 'New+' → 'Web Service'"
    echo "2. Connect your repository"
    echo "3. Deploy! (Everything is pre-configured)"
fi

echo ""
echo "📚 Full instructions: See EASY_DEPLOY.md"
echo "💡 Local testing: python webapp_production.py"
echo ""
echo "Happy captioning! 🎨"
