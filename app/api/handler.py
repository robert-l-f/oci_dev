import json

def handler(ctx, data: bytes = None):
    try:
        # Placeholder: would query DB and return response
        return json.dumps({"status": "ok", "data": "sample API response"})
    except Exception as e:
        return json.dumps({"error": str(e)})

