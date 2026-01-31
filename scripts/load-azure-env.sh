#!/bin/bash

# Bash Script to Load Azure Environment Variables
# This script loads your Azure Developer CLI environment variables every time you develop locally
# Usage: source ./scripts/load-azure-env.sh
# Then: $AZURE_SEARCH_SERVICE, etc. will be available in your current shell

# Set error handling
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================"
echo "Azure Environment Loader"
echo -e "========================================${NC}"

# Step 1: Check if azd is installed
echo -e "${YELLOW}[1/3]${NC} Checking if Azure Developer CLI (azd) is installed..."
if ! command -v azd &> /dev/null; then
    echo -e "${RED}✗${NC} Azure Developer CLI not found. Please install it from: https://aka.ms/azd/install"
    return 1
fi

azd_version=$(azd version 2>/dev/null || echo "unknown")
echo -e "${GREEN}✓${NC} Azure Developer CLI found: $azd_version"

# Step 2: Get the default azd environment
echo -e "${YELLOW}[2/3]${NC} Loading default Azure Developer CLI environment..."

env_json=$(azd env list -o json 2>/dev/null)
if [ -z "$env_json" ]; then
    echo -e "${RED}✗${NC} Failed to retrieve Azure Developer CLI environments"
    echo "Run 'azd env new' or 'azd env select' first."
    return 1
fi

# Parse JSON to find default environment
env_name=$(echo "$env_json" | grep -o '"Name":"[^"]*","IsDefault":true' | head -1 | cut -d'"' -f4)
dot_env_path=$(echo "$env_json" | grep -o '"DotEnvPath":"[^"]*"' | grep -B1 '"IsDefault":true' | head -1 | cut -d'"' -f4)

if [ -z "$env_name" ]; then
    echo -e "${RED}✗${NC} No default Azure Developer CLI environment found."
    echo "Run 'azd env new' or 'azd env select' first."
    return 1
fi

echo -e "${GREEN}✓${NC} Found environment: ${GREEN}$env_name${NC}"
echo -e "${GREEN}✓${NC} Loading from: $dot_env_path"

# Step 3: Load environment variables from .env file
echo -e "${YELLOW}[3/3]${NC} Loading environment variables..."

if [ ! -f "$dot_env_path" ]; then
    echo -e "${RED}✗${NC} Environment file not found at: $dot_env_path"
    return 1
fi

# Load the .env file (source it in current shell)
set -a
source "$dot_env_path"
set +a

# Count loaded variables
var_count=$(grep -cv '^\s*$\|^\s*#' "$dot_env_path" || true)
echo -e "${GREEN}✓${NC} Loaded ${GREEN}$var_count${NC} environment variables"

# Summary
echo ""
echo -e "${GREEN}========================================"
echo "Setup Complete!"
echo -e "========================================${NC}"
echo ""
echo "Key environment variables now available:"
echo -e "  ${GREEN}AZURE_SEARCH_SERVICE${NC}: $AZURE_SEARCH_SERVICE"
echo -e "  ${GREEN}AZURE_SEARCH_INDEX${NC}: $AZURE_SEARCH_INDEX"
echo -e "  ${GREEN}AZURE_STORAGE_ACCOUNT${NC}: $AZURE_STORAGE_ACCOUNT"
echo -e "  ${GREEN}AZURE_OPENAI_SERVICE${NC}: $AZURE_OPENAI_SERVICE"
echo ""
echo "You can now run your development commands:"
echo -e "  ${GREEN}cd app/backend && python -m quart run --reload${NC}"
echo -e "  ${GREEN}cd app/frontend && npm run dev${NC}"
echo -e "  ${GREEN}python app/backend/prepdocs.py data/Train_CMO/**/*.pdf${NC}"
echo ""
