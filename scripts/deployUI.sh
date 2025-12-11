#!/bin/bash
set -e
set -o pipefail

echo "🚀 Starting UI build and deploy..."

cd ../ui #Navigating to the UI folder

echo "🔨 Building the app..."
npm run build

echo "☁️ Uploading build to Azure Blob Storage..."
az storage blob upload-batch \
  --account-name alchemysitehosting \
  --destination \$web \
  --source dist \
  --overwrite \


# echo "🌐 Purging Front Door cache..."
# az afd endpoint purge \
#   --resource-group alc-gant-rg \
#   --profile-name alc-gant-frontdoor \
#   --endpoint-name alchemy-visualisations \
#   --content-paths "/*"

echo "✅ Deployment complete!"
