import os
import sys
import uuid
from pathlib import Path

# ===== 1. LOAD ENV FIRST (before anything else) =====
from dotenv import load_dotenv
load_dotenv()

# ===== 2. FIX WORKING DIRECTORY =====
current_dir = os.path.dirname(os.path.abspath(__file__))
expected_dir = os.path.join(os.path.dirname(current_dir), 'backend')
if not current_dir.endswith('backend'):
    print(f"\n[WARN] Warning: Not in backend directory!")
    print(f"   Current: {current_dir}")
    print(f"   Expected: {expected_dir}")
    print(f"   Changing to backend directory...")
    os.chdir(expected_dir)
    current_dir = expected_dir
    print(f"[OK] Changed to: {current_dir}\n")

# ===== 3. NOW IMPORT FLASK AND OTHERS =====
from flask import Flask, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# ===== 4. INITIALIZE FLASK =====
app = Flask(__name__, static_folder='static')

# Initialize JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
jwt = JWTManager(app)

# Configure CORS from env
cors_origins_str = os.getenv('CORS_ORIGINS', 'http://localhost:8000,http://localhost:3000')
cors_origins = [origin.strip() for origin in cors_origins_str.split(',') if origin.strip()]
CORS(app, origins=cors_origins, supports_credentials=True, allow_headers=['Content-Type', 'Authorization'])
print(f"[OK] CORS enabled for {len(cors_origins)} origin(s)\n")

# ===== 5. REGISTER ROUTES =====
try:
    from routes import dish as dish_routes
    app.register_blueprint(dish_routes.bp, url_prefix='/api/dish')
    print("[OK] Dish routes registered")
except Exception as e:
    print(f"[WARN] Could not import dish routes: {e}")

def _register_optional(bp_name, prefix):
    try:
        mod = __import__(f'routes.{bp_name}', fromlist=['bp'])
        if hasattr(mod, 'bp'):
            app.register_blueprint(mod.bp, url_prefix=prefix)
            print(f"[OK] {bp_name} routes registered")
    except Exception:
        pass

_register_optional('grocery', '/api/grocery')
_register_optional('user', '/api/user')
_register_optional('auth', '/api/auth')
_register_optional('tracker', '/api/tracker')
print("[OK] All routes registered successfully\n")

# ===== 6. CREATE STATIC DIRS =====
PDF_RECIPES_DIR = os.path.join(current_dir, 'static', 'pdfs', 'recipes')
PDF_ING_DIR = os.path.join(current_dir, 'static', 'pdfs', 'ingredients')
os.makedirs(PDF_RECIPES_DIR, exist_ok=True)
os.makedirs(PDF_ING_DIR, exist_ok=True)
print(f"[OK] PDF directories initialized\n")

# ===== 7. MONGODB CONNECTION (PyMongo + MongoEngine) =====
try:
    from config import Config
    import pymongo
    import mongoengine
    
    mongo_uri = Config.MONGO_URI or os.getenv('MONGO_URI')
    if mongo_uri and 'mongodb' in mongo_uri.lower():
        try:
            # Test connection with PyMongo
            client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            print(f"[OK] MongoDB connected successfully\n")
            
            # Initialize MongoEngine with the URI for ORM operations
            mongoengine.connect(host=mongo_uri)
            print(f"[OK] MongoEngine initialized for ORM operations\n")
        except Exception as db_err:
            print(f"[WARN] MongoDB connection failed (will continue): {db_err}\n")
            print(f"[INFO] Some features like expiry checking will be disabled\n")
    else:
        print("[WARN] No MONGO_URI configured; DB features disabled\n")
except Exception as e:
    print(f"[WARN] Could not check MongoDB: {e}\n")

# ===== 8. START BACKGROUND SCHEDULER =====
try:
    from services.expiry_scheduler import start_scheduler_thread
    print("[SCHEDULER] Starting background scheduler...")
    start_scheduler_thread()
    print("[OK] Food Tracker scheduler initialized\n")
except Exception as e:
    print(f"[WARN] Could not start scheduler: {e}\n")

# ===== 9. HEALTH CHECK ENDPOINT =====
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'NitA API'}), 200


def _missing_keys_response():
    missing = []
    if not os.getenv('SPOONACULAR_API_KEY'):
        missing.append('SPOONACULAR_API_KEY')
    if not (os.getenv('GOOGLE_SEARCH_API_KEY') and os.getenv('GOOGLE_SEARCH_ENGINE_ID')):
        missing.append('GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID')
    if missing:
        return jsonify({
            'error': 'Missing API keys',
            'missing': missing,
            'instructions': 'Set environment variables SPOONACULAR_API_KEY or (GOOGLE_SEARCH_API_KEY + GOOGLE_SEARCH_ENGINE_ID). Optionally set LLM_API_KEY for AI normalization.'
        }), 400
    return None


@app.route('/api/dish/fetch', methods=['POST'])
def fetch_dish():
    data = request.get_json(force=True)
    dish = (data or {}).get('dish_name')
    servings = int((data or {}).get('servings') or 1)
    if not dish:
        return jsonify({'error': 'dish_name is required'}), 400

    # If no provider keys at all, return a helpful message instead of failing silently
    if not (os.getenv('SPOONACULAR_API_KEY') or (os.getenv('GOOGLE_SEARCH_API_KEY') and os.getenv('GOOGLE_SEARCH_ENGINE_ID'))):
        return _missing_keys_response()

    # Try to use the existing recipe_service which implements multi-strategy fetching
    try:
        try:
            from services.recipe_service import RecipeService
        except Exception:
            from backend.services.recipe_service import RecipeService
        svc = RecipeService()
        recipe = svc.fetch_recipe(dish)
    except EnvironmentError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': 'Failed to fetch recipe', 'detail': str(e)}), 500

    # Important: DO NOT write recipe into MongoDB automatically. Return runtime-only object.
    return jsonify({'recipe': recipe}), 200


@app.route('/api/dish/generate_pdf', methods=['POST'])
def generate_pdf():
    data = request.get_json(force=True)
    dish = (data or {}).get('dish_name')
    servings = int((data or {}).get('servings') or 1)
    include_grocery = bool((data or {}).get('include_grocery', False))
    if not dish:
        return jsonify({'error': 'dish_name is required'}), 400

    if not (os.getenv('SPOONACULAR_API_KEY') or (os.getenv('GOOGLE_SEARCH_API_KEY') and os.getenv('GOOGLE_SEARCH_ENGINE_ID'))):
        return _missing_keys_response()

    # Use the existing recipe_service implementation to fetch and normalize
    try:
        try:
            from services.recipe_service import RecipeService
        except Exception:
            from backend.services.recipe_service import RecipeService
        svc = RecipeService()
        recipe_dict = svc.fetch_recipe(dish)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch recipe for PDF', 'detail': str(e)}), 500

    # Create a simple runtime object expected by the PDF generator
    recipe_obj = type('R', (), {})()
    recipe_obj.dish_name = recipe_dict.get('title') or dish
    recipe_obj.title = recipe_obj.dish_name
    recipe_obj.servings = servings
    recipe_obj.summary = recipe_dict.get('summary') or recipe_dict.get('description')
    recipe_obj.ingredients = recipe_dict.get('ingredients') or recipe_dict.get('ingredientLines') or []
    # Ensure ingredients are objects with name/quantity/unit where possible
    norm_ings = []
    for ing in recipe_obj.ingredients:
        I = type('I', (), {})()
        if isinstance(ing, dict):
            I.name = ing.get('name') or ing.get('original') or str(ing)
            I.quantity = ing.get('amount') or ing.get('quantity') or None
            I.unit = ing.get('unit') or ''
        else:
            I.name = str(ing)
            I.quantity = None
            I.unit = ''
        norm_ings.append(I)
    recipe_obj.ingredients = norm_ings
    recipe_obj.instructions = recipe_dict.get('steps') or recipe_dict.get('instructions') or []
    recipe_obj.nutrition = recipe_dict.get('nutrition') or recipe_dict.get('nutritionPerServing') or {}

    # Produce a simple PDF using reportlab (installed in venv). Keep content minimal and dynamic.
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception:
        return jsonify({'error': 'reportlab is required to generate PDFs. Install it in your environment.'}), 500

    filename = f"recipe_steps_{secure_filename(recipe_obj.dish_name or 'recipe')}_{uuid.uuid4().hex[:8]}.pdf"
    path = os.path.join(PDF_RECIPES_DIR, filename)

    try:
        c = canvas.Canvas(path, pagesize=letter)
        width, height = letter
        y = height - 50
        c.setFont('Helvetica-Bold', 18)
        c.drawString(50, y, recipe_obj.title or recipe_obj.dish_name)
        y -= 30
        c.setFont('Helvetica', 11)
        c.drawString(50, y, f"Servings: {recipe_obj.servings}")
        y -= 20

        if recipe_obj.summary:
            c.setFont('Helvetica-Oblique', 10)
            c.drawString(50, y, str(recipe_obj.summary)[:200])
            y -= 30

        c.setFont('Helvetica-Bold', 14)
        c.drawString(50, y, 'Ingredients:')
        y -= 20
        c.setFont('Helvetica', 10)
        for ing in recipe_obj.ingredients:
            line = f"- {ing.quantity or ''} {ing.unit or ''} {ing.name or ''}".strip()
            c.drawString(60, y, line[:90])
            y -= 14
            if y < 80:
                c.showPage()
                y = height - 50

        c.setFont('Helvetica-Bold', 14)
        c.drawString(50, y, 'Instructions:')
        y -= 20
        c.setFont('Helvetica', 10)
        for step in recipe_obj.instructions:
            c.drawString(60, y, (step or '')[:100])
            y -= 14
            if y < 80:
                c.showPage()
                y = height - 50

        # Nutrition block
        if recipe_obj.nutrition:
            c.setFont('Helvetica-Bold', 14)
            c.drawString(50, y, 'Nutrition (per serving):')
            y -= 18
            c.setFont('Helvetica', 10)
            for k, v in (recipe_obj.nutrition.items() if isinstance(recipe_obj.nutrition, dict) else []):
                c.drawString(60, y, f"{k}: {v}")
                y -= 14
                if y < 80:
                    c.showPage()
                    y = height - 50

        c.save()
    except Exception as e:
        return jsonify({'error': 'Failed to generate PDF', 'detail': str(e)}), 500

    # Return URL relative to server
    pdf_url = f"/static/pdfs/recipes/{filename}"
    return jsonify({'pdf_url': pdf_url, 'path': path}), 200


@app.route('/static/pdfs/recipes/<path:filename>')
def serve_recipe_pdf(filename):
    return send_from_directory(PDF_RECIPES_DIR, filename)


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Starting AI-Based Smart Food Waste Management API")
    print("="*60)
    print(f"[INFO] Running from: {current_dir}")
    print(f"[INFO] Server listening on: 0.0.0.0:5000 (all interfaces)")
    print(f"[INFO] Access in browser: http://localhost:5000")
    print(f"[INFO] API endpoint: http://localhost:5000/api")
    print(f"[INFO] Health check: http://localhost:5000/api/health")
    print(f"[INFO] CORS enabled for: {cors_origins}")
    print(f"[INFO] Debug mode: {'ON' if app.debug else 'OFF'}")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
