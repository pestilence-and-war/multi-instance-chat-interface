from waitress import serve
import app
from dotenv import load_dotenv

import sys
import pprint # Pretty-print, makes the output easier to read

print(f"\n\n--- PYTHON IS SEARCHING THESE PATHS FOR MODULES ---")
pprint.pprint(sys.path)
print("----------------------------------------------------\n\n")

serve(app.app, host='0.0.0.0', port=5000, threads=8)
load_dotenv()