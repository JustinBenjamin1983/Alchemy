#!/bin/bash

# CONFIGURABLE SETTINGS
DOCKER_IMAGE="mcr.microsoft.com/azure-functions/python:4-python3.12"

RESOURCE_GROUP="alchemy-aishop-apps-func-test"
STORAGE_ACCOUNT="aishopfunctionstest"
CONTAINER_NAME="functiondeploy"
FUNCTION_APP="temptest324234"

ENV_VAR_NAME="WEBSITE_RUN_FROM_PACKAGE"
SAS_EXPIRY_DAYS=12

APP_DIR="$(pwd)"
OUTPUT_ZIP="functionapp-async.zip"
MAX_SAFE_ZIP_SIZE_MB=800


echo "🚀 Starting build process..."

# Step 1: Clean previous build
echo "🧹 Cleaning previous .python_packages..."
rm -rf .python_packages
mkdir -p .python_packages/lib/site-packages

# -----------------------------------------
# RUN SYNTAX CHECK ON ALL OF MY PYTHON FILES
# -----------------------------------------
echo "🔍 Running syntax check on Python files..."
find . \( -path ./\.python_packages -o -path ./\.venv -o -path ./__pycache__ -o -path ./tests -o -path ./\.git -o -path ./scripts \) -prune -o -name "*.py" -exec python3 -m py_compile {} \;

# Step 2: Run Docker to build Linux-compatible Python packages
echo "🐳 Building dependencies inside Docker..."
docker run --rm -v "$APP_DIR":/home/site/wwwroot -w /home/site/wwwroot $DOCKER_IMAGE /bin/bash -c "
    pip install -qq -r requirements.txt --target=.python_packages/lib/site-packages
"

# Step 3: Remove previous zip
echo "🧹 Removing old ZIP if exists..."
rm -f $OUTPUT_ZIP

# Step 4: Create new ZIP
echo "📦 Zipping the app..."
zip -qr $OUTPUT_ZIP . -x "*.git/*" "*.venv/*" "*__pycache__/*" "*.DS_Store" "*.ipynb_checkpoints/*"

# Step 5: Show ZIP size
ZIP_SIZE_BYTES=$(stat -f%z "$OUTPUT_ZIP")
ZIP_SIZE_MB=$(echo "scale=2; $ZIP_SIZE_BYTES/1024/1024" | bc)

echo "📏 ZIP file size: $ZIP_SIZE_MB MB"

# Step 6: Warn if ZIP is large
if (( $(echo "$ZIP_SIZE_MB > $MAX_SAFE_ZIP_SIZE_MB" | bc -l) )); then
    echo "⚠️ WARNING: ZIP size exceeds $MAX_SAFE_ZIP_SIZE_MB MB. Azure might reject it or cause slow cold starts."
else
    echo "✅ ZIP size is within safe limits."
fi


# ========== 2. UPLOAD TO BLOB STORAGE ==========
echo "Uploading to Blob Storage..."
az storage blob upload \
  --account-name $STORAGE_ACCOUNT \
  --container-name $CONTAINER_NAME \
  --name $OUTPUT_ZIP \
  --file $OUTPUT_ZIP \
  --overwrite
echo "✅ Uploaded"

# ========== 3. GENERATE SAS TOKEN ==========
echo "Generating SAS URL..."
EXPIRY_TIME=$(date -u -v+${SAS_EXPIRY_DAYS}d '+%Y-%m-%dT%H:%MZ')
SAS_URL=$(az storage blob generate-sas \
  --account-name $STORAGE_ACCOUNT \
  --container-name $CONTAINER_NAME \
  --name $OUTPUT_ZIP \
  --permissions r \
  --expiry "$EXPIRY_TIME" \
  --output tsv)

BLOB_URL="https://${STORAGE_ACCOUNT}.blob.core.windows.net/${CONTAINER_NAME}/${OUTPUT_ZIP}?${SAS_URL}"

# ========== 4. UPDATE APP SETTING ==========
echo "Updating $ENV_VAR_NAME in Function App..."
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings "$ENV_VAR_NAME=$BLOB_URL"

echo $OUTPUT_ZIP
echo "🎯 Done"