import io
import json

def handler(ctx, data: bytes = None):
    try:
        body = json.loads(data.decode('utf-8'))
        # Placeholder: would call Quip API & insert into DB
        return json.dumps({"status": "ingested", "data": body})
    except Exception as e:
        return json.dumps({"error": str(e)})

