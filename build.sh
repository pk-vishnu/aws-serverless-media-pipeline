#!/bin/bash
# This script builds both the processor and analyzer Lambda zips

set -e

PROCESSOR_SRC_DIR="lambda_processing"
ANALYZER_SRC_DIR="lambda_analyser"
BUILD_DIR="build"

PROCESSOR_TMP_DIR="${BUILD_DIR}/tmp_processor"
ANALYZER_TMP_DIR="${BUILD_DIR}/tmp_analyzer"

PROCESSOR_ZIP_NAME="processing_lambda.zip" 
ANALYZER_ZIP_NAME="analyzer_lambda.zip"

echo "Cleaning old build artifacts..."
rm -rf ${BUILD_DIR}
mkdir -p ${PROCESSOR_TMP_DIR}
mkdir -p ${ANALYZER_TMP_DIR}

echo "Building ${PROCESSOR_ZIP_NAME}..."
echo "  Installing dependencies from ${PROCESSOR_SRC_DIR}/requirements.txt"
pip install -r "${PROCESSOR_SRC_DIR}/requirements.txt" -t ${PROCESSOR_TMP_DIR}

echo "  Copying source: ${PROCESSOR_SRC_DIR}/image_processor.py"
cp "${PROCESSOR_SRC_DIR}/image_processor.py" ${PROCESSOR_TMP_DIR}/

echo "  Zipping package..."
(cd ${PROCESSOR_TMP_DIR} && zip -r "../${PROCESSOR_ZIP_NAME}" .)

echo "Building ${ANALYZER_ZIP_NAME}..."
echo "  Installing dependencies from ${ANALYZER_SRC_DIR}/requirements.txt"
pip install -r "${ANALYZER_SRC_DIR}/requirements.txt" -t ${ANALYZER_TMP_DIR}

echo "  Copying source: ${ANALYZER_SRC_DIR}/image_analyser.py"
cp "${ANALYZER_SRC_DIR}/image_analyser.py" "${ANALYZER_TMP_DIR}/image_analyser.py"

echo "  Zipping package..."
(cd ${ANALYZER_TMP_DIR} && zip -r "../${ANALYZER_ZIP_NAME}" .)

echo "Cleaning up temporary directories..."
rm -rf ${PROCESSOR_TMP_DIR}
rm -rf ${ANALYZER_TMP_DIR}

echo "Build complete!"
echo "Artifacts:"
echo "  ${BUILD_DIR}/${PROCESSOR_ZIP_NAME}"
echo "  ${BUILD_DIR}/${ANALYZER_ZIP_NAME}"
