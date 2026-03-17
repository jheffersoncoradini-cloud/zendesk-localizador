from flask import Flask, request, jsonify
import requests
import re
import os

print("APP1 ATUALIZADO RODANDO")

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "OK", 200
    
ZENDESK_SUBDOMAIN = os.environ.get("ZENDESK_SUBDOMAIN")
ZENDESK_EMAIL = os.environ.get("ZENDESK_EMAIL")
ZENDESK_API_TOKEN = os.environ.get("ZENDESK_TOKEN")

CAMPO_PEDIDO_ID = 48132439975315


def extrair_pedido(texto):
    texto = str(texto)
    texto = texto.replace("<br>", " ")
    texto = texto.replace("&nbsp;", " ")

    match = re.search(r"Pedido:\s*(\d+)", texto, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def buscar_ticket(pedido):
    url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/search.json"
    query = f"type:ticket custom_field_{CAMPO_PEDIDO_ID}:{pedido}"

    response = requests.get(
        url,
        params={"query": query},
        auth=(f"{ZENDESK_EMAIL}/token", ZENDESK_API_TOKEN),
        timeout=30
    )

    print("STATUS BUSCA:", response.status_code)
    print("QUERY:", query)
    print("RESPOSTA BUSCA:", response.text)

    if response.status_code != 200:
        return None

    data = response.json()
    results = data.get("results", [])

    if not results:
        return None

    return results[0]["id"]


def adicionar_follower(ticket_id, email):
    if not email:
        print("EMAIL DO FOLLOWER N O INFORMADO")
        return

    url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/tickets/{ticket_id}.json"

    payload = {
        "ticket": {
            "followers": [
                {
                    "user_email": email,
                    "action": "put"
                }
            ]
        }
    }

    response = requests.put(
        url,
        json=payload,
        auth=(f"{ZENDESK_EMAIL}/token", ZENDESK_API_TOKEN),
        timeout=30
    )

    print("STATUS FOLLOWER:", response.status_code)
    print("RESPOSTA FOLLOWER:", response.text)


@app.route("/webhook/localizador", methods=["POST"])
def webhook():
    data = request.json or {}
    print("PAYLOAD RECEBIDO:", data)

    texto = str(data)
    pedido = extrair_pedido(texto)

    print("PEDIDO EXTRAIDO:", pedido)

    if not pedido:
        return jsonify({"status": "sem_pedido"}), 200

    ticket_id = buscar_ticket(pedido)
    print("TICKET ENCONTRADO:", ticket_id)

    if not ticket_id:
        return jsonify({"status": "ticket_nao_encontrado", "pedido": pedido}), 200

    email = data.get("current_user_email")
    print("FOLLOWER:", email)

    adicionar_follower(ticket_id, email)

    return jsonify({"status": "ok", "ticket_id": ticket_id, "pedido": pedido}), 200


if __name__ == "__main__":
    app.run(port=5000, debug=True)
