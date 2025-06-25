from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security.utils import get_authorization_scheme_param
from pydantic import BaseModel
import json
import os
import asyncio
import tempfile
import uuid
from datetime import datetime
from typing import List, Optional
import logging
import ssl
import socket
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from ipaddress import ip_address
import datetime

# Voice processing imports
import edge_tts
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI()

app = FastAPI(title="Smart Shopping List API with Voice")

# SSL Certificate paths
SSL_DIR = "ssl_certs"
CERT_FILE = os.path.join(SSL_DIR, "cert.pem")
KEY_FILE = os.path.join(SSL_DIR, "key.pem")


def get_local_ip():
    """Get the local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def generate_ssl_certificate():
    """Generate self-signed SSL certificate using Python cryptography library"""
    os.makedirs(SSL_DIR, exist_ok=True)

    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        logger.info("SSL certificates already exist")
        return True

    try:
        local_ip = get_local_ip()
        logger.info(f"Generating SSL certificate for local IP: {local_ip}")

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Create certificate subject
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "IL"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Local"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Smart Shopping List"),
            x509.NameAttribute(NameOID.COMMON_NAME, local_ip),
        ])

        # Create certificate
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            # Certificate valid for 1 year
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("*.local"),
                x509.IPAddress(ip_address("127.0.0.1")),
                x509.IPAddress(ip_address(local_ip)),
            ]),
            critical=False,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
            ]),
            critical=True,
        ).sign(private_key, hashes.SHA256())

        # Write private key to file
        with open(KEY_FILE, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        # Write certificate to file
        with open(CERT_FILE, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        logger.info("SSL certificate generated successfully using Python cryptography")
        logger.info(f"Certificate: {CERT_FILE}")
        logger.info(f"Private key: {KEY_FILE}")
        logger.info(f"Valid for: localhost, *.local, 127.0.0.1, {local_ip}")
        return True

    except Exception as e:
        logger.error(f"Error generating SSL certificate: {e}")
        return False


def check_ssl_requirements():
    """Check if SSL certificates exist or can be generated"""
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        return True

    # Try to generate certificates
    return generate_ssl_certificate()


# Data models
class ShoppingItem(BaseModel):
    id: str
    name: str
    quantity: str
    completed: bool = False
    created_at: str
    tag: str = "אחר"  # Default tag


class AddItemRequest(BaseModel):
    name: str
    quantity: str = "1"
    tag: str = "אחר"  # Optional tag


class ToggleItemRequest(BaseModel):
    item_id: str


class RemoveItemRequest(BaseModel):
    item_id: str


class ShoppingListResponse(BaseModel):
    items: List[ShoppingItem]
    last_modified: str


class TagStatsResponse(BaseModel):
    tag: str
    count: int
    completed_count: int


class TextToSpeechRequest(BaseModel):
    text: str


# Predefined categories in Hebrew
PREDEFINED_TAGS = [
    "חלב ומוצרי חלב",
    "בשר ודגים",
    "ירקות",
    "פירות",
    "לחם ומאפים",
    "משקאות",
    "חטיפים וממתקים",
    "מוצרי בית",
    "קפואים",
    "תבלינים ורטבים",
    "דגנים וקטניות",
    "אחר"
]


def categorize_item_simple(item_name: str) -> str:
    """Simple item categorization"""
    item_lower = item_name.lower()

    # Dairy products
    if any(word in item_lower for word in ["חלב", "גבינה", "יוגורט", "קוטג", "חמאה", "שמנת"]):
        return "חלב ומוצרי חלב"

    # Fruits
    elif any(word in item_lower for word in ["בננה", "תפוח", "תפוז", "ענב", "תות", "מלון", "אבטיח", "מנגו"]):
        return "פירות"

    # Vegetables
    elif any(word in item_lower for word in ["עגבני", "מלפפון", "חסה", "גזר", "בצל", "פלפל", "ברוקולי"]):
        return "ירקות"

    # Bread and bakery
    elif any(word in item_lower for word in ["לחם", "פיתה", "בגט", "חלה", "עוגה"]):
        return "לחם ומאפים"

    # Beverages
    elif any(word in item_lower for word in ["מים", "מיץ", "קולה", "בירה", "יין", "קפה", "תה"]):
        return "משקאות"

    # Meat and fish
    elif any(word in item_lower for word in ["בשר", "עוף", "דג", "נקניק", "קציצ", "טונה"]):
        return "בשר ודגים"

    else:
        return "אחר"


def auto_categorize_item(item_name: str) -> str:
    """Return default category - agent will handle intelligent categorization"""
    return categorize_item_simple(item_name)


# File paths
SHOPPING_LIST_FILE = "static2/shopping_list.json"
STATIC_DIR = "static"
AUDIO_DIR = "static2/audio"

# Ensure directories exist
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)


def ensure_static_files():
    """Ensure all required static files exist"""
    generic_image_path = os.path.join(STATIC_DIR, "generic-product.png")
    if not os.path.exists(generic_image_path):
        import base64
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
        with open(generic_image_path, 'wb') as f:
            f.write(png_data)
        logger.info("Created generic-product.png")


ensure_static_files()


def load_shopping_list():
    """Load shopping list from JSON file"""
    try:
        if os.path.exists(SHOPPING_LIST_FILE):
            with open(SHOPPING_LIST_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure all items have tags
                for item in data.get("items", []):
                    if "tag" not in item:
                        item["tag"] = auto_categorize_item(item.get("name", ""))
                return data
        else:
            empty_list = {
                "items": [],
                "last_modified": datetime.now().isoformat()
            }
            save_shopping_list(empty_list)
            return empty_list
    except Exception as e:
        logger.error(f"Error loading shopping list data: {e}")
        return {
            "items": [],
            "last_modified": datetime.now().isoformat()
        }


def save_shopping_list(data):
    """Save shopping list to JSON file"""
    try:
        data["last_modified"] = datetime.now().isoformat()
        with open(SHOPPING_LIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Shopping list data saved successfully")
        return True
    except Exception as e:
        logger.error(f"Error saving shopping list data: {e}")
        return False


# ============================================================================
# VOICE PROCESSING UTILITIES
# ============================================================================

def is_likely_false_positive(transcription: str) -> bool:
    """Check if transcription is likely a false positive/hallucination"""
    if not transcription or not transcription.strip():
        return True

    # Common false positives that Whisper tends to hallucinate
    false_positives = [
        "תודה",
        "תודה רבה",
        "אחד",
        "שני",
        "שלום",
        "כן",
        "לא",
        "מה",
        "איך",
        "בוקר טוב",
        "לילה טוב",
        "מצטער",
        "סליחה"
    ]

    clean_text = transcription.strip().lower()

    # Check if it's exactly a false positive
    if clean_text in [fp.lower() for fp in false_positives]:
        return True

    # Check if it's too short (likely hallucination)
    if len(clean_text) < 3:
        return True

    return False


def clean_text_for_tts(text: str) -> str:
    """Clean text for TTS by removing markdown and formatting"""
    if not text:
        return text

    # Remove markdown formatting
    text = text.replace('**', '')  # Bold
    text = text.replace('*', '')  # Italics/emphasis
    text = text.replace('__', '')  # Underline
    text = text.replace('_', '')  # Underline single
    text = text.replace('```', '')  # Code blocks
    text = text.replace('`', '')  # Inline code
    text = text.replace('#', '')  # Headers
    text = text.replace('>', '')  # Blockquotes
    text = text.replace('[', '')  # Link brackets
    text = text.replace(']', '')  # Link brackets
    text = text.replace('(', '')  # Link parentheses
    text = text.replace(')', '')  # Link parentheses

    # Remove excessive whitespace
    text = ' '.join(text.split())

    # Remove bullet points and special characters that sound bad in TTS
    text = text.replace('•', '')
    text = text.replace('○', '')
    text = text.replace('◦', '')
    text = text.replace('–', '-')
    text = text.replace('—', '-')

    return text.strip()


# ============================================================================
# SECURITY MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def security_headers_middleware(request, call_next):
    """Add basic security headers"""
    response = await call_next(request)

    # Basic security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # For HTTPS only (will be ignored on HTTP)
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


# ============================================================================
# VOICE PROCESSING ENDPOINTS
# ============================================================================

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe uploaded audio to Hebrew text using OpenAI Whisper"""
    temp_file_path = None
    try:
        logger.info(f"Received audio file: {file.filename}, content_type: {file.content_type}")

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            temp_file_path = temp_file.name

            logger.info(f"Temporary file created: {temp_file_path}, size: {len(content)} bytes")

        # Transcribe using OpenAI Whisper (file is now closed)
        with open(temp_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="he"  # Hebrew language
            )

        transcribed_text = transcription.text
        logger.info(f"Transcription successful: {transcribed_text}")

        # Check for false positives
        if is_likely_false_positive(transcribed_text):
            logger.info(f"Filtered out false positive: {transcribed_text}")
            return {
                "success": True,
                "transcription": "",  # Return empty to indicate false positive
                "message": "False positive filtered out",
                "filtered": True
            }

        return {
            "success": True,
            "transcription": transcribed_text,
            "message": "Audio transcribed successfully",
            "filtered": False
        }

    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        # Clean up temp file with better error handling
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                import time
                time.sleep(0.1)  # Small delay to ensure file is released
                os.unlink(temp_file_path)
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Could not delete temporary file {temp_file_path}: {cleanup_error}")
                # File will be cleaned up by system temp cleanup eventually


@app.post("/api/text-to-speech")
async def text_to_speech(request: TextToSpeechRequest):
    """Convert Hebrew text to speech using edge-tts"""
    try:
        text = request.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")

        # Clean text for TTS
        clean_text = clean_text_for_tts(text)
        logger.info(f"Generating TTS for cleaned text: {clean_text}")

        # Generate unique filename
        audio_filename = f"response_{uuid.uuid4().hex[:8]}.mp3"
        audio_path = os.path.join(AUDIO_DIR, audio_filename)

        # Generate TTS using edge-tts with Hebrew voice
        voice = "he-IL-HilaNeural"  # Female Hebrew voice
        # Alternative: "he-IL-AvriNeural" for male voice

        communicate = edge_tts.Communicate(clean_text, voice)
        await communicate.save(audio_path)

        logger.info(f"TTS generated successfully: {audio_filename}")

        return {
            "success": True,
            "audio_url": f"/static/audio/{audio_filename}",
            "text": clean_text,
            "original_text": text,
            "message": "TTS generated successfully"
        }

    except Exception as e:
        logger.error(f"Error generating TTS: {e}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@app.post("/api/voice-command")
async def process_voice_command(file: UploadFile = File(...)):
    """Process voice command end-to-end: STT -> Agent -> TTS"""
    temp_file_path = None
    try:
        logger.info("Processing voice command...")

        # Step 1: Transcribe audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            temp_file_path = temp_file.name

            logger.info(f"Audio file size: {len(content)} bytes")

        # Transcribe using OpenAI Whisper (file is now closed)
        with open(temp_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="he"
            )

        transcribed_text = transcription.text.strip()
        logger.info(f"Voice command transcribed: {transcribed_text}")

        if not transcribed_text:
            return {
                "success": False,
                "error": "לא הצלחתי לשמוע פקודה ברורה",
                "transcription": "",
                "response": "לא הצלחתי לשמוע פקודה ברורה. אנא נסה שוב."
            }

        # Step 2: Process with shopping agent (simplified version for now)
        agent_response = await process_shopping_command(transcribed_text)

        # Step 3: Clean response for TTS (remove markdown formatting)
        clean_response = clean_text_for_tts(agent_response)
        logger.info(f"Cleaned response for TTS: {clean_response}")

        # Step 4: Generate TTS response
        audio_filename = f"voice_response_{uuid.uuid4().hex[:8]}.mp3"
        audio_path = os.path.join(AUDIO_DIR, audio_filename)

        voice = "he-IL-HilaNeural"
        communicate = edge_tts.Communicate(clean_response, voice)
        await communicate.save(audio_path)

        logger.info("Voice command processed successfully")

        return {
            "success": True,
            "transcription": transcribed_text,
            "response": agent_response,
            "audio_url": f"/static/audio/{audio_filename}"
        }

    except Exception as e:
        logger.error(f"Error processing voice command: {e}")
        error_message = "מצטער, לא הצלחתי לעבד את הפקודה. אנא נסה שוב."

        # Generate error TTS
        try:
            audio_filename = f"error_response_{uuid.uuid4().hex[:8]}.mp3"
            audio_path = os.path.join(AUDIO_DIR, audio_filename)
            voice = "he-IL-HilaNeural"

            # Clean error message for TTS
            clean_error_message = clean_text_for_tts(error_message)
            communicate = edge_tts.Communicate(clean_error_message, voice)
            await communicate.save(audio_path)

            return {
                "success": False,
                "error": str(e),
                "transcription": "",
                "response": error_message,
                "audio_url": f"/static/audio/{audio_filename}"
            }
        except:
            raise HTTPException(status_code=500, detail=f"Voice command processing failed: {str(e)}")
    finally:
        # Clean up temp file with better error handling
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                import time
                time.sleep(0.1)  # Small delay to ensure file is released
                os.unlink(temp_file_path)
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Could not delete temporary file {temp_file_path}: {cleanup_error}")
                # File will be cleaned up by system temp cleanup eventually


async def process_shopping_command(command: str) -> str:
    """Process shopping command and return response"""
    try:
        # Import and use shopping agent
        from shopping_agent import SmartShoppingAgent
        agent = SmartShoppingAgent()
        response = agent.process_voice_command(command)
        return response
    except ImportError:
        # Fallback processing if agent is not available
        logger.warning("Shopping agent not available, using fallback processing")
        return await fallback_command_processing(command)
    except Exception as e:
        logger.error(f"Error with shopping agent: {e}")
        return await fallback_command_processing(command)


async def fallback_command_processing(command: str) -> str:
    """Fallback command processing without the full agent"""
    command_lower = command.lower()

    # Simple keyword-based processing
    if any(word in command_lower for word in ["הוסף", "תוסיף", "להוסיף"]):
        # Extract item name (simplified)
        item_name = command.strip()
        for word in ["הוסף", "תוסיף", "להוסיף", "לרשימה", "את", "לי"]:
            item_name = item_name.replace(word, "").strip()

        if item_name:
            # Add item to shopping list
            data = load_shopping_list()
            new_item = {
                "id": str(uuid.uuid4()),
                "name": item_name,
                "quantity": "1",
                "completed": False,
                "created_at": datetime.now().isoformat(),
                "tag": categorize_item_simple(item_name)
            }
            data["items"].append(new_item)

            if save_shopping_list(data):
                return f"הוספתי {item_name} לרשימת הקניות בקטגוריה {new_item['tag']}"
            else:
                return "מצטער, לא הצלחתי להוסיף את הפריט"
        else:
            return "לא הבנתי איזה פריט להוסיף. אנא נסה שוב."

    elif any(word in command_lower for word in ["רשימה", "מה יש", "תראה"]):
        # Show shopping list
        data = load_shopping_list()
        items = data.get("items", [])

        if not items:
            return "רשימת הקניות ריקה כרגע"

        pending_items = [item for item in items if not item.get("completed", False)]
        if not pending_items:
            return "כל הפריטים ברשימה הושלמו"

        item_list = ", ".join([item["name"] for item in pending_items[:5]])
        if len(pending_items) > 5:
            return f"יש לך {len(pending_items)} פריטים ברשימה: {item_list} ועוד"
        else:
            return f"יש לך {len(pending_items)} פריטים ברשימה: {item_list}"

    else:
        return "לא הבנתי את הפקודה. תוכל לומר 'הוסף' ושם הפריט, או 'תראה לי את הרשימה'"


# ============================================================================
# EXISTING SHOPPING LIST ENDPOINTS
# ============================================================================

@app.get("/static/{file_path:path}")
async def serve_static(file_path: str):
    """Custom static file handler with better error handling"""
    full_path = os.path.join(STATIC_DIR, file_path)

    if os.path.exists(full_path) and os.path.isfile(full_path):
        return FileResponse(full_path)
    else:
        logger.warning(f"Static file not found: {file_path}")
        if file_path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
            generic_path = os.path.join(STATIC_DIR, "generic-product.png")
            if os.path.exists(generic_path):
                return FileResponse(generic_path)
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")


@app.get("/")
async def read_root():
    """Serve the main HTML page"""
    html_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "index.html not found. Please ensure all static files are in the static/ directory."}
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/shopping-list", response_model=ShoppingListResponse)
async def get_shopping_list():
    """Get the current shopping list"""
    try:
        data = load_shopping_list()
        return ShoppingListResponse(**data)
    except Exception as e:
        logger.error(f"Error getting shopping list: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/tags")
async def get_tags():
    """Get all available tags/categories"""
    return {"tags": PREDEFINED_TAGS}


@app.get("/api/shopping-list/by-tag/{tag}")
async def get_shopping_list_by_tag(tag: str):
    """Get shopping list items filtered by tag"""
    try:
        data = load_shopping_list()
        filtered_items = [item for item in data["items"] if item.get("tag", "אחר") == tag]
        return {
            "items": filtered_items,
            "tag": tag,
            "count": len(filtered_items),
            "last_modified": data["last_modified"]
        }
    except Exception as e:
        logger.error(f"Error getting shopping list by tag: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/tag-stats")
async def get_tag_stats():
    """Get statistics for each tag"""
    try:
        data = load_shopping_list()
        tag_stats = {}

        # Initialize all predefined tags
        for tag in PREDEFINED_TAGS:
            tag_stats[tag] = {"count": 0, "completed_count": 0}

        # Count items by tag
        for item in data["items"]:
            tag = item.get("tag", "אחר")
            if tag not in tag_stats:
                tag_stats[tag] = {"count": 0, "completed_count": 0}

            tag_stats[tag]["count"] += 1
            if item.get("completed", False):
                tag_stats[tag]["completed_count"] += 1

        # Convert to list format
        stats = [
            {
                "tag": tag,
                "count": stats["count"],
                "completed_count": stats["completed_count"]
            }
            for tag, stats in tag_stats.items()
            if stats["count"] > 0
        ]

        return {"tag_stats": stats}
    except Exception as e:
        logger.error(f"Error getting tag stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/add-item")
async def add_item(request: AddItemRequest):
    """Add a new item to the shopping list"""
    try:
        data = load_shopping_list()

        # Auto-categorize if no tag provided or tag is default
        tag = request.tag
        if tag == "אחר" or not tag:
            tag = categorize_item_simple(request.name)

        new_item = {
            "id": str(uuid.uuid4()),
            "name": request.name.strip(),
            "quantity": request.quantity.strip(),
            "completed": False,
            "created_at": datetime.now().isoformat(),
            "tag": tag
        }

        data["items"].append(new_item)

        if save_shopping_list(data):
            logger.info(f"Added item: {request.name} with tag: {tag}")
            return {"success": True, "message": "Item added successfully", "item": new_item}
        else:
            raise HTTPException(status_code=500, detail="Failed to save shopping list")

    except Exception as e:
        logger.error(f"Error adding item: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/toggle-item")
async def toggle_item(request: ToggleItemRequest):
    """Toggle the completed status of an item"""
    try:
        data = load_shopping_list()

        for item in data["items"]:
            if item["id"] == request.item_id:
                item["completed"] = not item["completed"]
                break
        else:
            raise HTTPException(status_code=404, detail="Item not found")

        if save_shopping_list(data):
            logger.info(f"Toggled item: {request.item_id}")
            return {"success": True, "message": "Item toggled successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save shopping list")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling item: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/remove-item")
async def remove_item(request: RemoveItemRequest):
    """Remove an item from the shopping list"""
    try:
        data = load_shopping_list()

        original_length = len(data["items"])
        data["items"] = [item for item in data["items"] if item["id"] != request.item_id]

        if len(data["items"]) == original_length:
            raise HTTPException(status_code=404, detail="Item not found")

        if save_shopping_list(data):
            logger.info(f"Removed item: {request.item_id}")
            return {"success": True, "message": "Item removed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save shopping list")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing item: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/clear-list")
async def clear_list():
    """Clear all items from the shopping list"""
    try:
        data = {
            "items": [],
            "last_modified": datetime.now().isoformat()
        }

        if save_shopping_list(data):
            logger.info("Cleared shopping list")
            return {"success": True, "message": "Shopping list cleared successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear shopping list")

    except Exception as e:
        logger.error(f"Error clearing list: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Add CORS middleware for development (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost:8000", "https://127.0.0.1:8000"],  # Restrict to HTTPS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware for basic protection
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.local", get_local_ip()]
)

if __name__ == "__main__":
    import uvicorn

    ensure_static_files()

    required_files = ["index.html", "styles.css", "scripts.js"]
    missing_files = []

    for file in required_files:
        if not os.path.exists(os.path.join(STATIC_DIR, file)):
            missing_files.append(file)

    if missing_files:
        logger.warning(f"Missing static files: {missing_files}")
        logger.info("Server will start but some features may not work properly")

    # Check SSL requirements
    use_ssl = check_ssl_requirements()

    if use_ssl:
        logger.info("Starting Smart Shopping List Server with HTTPS support...")
        logger.info(f"Server will be available at:")
        logger.info(f"  https://localhost:8000")
        logger.info(f"  https://{get_local_ip()}:8000")
        logger.info("Voice endpoints available:")
        logger.info("  POST /api/transcribe - Convert audio to text")
        logger.info("  POST /api/text-to-speech - Convert text to audio")
        logger.info("  POST /api/voice-command - Full voice command processing")
        logger.warning("Using self-signed certificate - browsers will show security warning")
        logger.info("To trust the certificate, add it to your browser or accept the security warning")

        # Run with SSL
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            ssl_keyfile=KEY_FILE,
            ssl_certfile=CERT_FILE,
            ssl_version=ssl.PROTOCOL_TLSv1_2
        )
    else:
        logger.warning("SSL certificates could not be generated - falling back to HTTP")
        logger.warning("Install OpenSSL to enable HTTPS support")
        logger.info("Starting Smart Shopping List Server with HTTP...")
        logger.info(f"Server will be available at:")
        logger.info(f"  http://localhost:8000")
        logger.info(f"  http://{get_local_ip()}:8000")

        # Run without SSL
        uvicorn.run(app, host="0.0.0.0", port=8000)