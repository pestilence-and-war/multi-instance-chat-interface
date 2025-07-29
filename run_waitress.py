from waitress import serve
import app
from dotenv import load_dotenv

serve(app.app, host='0.0.0.0', port=5000, threads=8)
load_dotenv()