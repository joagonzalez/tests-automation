#!/bin/bash

echo "Creating network test ZIP package..."

# Create temporary directory
TEMP_DIR="temp_network_test"
ZIP_NAME="network_test_001.zip"

# Clean up any existing temp directory
rm -rf $TEMP_DIR
rm -f $ZIP_NAME

# Create directory structure
mkdir -p $TEMP_DIR

# Copy test results
cp test_results/network_run_001/network_results.csv $TEMP_DIR/

# Create ZIP
cd $TEMP_DIR
zip ../$ZIP_NAME *.csv
cd ..

# Clean up
rm -rf $TEMP_DIR

echo "✅ Created $ZIP_NAME"
echo "You can now import this with:"
echo "uv run benchmark-analyzer import-results \\"
echo "  --package $ZIP_NAME \\"
echo "  --type network \\"
echo "  --environment environments/network-lab.yaml \\"
echo "  --bom boms/network-server.yaml \\"
echo "  --engineer 'Network Team' \\"
echo "  --comments 'Network performance baseline test'"