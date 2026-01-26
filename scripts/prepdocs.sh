#!/bin/sh

# Load Python environment
. ./scripts/load_python_env.sh

echo "========================================"
echo "  Config-Driven Index Creation System"
echo "========================================"
echo ""

cwd=$(pwd)
additionalArgs=""
if [ $# -gt 0 ]; then
    additionalArgs="$@"
fi

# Path to configuration file
configPath="$cwd/data/index_config.json"

if [ ! -f "$configPath" ]; then
    echo "ERROR: index_config.json not found at $configPath"
    echo "Running in single-index mode with default settings..."
    ./.venv/bin/python ./app/backend/prepdocs.py "$cwd/data/*" --verbose $additionalArgs
    exit $?
fi

# Read configuration using Python (cross-platform JSON parsing)
echo "Loading configuration from: $configPath"

# Use Python to parse the JSON and generate shell-compatible output
indexData=$(./.venv/bin/python -c "
import json
import sys

with open('$configPath', 'r') as f:
    config = json.load(f)

base_path = config['base_path']
indexes = config['indexes']

# Output format: INDEX_KEY|INDEX_NAME|FOLDER1,FOLDER2,... (or * for all)
for index_key, index_config in indexes.items():
    index_name = index_config['name']
    folders = index_config['folders']
    folders_str = ','.join(folders)
    print(f'{index_key}|{index_name}|{folders_str}')
")

basePath=$(./.venv/bin/python -c "
import json
with open('$configPath', 'r') as f:
    config = json.load(f)
print(config['base_path'])
")

# Count indexes
totalIndexes=$(echo "$indexData" | wc -l | tr -d ' ')
currentIndex=0

echo "Found $totalIndexes index(es) to create/update"
echo "Base path: $basePath"
echo ""

# Process each index
echo "$indexData" | while IFS='|' read -r indexKey indexName foldersStr; do
    currentIndex=$((currentIndex + 1))

    echo "========================================"
    echo "[$currentIndex/$totalIndexes] Processing: $indexKey"
    echo "  Index Name: $indexName"
    echo "========================================"

    # Check if folders is "*" (all folders)
    if [ "$foldersStr" = "*" ]; then
        echo "  Mode: ALL folders (wildcard)"
        echo ""

        dataPath="$cwd/$basePath/*"
        echo "  Running: ./app/backend/prepdocs.py \"$dataPath\" --index $indexKey --verbose $additionalArgs"

        ./.venv/bin/python ./app/backend/prepdocs.py "$dataPath" --index "$indexKey" --verbose $additionalArgs

        if [ $? -ne 0 ]; then
            echo "  ERROR: Failed to index all folders for $indexKey"
            exit 1
        fi
        echo "  SUCCESS: All folders indexed to $indexName"
    else
        # Specific folders - loop through each one
        # Count folders by counting commas + 1
        folderCount=$(echo "$foldersStr" | tr ',' '\n' | wc -l | tr -d ' ')
        echo "  Mode: Specific folders ($folderCount folder(s))"
        echo ""

        currentFolder=0

        # Split folders by comma and process each
        echo "$foldersStr" | tr ',' '\n' | while read -r folder; do
            currentFolder=$((currentFolder + 1))
            echo "  [$currentFolder/$folderCount] Indexing folder: $folder"

            dataPath="$cwd/$basePath/$folder"
            echo "    Running: ./app/backend/prepdocs.py \"$dataPath\" --index $indexKey --verbose $additionalArgs"

            ./.venv/bin/python ./app/backend/prepdocs.py "$dataPath" --index "$indexKey" --verbose $additionalArgs

            if [ $? -ne 0 ]; then
                echo "    ERROR: Failed to index folder '$folder' for $indexKey"
                exit 1
            fi
            echo "    SUCCESS: '$folder' indexed to $indexName"
            echo ""
        done
    fi

    echo ""
done

# Final summary
echo "========================================"
echo "  INDEXING COMPLETE!"
echo "========================================"
echo ""
echo "Created/Updated indexes:"

echo "$indexData" | while IFS='|' read -r indexKey indexName foldersStr; do
    if [ "$foldersStr" = "*" ]; then
        echo "  - $indexName ($indexKey): ALL folders"
    else
        folderCount=$(echo "$foldersStr" | tr ',' '\n' | wc -l | tr -d ' ')
        echo "  - $indexName ($indexKey): $folderCount folder(s)"
    fi
done

echo ""
echo "To switch indexes, set environment variable:"
echo "  export AZURE_SEARCH_INDEX='gptkbindex-internal'"
echo "  export AZURE_SEARCH_INDEX='gptkbindex-public'"
echo ""
