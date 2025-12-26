import requests
from io import BytesIO
from uuid import uuid4


def send_whatsapp_image(
    to: str,
    caption: str,
    image
):
    """
    Send image to WhatsApp with unique request_id
    """

    request_id = str(uuid4())  # 👈 UNIQUE ID

    img_buffer = BytesIO()
    image.save(img_buffer, format="PNG")
    img_buffer.seek(0)

    url = "https://gate.whapi.cloud/messages/image"
    token = "L6R0CC9wNsolWnDmVOVfMbUKNS8gI1Ae"

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Request-ID": request_id   # 👈 UNIQUE PARAM
    }

    data = {
        "to": to,
        "caption": caption
    }

    files = {
        "media": (f"snapshot_{request_id}.png", img_buffer, "image/png")
    }

    response = requests.post(
        url,
        data=data,
        files=files,
        headers=headers,
        timeout=60
    )

    try:
        resp = response.json()
    except Exception:
        resp = response.text

    return {
        "request_id": request_id,
        "status_code": response.status_code,
        "response": resp
    }

# result = send_whatsapp_image(
#     to="120363422762100087@g.us", 
#     caption="*P10 Supply Tracking*",
#     image=image
# )
