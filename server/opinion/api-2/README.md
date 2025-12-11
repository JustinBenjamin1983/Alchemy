# SQL Alchemy

## scalar fetch

session.query(Document).with_entities(Document.original_file_name).first()
filename = (
session.query(Document.original_file_name)
.filter(Document.id == some_id)
.scalar()
)
result = session.query(Document.original_file_name).filter(...).first()
session.query(Folder).filter_by(folder_name="root", dd_id=dd_id).first()
session.query(Folder).filter_by(folder_name="root", dd_id=dd_id).all()
session.query(Document)
.join(Folder)
.filter(Folder.dd_id == dd_id)
.all()

## update

doc = session.query(Document).filter_by(id=doc_id).first()
if doc:
doc.processing_status = "Complete"
doc.uploaded_at = datetime.datetime.utcnow()
session.commit()

## update

session.execute(
update(Document)
.where(Document.id == doc_id)
.values(processing_status="Complete", uploaded_at=datetime.datetime.utcnow())
)
session.commit()

## update

session.query(Document).filter_by(folder_id=folder_id).update(
{"processing_status": "Complete"}
)
session.commit()

# build process

chmod +x build.sh
./build.sh

alchemy-aishop-func-app-test-docker

Support queries:
https://learn.microsoft.com/en-us/answers/questions/2264887/azure-function-app-function-key-validation-and-con
https://www.reddit.com/r/AZURE/comments/1kik3aw/azure_function_app_function_keys_not_working/

You can get the APIM gateway IP address from APIM → Network → Inbound IP address

🛠️ 2. How to Store the Function Key as a Named Value
In Azure Portal:
Go to your API Management instance

In the left menu, select Named values

Click + Add

Fill in:

Display name: FunctionKey-MyBackend

Name: function-key-mybackend

Value: paste your function key (from Azure → Function App → Function → Function Keys → default)

✅ Check "Secret"

Click Create

✅ You now have a secure named value called {{function-key-mybackend}}.

🔄 3. Forward the Function Key in Your APIM Policy
When APIM calls your backend function (which expects ?code=...), you'll pass the key using the Named Value:

Example policy (inside your API operation):
xml
Copy
Edit
<inbound>

<base />
<set-query-parameter name="code" value="{{function-key-mybackend}}" />
</inbound>

func start

curl -X POST https://apim-func-test-123123123412.azure-api.net/alchemy-aishop-func-app-test-docker/upload \
 -H "Authorization: Bearer " \
 -H "Ocp-Apim-Subscription-Key: 1d1cb334ca62490e936f77eb1da89bdd" -H "Content-Type: application/json" -d '{}'

# try:

    #     email, err = auth_get_email(req)
    #     if err:
    #         logging.exception("❌ auth_get_email", err)
    #     logging.info(f"email {email}")

    #     data = req.get_json()
    #     id = data["id"]
    #     if not id:
    #         return func.HttpResponse("Id not supplied", status_code=404)
    #     # save({"email":email, "surname":"bob", "age":2, "firstname":"simo", "special": {"new_thing":"bbbb", "items":[{"one":1},{"two":2}]}}, ["surname", "special"])
    #     entity = get(email)
    #     entity_data = json.loads(entity.get("payload", "{}"))  # default to stringified empty dict
    #     opinions = entity_data.get("opinions", [])

    #     matched_opinion = next((item for item in opinions if item.get("id") == id), None)

    #     # documents = matched_opinion.get("documents", [])
    #     # enabled_docs = [
    #     #     {"doc_id": doc["doc_id"], "doc_name": doc["doc_name"]}
    #     #     for doc in documents if doc.get("enabled")
    #     # ]
    #     # # "explain the benefit of AI to seniors" - "b0ec0750-47c1-4e97-91be-f154870c8d3f"
    #     # # "explain rule 10.6" - "0536ef06-d7ea-4bc2-a362-f2af8a4bb232"
    #     # find_in_opinion_docs(["b0ec0750-47c1-4e97-91be-f154870c8d3f"], "explain the benefit of AI to seniors")

    #     draft = create(matched_opinion["facts"], matched_opinion["questions"], matched_opinion["assumptions"])

    #     return func.HttpResponse(json.dumps({"draft":draft}), status_code=200)
    # except Exception as e:
    #     logging.info(f"failed")
    #     logging.info(e)
    #     logging.exception("❌ Error occurred", e)
    #     return func.HttpResponse("Server error", status_code=500)

## Deploying the Function Apps

If on arch linux use

```bash
sudo chown -R $USER:$USER .python_packages
chmod +x ./build_arch.sh #Specific script with date format for linux
./build_arch.sh
```
