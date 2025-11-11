#!/bin/bash
set -e
cd "$(dirname "$0")"

rm -f ../lambda.zip
pip install -r requirements.txt -t .
zip -r ../lambda.zip .
echo "Lambda package created at ../lambda.zip"
