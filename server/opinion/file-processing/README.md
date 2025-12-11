python3 -m venv my_virtual_env
source ./my_virtual_env/bin/activate

pip install -r requirements.txt --target=".python*packages/lib/site-packages"
zip -r functionapp-async.zip . -x "*.venv/\_"

pip install -r requirements.txt

# function keys

Look under "AsyncFileIndexing | Function Keys".

curl -v -X POST "https://temptest324234.azurewebsites.net/api/blob-events?code=" \
 -H "Content-Type: application/json" \
 -d '[
{
"id": "abc",
"eventType": "Microsoft.EventGrid.SubscriptionValidationEvent",
"subject": "test",
"eventTime": "2025-05-06T00:00:00Z",
"data": {
"validationCode": "1234567890"
},
"dataVersion": "1.0"
}
]'
