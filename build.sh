#!/bin/bash

# A simple script to build the WordPress plugin zip file.

# Set the plugin slug and version.
PLUGIN_SLUG="wp-idealista-scraper"
PLUGIN_VERSION=$(grep -i "Version:" "wp-idealista-scraper/wp-idealista-scraper.php" | awk -F' ' '{print $2}' | tr -d '\r')

# Set the build directory.
BUILD_DIR="build"

# Create the build directory if it doesn't exist.
mkdir -p $BUILD_DIR

# Set the zip file name.
ZIP_FILE="$BUILD_DIR/$PLUGIN_SLUG.$PLUGIN_VERSION.zip"

# Create the zip file.
echo "Creating zip file: $ZIP_FILE"
zip -r $ZIP_FILE $PLUGIN_SLUG -x "*.git*" "*build.sh*" "*README.md*" "*docs/*"

echo "Build complete."
