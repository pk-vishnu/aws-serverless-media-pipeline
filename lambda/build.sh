#!/bin/bash
set -e

echo "Cleaning old build..."
rm -rf build
mkdir -p build/tmp

echo "Installing dependencies..."
pip install -r lambda/requirements.txt -t build/tmp

echo "Copying source..."
cp lambda/image_processor.py build/tmp/

echo " Zipping package..."
cd build/tmp
zip -r ../lambda.zip .
cd ../..
rm -rf build/tmp

echo "Built build/lambda.zip"
