from flask import Flask, render_template, request, send_from_directory
from flask_mail import Mail, Message
import os
import requests

app = Flask(__name__)

# --- Email config (env first, fallback to your current values) ---
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "demenagementpmg@gmail.com")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "jjrd trtj ysfn ppfe")  # Gmail App Password
MAIL_DEFAULT = os.getenv("MAIL_DEFAULT_SENDER", "demenagementpmg@gmail.com")

app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_DEFAULT_SENDER=MAIL_DEFAULT,
)
mail = Mail(app)

# ---- Service Configuration ----
SERVICE_LABELS = {
    'moving': {'en': 'Moving', 'fr': 'Déménagement'},
    'junk_removal': {'en': 'Junk Removal', 'fr': 'Enlèvement d\'objets'},
    'cleaning': {'en': 'Cleaning', 'fr': 'Nettoyage'},
    'transport': {'en': 'General Transport', 'fr': 'Transport général'},
    'packing': {'en': 'Packing', 'fr': 'Emballage'},
    'storage': {'en': 'Storage', 'fr': 'Entreposage'}
}

def get_service_label(service_type: str, lang: str = 'en') -> str:
    """Get properly formatted service label in specified language"""
    service_key = (service_type or '').strip().lower().replace(' ', '_').replace('-', '_')
    
    # Debug logging to help you verify it's working
    app.logger.info(f"Service lookup: original='{service_type}' -> key='{service_key}'")
    
    if service_key in SERVICE_LABELS:
        label = SERVICE_LABELS[service_key].get(lang, SERVICE_LABELS[service_key]['en'])
        app.logger.info(f"Found service label: '{label}'")
        return label
    
    # Better fallback
    fallback = service_type.replace('_', ' ').title() if service_type else 'Moving'
    app.logger.info(f"Using fallback: '{fallback}'")
    return fallback

# ---- Helper Functions ----
def send_customer_acknowledgment(to_email: str, customer_data: dict, lang: str = 'en'):
    """Send acknowledgment email to customer with proper service type"""
    if not to_email or '@' not in to_email:
        app.logger.warning(f"Invalid email address: {to_email}")
        return False
    
    name = customer_data.get('name', 'client')
    service_type = customer_data.get('service_type', 'moving')
    service_label = get_service_label(service_type, lang)
    
    # Email subject
    if lang == 'fr':
        subject = f"Merci pour votre demande - PMG Déménagement ({service_label})"
    else:
        subject = f"Thank you for your request - PMG Moving ({service_label})"
    
    # Build service-specific details
    service_details_en = ""
    service_details_fr = ""
    
    if service_type == 'cleaning':
        # Cleaning service details
        if customer_data.get('cleaning_type'):
            service_details_en += f"- Cleaning Type: {customer_data.get('cleaning_type')}\n"
            service_details_fr += f"- Type de nettoyage: {customer_data.get('cleaning_type')}\n"
        if customer_data.get('property_size'):
            service_details_en += f"- Property Size: {customer_data.get('property_size')}\n"
            service_details_fr += f"- Taille de la propriété: {customer_data.get('property_size')}\n"
        if customer_data.get('service_address'):
            service_details_en += f"- Service Address: {customer_data.get('service_address')}\n"
            service_details_fr += f"- Adresse du service: {customer_data.get('service_address')}\n"
        if customer_data.get('pets'):
            service_details_en += f"- Pets: {customer_data.get('pets')}\n"
            service_details_fr += f"- Animaux: {customer_data.get('pets')}\n"
    else:
        # Moving/other service details
        if customer_data.get('pickup_address') and customer_data.get('pickup_address') != 'N/A':
            service_details_en += f"- From: {customer_data.get('pickup_address')}\n"
            service_details_fr += f"- De: {customer_data.get('pickup_address')}\n"
        if customer_data.get('dropoff_address') and customer_data.get('dropoff_address') != 'N/A':
            service_details_en += f"- To: {customer_data.get('dropoff_address')}\n"
            service_details_fr += f"- Vers: {customer_data.get('dropoff_address')}\n"
    
    # Email body
    if lang == 'fr':
        body = f"""Bonjour {name},

Merci d'avoir contacté PMG Déménagement. Nous avons bien reçu votre demande de {service_label.lower()}.

Détails de votre demande:
- Service: {service_label}
- Date souhaitée: {customer_data.get('date', 'À confirmer')}
{service_details_fr}
Pour planifier un appel rapide: https://calendly.com/groupepmg
Répondez à ce courriel pour ajouter des détails (escaliers, ascenseur, objets fragiles, etc.).

Cordialement,
L'équipe PMG

---

Hello {name},

Thank you for contacting PMG Moving. We've received your {service_label.lower()} request.

Your Request Details:
- Service: {service_label}
- Requested Date: {customer_data.get('date', 'TBD')}
{service_details_en}
To schedule a quick call: https://calendly.com/groupepmg
Reply with any details (stairs, elevator, fragile items, etc.).

Best regards,
PMG Team"""
    else:
        body = f"""Hello {name},

Thank you for contacting PMG Moving. We've received your {service_label.lower()} request.

Your Request Details:
- Service: {service_label}
- Requested Date: {customer_data.get('date', 'TBD')}
{service_details_en}
To schedule a quick call: https://calendly.com/groupepmg
Reply with any details (stairs, elevator, fragile items, etc.).

Best regards,
PMG Team

---

Bonjour {name},

Merci d'avoir contacté PMG Déménagement. Nous avons bien reçu votre demande de {service_label.lower()}.

Détails de votre demande:
- Service: {service_label}
- Date souhaitée: {customer_data.get('date', 'À confirmer')}
{service_details_fr}
Pour planifier un appel rapide: https://calendly.com/groupepmg
Répondez à ce courriel pour ajouter des détails (escaliers, ascenseur, objets fragiles, etc.).

Cordialement,
L'équipe PMG"""
    
    try:
        msg = Message(subject, recipients=[to_email])
        msg.body = body
        mail.send(msg)
        app.logger.info(f"Acknowledgment email sent to {to_email} for service: {service_label}")
        return True
    except Exception as e:
        app.logger.error(f"Failed to send acknowledgment email: {e}")
        return False

def send_internal_notification(customer_data: dict, lang: str = 'en'):
    """Send notification email to PMG team"""
    service_type = customer_data.get('service_type', 'moving')
    service_label = get_service_label(service_type, 'en')  # Internal emails in English
    
    subject = f"New {service_label} Request - {customer_data.get('name', 'Unknown')}"
    
    # Build service-specific details for internal email
    service_details = ""
    if service_type == 'cleaning':
        service_details += f"Cleaning Type: {customer_data.get('cleaning_type', 'N/A')}\n"
        service_details += f"Property Size: {customer_data.get('property_size', 'N/A')}\n"
        service_details += f"Service Address: {customer_data.get('service_address', 'N/A')}\n"
        service_details += f"Pets: {customer_data.get('pets', 'N/A')}\n"
    else:
        if customer_data.get('pickup_address'):
            service_details += f"Pickup Address: {customer_data.get('pickup_address', 'N/A')}\n"
        if customer_data.get('dropoff_address'):
            service_details += f"Drop-off Address: {customer_data.get('dropoff_address', 'N/A')}\n"
    
    body = f"""Hello PMG Team! A new {service_label.lower()} request has been submitted. Close that lead!

Customer Information:
Name: {customer_data.get('name', 'N/A')}
Email: {customer_data.get('email', 'N/A')}
Phone: {customer_data.get('phone', 'N/A')}
Language: {lang.upper()}

Service Details:
Service Type: {service_label}
Date: {customer_data.get('date', 'N/A')}
{service_details}
Comments: {customer_data.get('comments', 'N/A')}
Source: {customer_data.get('source', 'website')}
"""
    
    try:
        msg = Message(subject, recipients=[MAIL_DEFAULT])
        msg.body = body
        mail.send(msg)
        app.logger.info(f"Internal notification sent for {service_label} request")
        return True
    except Exception as e:
        app.logger.error(f"Failed to send internal notification: {e}")
        return False

def forward_to_fastapi(payload: dict):
    """Forward lead to FastAPI backend"""
    api_secret = os.getenv("API_SECRET", "pmg_api_2024_prod_1")
    headers = {"x-api-secret": api_secret}
    try:
        r = requests.post(
            "https://api.demenagementpmg.ca/lead",
            json=payload,
            headers=headers,
            timeout=5,
        )
        app.logger.info(f"Lead forwarded to FastAPI ({r.status_code})")
    except Exception as e:
        app.logger.error(f"FastAPI forwarding failed: {e}")

def forward_to_n8n(payload: dict):
    """Send lead data to n8n webhook"""
    url = os.getenv("LEADS_WEBHOOK_URL")
    secret = os.getenv("PMG_WEBHOOK_SECRET")
    
    if not url:
        app.logger.warning("LEADS_WEBHOOK_URL not set; skipping n8n forward")
        return
    
    headers = {"x-pmg-secret": secret} if secret else {}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        app.logger.info(f"n8n forward status: {r.status_code}")
    except Exception as e:
        app.logger.error(f"n8n forward failed: {e}")

def create_lead_payload(form_data: dict, lang: str) -> dict:
    """Create standardized lead payload for all integrations"""
    return {
        "name": form_data.get('name'),
        "email": form_data.get('email'),
        "phone": form_data.get('phone'),
        "lang": lang,
        "service_type": form_data.get('service_type', 'moving'),
        "pickup_address": form_data.get('pickup_address'),
        "dropoff_address": form_data.get('dropoff_address'),
        "service_address": form_data.get('service_address'),
        "move_date": form_data.get('move_date'),
        "cleaning_date": form_data.get('cleaning_date'),
        "cleaning_type": form_data.get('cleaning_type'),
        "property_size": form_data.get('property_size'),
        "pets": form_data.get('pets'),
        "comments": form_data.get('comments'),
        "notes": form_data.get('notes'),
        "source": form_data.get('source', 'website'),
        "utm_source": form_data.get('utm_source', ''),
        "timestamp": request.headers.get('X-Timestamp', '')
    }

# -------------------- Routes (EN) --------------------

@app.route("/")
def home():
    return render_template("index.html", title="Home")

@app.route("/contact")
def contact():
    return render_template("contact.html", title="Contact")

@app.route("/policies")
def policies():
    return render_template("policies.html", title="Terms of Service & Policies")

@app.route("/quote", methods=["GET", "POST"])
def quote():
    if request.method == "POST":
        # Extract form data - FIXED: using serviceType consistently
        form_data = {
            'name': f"{request.form.get('firstName', 'N/A')} {request.form.get('lastName', 'N/A')}",
            'email': request.form.get('email', 'N/A'),
            'phone': request.form.get('phone', 'N/A'),
            'pickup_address': request.form.get('pickupAddress', 'N/A'),
            'dropoff_address': request.form.get('dropoffAddress', 'N/A'),
            'comments': request.form.get('comments', 'N/A'),
            'move_date': request.form.get('movingDate', 'N/A'),
            'service_type': request.form.get('serviceType', 'moving'),  # FIXED: was serviceType -> service_type mismatch
            'source': request.form.get('source', 'website'),
            'utm_source': request.form.get('utm_source', '')
        }
        
        # Prepare customer data for emails
        customer_data = {
            'name': form_data['name'],
            'service_type': form_data['service_type'],
            'date': form_data['move_date'],
            'pickup_address': form_data['pickup_address'],
            'dropoff_address': form_data['dropoff_address'],
            'email': form_data['email'],
            'phone': form_data['phone'],
            'comments': form_data['comments'],
            'source': form_data['source']
        }
        
        # Send internal notification
        send_internal_notification(customer_data, 'en')
        
        # Send customer acknowledgment
        send_customer_acknowledgment(form_data['email'], customer_data, 'en')
        
        # Forward to integrations
        payload = create_lead_payload(form_data, 'en')
        forward_to_fastapi(payload)
        forward_to_n8n(payload)
        
        return render_template("thankyou.html", name=request.form.get('firstName', 'there'))
    
    return render_template("quote.html", title="Get a Quote")

@app.route("/cleaning", methods=["GET", "POST"])
def cleaning():
    if request.method == "POST":
        # Extract form data - Updated field mappings for cleaning
        form_data = {
            'name': request.form.get('name', 'N/A'),
            'email': request.form.get('email', 'N/A'),
            'phone': request.form.get('phone', 'N/A'),
            'service_address': request.form.get('serviceAddress', 'N/A'),
            'cleaning_date': request.form.get('cleaningDate', 'N/A'),
            'cleaning_type': request.form.get('cleaningType', 'N/A'),
            'property_size': request.form.get('propertySize', 'N/A'),
            'pets': request.form.get('pets', 'N/A'),
            'comments': request.form.get('comments', 'N/A'),
            'service_type': 'cleaning',
            'source': request.form.get('source', 'website'),
            'utm_source': request.form.get('utm_source', '')
        }
        
        # Prepare customer data for emails
        customer_data = {
            'name': form_data['name'],
            'service_type': 'cleaning',
            'date': form_data['cleaning_date'],
            'service_address': form_data['service_address'],
            'email': form_data['email'],
            'phone': form_data['phone'],
            'cleaning_type': form_data['cleaning_type'],
            'property_size': form_data['property_size'],
            'pets': form_data['pets'],
            'comments': form_data['comments'],
            'source': form_data['source']
        }
        
        # Send internal notification
        send_internal_notification(customer_data, 'en')
        
        # Send customer acknowledgment
        send_customer_acknowledgment(form_data['email'], customer_data, 'en')
        
        # Forward to integrations
        payload = create_lead_payload(form_data, 'en')
        forward_to_fastapi(payload)
        forward_to_n8n(payload)
        
        return render_template("thankyou.html", name=form_data['name'])
    
    return render_template("cleaning.html", title="Cleaning Services")

@app.route("/reviews")
def reviews():
    return render_template("reviews.html", title="Reviews")

@app.route("/gallery")
def gallery():
    gallery_folder = os.path.join(app.static_folder, "images/gallery")
    images = [img for img in os.listdir(gallery_folder)
              if img.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))]
    return render_template("gallery.html", images=images, title="Gallery")

@app.route("/why")
def why():
    return render_template("why.html", title="Why PMG")

# -------------------- Routes (FR) --------------------

@app.route("/fr")
def fr_home():
    return render_template("fr/index.html", title="Accueil")

@app.route("/fr/policies")
def fr_policies():
    return render_template("fr/policies.html", title="Conditions de service et politiques")

@app.route("/fr/quote", methods=["GET", "POST"])
def fr_quote():
    if request.method == "POST":
        # Extract form data - FIXED: using serviceType consistently
        form_data = {
            'name': f"{request.form.get('firstName', 'N/A')} {request.form.get('lastName', 'N/A')}",
            'email': request.form.get('email', 'N/A'),
            'phone': request.form.get('phone', 'N/A'),
            'pickup_address': request.form.get('pickupAddress', 'N/A'),
            'dropoff_address': request.form.get('dropoffAddress', 'N/A'),
            'comments': request.form.get('comments', 'N/A'),
            'move_date': request.form.get('movingDate', 'N/A'),
            'service_type': request.form.get('serviceType', 'moving'),  # FIXED: consistent field name
            'source': request.form.get('source', 'website'),
            'utm_source': request.form.get('utm_source', '')
        }
        
        # Prepare customer data for emails
        customer_data = {
            'name': form_data['name'],
            'service_type': form_data['service_type'],
            'date': form_data['move_date'],
            'pickup_address': form_data['pickup_address'],
            'dropoff_address': form_data['dropoff_address'],
            'email': form_data['email'],
            'phone': form_data['phone'],
            'comments': form_data['comments'],
            'source': form_data['source']
        }
        
        # Send internal notification
        send_internal_notification(customer_data, 'fr')
        
        # Send customer acknowledgment
        send_customer_acknowledgment(form_data['email'], customer_data, 'fr')
        
        # Forward to integrations
        payload = create_lead_payload(form_data, 'fr')
        forward_to_fastapi(payload)
        forward_to_n8n(payload)
        
        return render_template("fr/thankyou.html", name=request.form.get('firstName', 'there'))
    
    return render_template("fr/quote.html", title="Demander un devis")

@app.route("/fr/cleaning", methods=["GET", "POST"])
def fr_cleaning():
    if request.method == "POST":
        # Extract form data - Updated field mappings for cleaning
        form_data = {
            'name': request.form.get('name', 'N/A'),
            'email': request.form.get('email', 'N/A'),
            'phone': request.form.get('phone', 'N/A'),
            'service_address': request.form.get('serviceAddress', 'N/A'),
            'cleaning_date': request.form.get('cleaningDate', 'N/A'),
            'cleaning_type': request.form.get('cleaningType', 'N/A'),
            'property_size': request.form.get('propertySize', 'N/A'),
            'pets': request.form.get('pets', 'N/A'),
            'comments': request.form.get('comments', 'N/A'),
            'service_type': 'cleaning',
            'source': request.form.get('source', 'website'),
            'utm_source': request.form.get('utm_source', '')
        }
        
        # Prepare customer data for emails
        customer_data = {
            'name': form_data['name'],
            'service_type': 'cleaning',
            'date': form_data['cleaning_date'],
            'service_address': form_data['service_address'],
            'email': form_data['email'],
            'phone': form_data['phone'],
            'cleaning_type': form_data['cleaning_type'],
            'property_size': form_data['property_size'],
            'pets': form_data['pets'],
            'comments': form_data['comments'],
            'source': form_data['source']
        }
        
        # Send internal notification
        send_internal_notification(customer_data, 'fr')
        
        # Send customer acknowledgment
        send_customer_acknowledgment(form_data['email'], customer_data, 'fr')
        
        # Forward to integrations
        payload = create_lead_payload(form_data, 'fr')
        forward_to_fastapi(payload)
        forward_to_n8n(payload)
        
        return render_template("fr/thankyou.html", name=form_data['name'])
    
    return render_template("fr/cleaning.html", title="Services de nettoyage")

@app.route("/fr/contact")
def fr_contact():
    return render_template("fr/contact.html", title="Contact")

@app.route("/fr/reviews")
def fr_reviews():
    return render_template("fr/reviews.html", title="Avis")

@app.route("/fr/gallery")
def fr_gallery():
    gallery_folder = os.path.join(app.static_folder, "images/gallery")
    images = [img for img in os.listdir(gallery_folder)
              if img.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))]
    return render_template("fr/gallery.html", images=images, title="Galerie")

@app.route("/fr/why")
def fr_why():
    return render_template("fr/why.html", title="Pourquoi PMG")

# --- Let's Encrypt challenge passthrough ---
@app.route("/.well-known/acme-challenge/<path:filename>")
def certbot_challenge(filename):
    return send_from_directory(os.path.join(app.root_path, ".well-known/acme-challenge"), filename)

# Optional local run
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=False)
