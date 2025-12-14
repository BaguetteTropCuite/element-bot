import json
import os
import asyncio
import traceback
from flask import Flask, request, jsonify
from nio import AsyncClient

# Configuration de l'utilisateur Matrix Element
MATRIX_USER = os.environ.get("MATRIX_USER", "@bot_homelab:matrix.org")
MATRIX_PASSWORD = os.environ.get("MATRIX_PASSWORD")
HOMESERVER = os.environ.get("HOMESERVER", "https://matrix.org")
ROOM_ID = os.environ.get("ROOM_ID")

# Vérification des variables password et Romm_ID.
if not MATRIX_PASSWORD or not ROOM_ID:
    print("Erreur: Les variables MATRIX_PASSWORD et/ou ROOM_ID ne sont pas configurées.")
    exit(1)


app = Flask(__name__)

# Fonction d'envoi
async def send_matrix_message(room_id, message):
    client = AsyncClient(HOMESERVER, MATRIX_USER) # AsyncClient = Classe de la lib matrix-nio pour instancier le bot
    

    # Tentative de connexion au serveur depuis l'utilisateur bot
    try:
        await client.login(MATRIX_PASSWORD)
    except Exception as e:
        print(f"[BOT] Matrix connexion failed: {e}")
        return False

    # Rejoindre la room (Renverra toujours une erreur bénigne si l'utilisateur a déjà join la room)
    try:
        await client.join(room_id)
    except Exception:
        pass

    # Envoi
    response = await client.room_send( # Initialisation via un dict, arg obligatoires (room_id, message_type, content)
        room_id=room_id,
        message_type="m.room.message",
        content={
            "msgtype": "m.text",
            "body": message    # Variable du message
        }
    )
    
    await client.logout()
    
    return response.event_id is not None


# Route de test (Vérifie toute la logique de communication sans les erreurs de parsing fonctionne)
@app.route('/debug', methods=['POST'])
def handle_debug():
    try:
        notification_message = "debug sans json OK"
        
        success = asyncio.run(send_matrix_message(ROOM_ID, notification_message))

        if success:
            return jsonify({"status": "ok", "message": "Message de debug Matrix envoyé"}), 200
        else:
            return jsonify({"status": "error", "message": "Échec de l'envoi Matrix"}), 500
        
    except Exception as e:
        print(f" [DEBUG SANS JSON] C'est la merde : {e}")
        return jsonify({"status": "error", "message": f"Erreur critique lors du debug (Lié à la fonction) {str(e)}"}), 500
    
    

# Route de capture
@app.route('/capture-json', methods=['POST', 'GET'])
def capture_json():
    try:
        if request.is_json:
            data = request.json
            content_type = "JSON (application/json)"
        else:
            data = request.data.decode('utf-8') 
            content_type = "TEXTE BRUT (Content-Type manquant)"
            
        # Afficher le contenu complet dans les logs
        print("\n" + "="*50) 
        print(f"/! WEBHOOK CAPTURÉ ========================================== /!| ({content_type})")
        print(f"URL => : {request.url}")
        print(f"Méthode =>: {request.method}")
        
        if isinstance(data, dict) or isinstance(data, list):
            content_to_print = json.dumps(data, indent=4)
        else:
            # Si chaine de data brute
            content_to_print = str(data)
            
        print(f"Contenu => :\n{content_to_print}")
        print("="*50 + "\n")

        return jsonify({"status": "captured", "message": "Pokemon capturé"}), 200

    except Exception as e:
        # Si erreur
        print("\n" + "#"*50)
        print(f" [ERREUR CRITIQUE] Échec de la capture du Webhook : {e}")
        traceback.print_exc()
        print("#"*50 + "\n")
        
        return jsonify({"status": "error", "message": f"Échec de la capture: {str(e)}"}), 500


# Kuma
@app.route('/webhook/alert', methods=['POST'])
def handle_webhook():
    
    try:
        data = request.json
        print(f"Webhook reçu: {json.dumps(data, indent=2)}")

        # Extract JSON
        notification_message = "ALERTE KUMA n\n"
        
        # Kuma extract
        monitor_name = data.get('monitor', {}).get('name', 'Service Inconnu')
        status = data.get('status', 'INCONNU')
        
        if status == 'down':
            notification_message += f" **{monitor_name}** est HORS LIGNE (DOWN) !"
        elif status == 'up':
            notification_message += f" **{monitor_name}** est de nouveau EN LIGNE (UP)."
        else:
            notification_message += f" Statut mis à jour pour {monitor_name}: {status}"
        
        notification_message += f"\n\nMessage: {data.get('msg', 'Pas de message détaillé.')}"

        # Send
        success = asyncio.run(send_matrix_message(ROOM_ID, notification_message))

        if success:
            return jsonify({"status": "ok", "message": "Notification Matrix envoyée"}), 200
        else:
            return jsonify({"status": "error", "message": "Échec de l'envoi Matrix"}), 500

    except Exception as e:
        print(f"Erreur lors du traitement du Webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6969)