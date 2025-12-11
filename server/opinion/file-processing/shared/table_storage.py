import uuid
import json
import os
import logging
from azure.data.tables import TableServiceClient, TableEntity
from azure.core.exceptions import ResourceNotFoundError

def generate_identifier():
    """
    Generates a UUID-based identifier.
    """
    return str(uuid.uuid4())


def get(email: str, connection_string: str, table_name: str, partition_key: str):
    table_service = TableServiceClient.from_connection_string(connection_string)
    table_client = table_service.get_table_client(table_name=table_name)

    try:
        entity = table_client.get_entity(partition_key=partition_key, row_key=email)
        entity['clean_payload'] = json.loads(entity['payload'])

        return entity
    except ResourceNotFoundError:
        logging.warning(f"No entity found for email: {email}")
        raise ValueError("No email found")

def save(row_key: str, data: dict, allowed_keys: list, connection_string: str, table_name: str, partition_key: str, add_to_item: str = None):
    # TODO: check if payload is str or obj
    try:
        filtered_data = data # TODO {k: v for k, v in data.items() if k in allowed_keys}
        # email = filtered_data.pop("email", None)
        # logging.info("filtered_data")
        # logging.info(filtered_data)
        # if not email:
        #     logging.exception("No email found")
        #     raise ValueError("No email found")

        table_service = TableServiceClient.from_connection_string(connection_string)
        table_client = table_service.get_table_client(table_name=table_name)

        # Create table if it doesn't exist
        try:
            table_client.create_table()
        except Exception:
            pass  # Table already exists
        
        # Prepare entity
        entity = TableEntity()
        try:
            entity = table_client.get_entity(partition_key=partition_key, row_key=str(row_key))
            payload = json.loads(entity["payload"])
            
            if add_to_item:
                logging.info("payload")
                logging.info(payload)
                logging.info(add_to_item)
                if add_to_item in payload and isinstance(payload[add_to_item], list):
                    logging.info("payload[add_to_item]")
                    logging.info(payload[add_to_item])
                    #payload[add_to_item] = payload[add_to_item] + filtered_data
                    logging.info("filtered_data")
                    logging.info(filtered_data)
                    payload[add_to_item].append(filtered_data)
                    logging.info("adding")
                    entity["payload"] = json.dumps(payload)
                else:
                    entity["payload"] = json.dumps([filtered_data])
            else:
                logging.info(f" save - saving to payload {filtered_data}")
                entity["payload"] = json.dumps(filtered_data)
        except Exception as e:
            logging.info(e)
            entity["PartitionKey"] = partition_key
            entity["RowKey"] = row_key
            if add_to_item:
                entity["payload"] = json.dumps({add_to_item:[filtered_data]})
            else:
                entity["payload"] = json.dumps(filtered_data)
        
        # Save entity
        table_client.upsert_entity(entity)

        # logging.info("done with save")

    except Exception as e:
        logging.info(e)
        logging.exception("Error storing JSON data")


def get_user_info(email:str):
    return get(email, os.environ["USER_TABLE_STORAGE_CONNECTION_STRING"], os.environ["USER_TABLE_NAME"], os.environ["USER_TABLE_PARTITION_KEY"])

def save_user_info(row_key: str, data: dict, allowed_keys: list = None, add_to_item: str = None):
    return save(row_key, data, allowed_keys, os.environ["USER_TABLE_STORAGE_CONNECTION_STRING"], os.environ["USER_TABLE_NAME"], os.environ["USER_TABLE_PARTITION_KEY"], add_to_item)

def get_opinions_settings():
    temp = get("settings", os.environ["OPINIONS_SETTINGS_TABLE_STORAGE_CONNECTION_STRING"], os.environ["OPINIONS_SETTINGS_TABLE_NAME"], os.environ["OPINIONS_SETTINGS_PARTITION_KEY"])
    logging.info(f"get_opinions_settings: {temp=}")
    return temp

def save_opinion_settings(data: dict, allowed_keys: list, add_to_item: str = None):
    return save("settings", data, allowed_keys, os.environ["OPINIONS_SETTINGS_TABLE_STORAGE_CONNECTION_STRING"], os.environ["OPINIONS_SETTINGS_TABLE_NAME"], os.environ["OPINIONS_SETTINGS_PARTITION_KEY"], add_to_item)


# def table_update():
#     try:
#         data = {"name":"bob", "user_id": 123}
#         user_id = data.get("user_id")
#         if not user_id:
#             logging.exception("no user_id")
#             return
#         logging.info(f"found user id {user_id}")
        
#         # Connect to Table Storage
#         table_service = TableServiceClient.from_connection_string(TABLE_STORAGE_CONNECTION_STRING)
#         table_client = table_service.get_table_client(table_name=TABLE_NAME)

#         # Query for the entity (assume PartitionKey is 'UserData')
#         entity = None
#         # entities = table_client.query_entities(f"PartitionKey eq 'UserData' and user_id eq '{user_id}'")
#         # for e in entities:
#         #     entity = e
#         #     break
#         entity = table_client.get_entity(partition_key="UserData", row_key=str(user_id))


#         if not entity:
#             logging.exception("no entity")
#             return

#         # Read, modify and update the entity
#         entity["status"] = data.get("status", entity.get("status", "active"))
#         entity["last_updated"] = data.get("timestamp")

#         # Optionally update payload if provided
#         if "payload" in data:
#             entity["payload"] = json.dumps(data["payload"])

#         table_client.update_entity(mode=UpdateMode.MERGE, entity=entity)
#         return func.HttpResponse("User data updated successfully", status_code=200)

#     except Exception as e:
#         logging.exception("Error updating user data")
        
    
# def table_store():

#     try:
#         data = {"user_id": 123, "name":"bob", "surname": "sss"}
        
#         # Connect to Table Storage
#         table_service = TableServiceClient.from_connection_string(TABLE_STORAGE_CONNECTION_STRING)
#         table_client = table_service.get_table_client(table_name=TABLE_NAME)

#         # Create table if it doesn't exist
#         try:
#             table_client.create_table()
#         except Exception:
#             pass  # Table already exists

#         # Prepare entity
#         entity = TableEntity()
#         entity["PartitionKey"] = "UserData"
#         entity["RowKey"] = str(data['user_id']) #str(uuid.uuid4())

#         # Store only selected fields (customize as needed)
#         for key in ["user_id", "name"]:
#             if key in data:
#                 entity[key] = data[key]

#         # Store the rest of the data as raw JSON string
#         entity["payload"] = json.dumps(data)

#         # Save entity
#         table_client.create_entity(entity)

#         logging.info("done with save")

#     except Exception as e:
#         logging.exception("Error storing JSON data")

