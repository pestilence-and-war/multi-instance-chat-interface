import json
import os
import requests
import time
import logging
from typing import Optional
from chat_manager import chat_manager

logger = logging.getLogger(__name__)

def inspect_image_url(url: str, query: str = "Describe this image in detail, focusing on style, colors, and subject matter.", instance=None) -> str:
    """
    (High-Cost) Downloads an image from a URL and uses the current model's vision capabilities 
    to analyze it. This allows agents to 'see' and verify sourced assets.
    
    @param url (string): The direct URL to the image file. REQUIRED.
    @param query (string): The question or instruction for the vision analysis.
    @param instance (object): INTERNAL. The calling ChatInstance. DO NOT provide this manually.
    """
    logger.info(f"Inspecting image at URL: {url}")
    
    # 1. Inherit Model and Provider from parent
    if instance and instance.api_client:
        provider_name = instance.api_client_class_name.replace('Client', '')
        model_name = instance.selected_model
    else:
        provider_name = "Ollama"
        model_name = "gpt-oss:20b"
        logger.warning("No parent instance found for vision. Falling back to defaults.")

    temp_image_path = None
    spec_instance = None
    
    try:
        # 2. Download the image
        response = requests.get(url, timeout=15, stream=True)
        response.raise_for_status()
        
        # --- NEW: MIME-Type Validation ---
        content_type = response.headers.get('Content-Type', '').lower()
        if 'image' not in content_type:
            return json.dumps({
                "status": "error", 
                "message": f"The URL provided is not a direct image (Content-Type: {content_type}). It may be a landing page. Please provide a direct link to the image file."
            })

        # Ensure 'chat_sessions' folder exists for temporary files
        upload_folder = 'chat_sessions'
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
        # Create a unique temporary filename
        ext = url.split('.')[-1].split('?')[0].lower()
        if ext not in ['jpg', 'jpeg', 'png', 'webp']:
            ext = 'jpg'
        
        filename = f"vision_tmp_{int(time.time()*1000)}.{ext}"
        temp_image_path = os.path.join(upload_folder, filename)
        
        with open(temp_image_path, 'wb') as f:
            f.write(response.content)
        
        # 3. Create a temporary ChatInstance for the vision call
        spec_instance = chat_manager.create_instance(provider_name=provider_name)
        if not spec_instance:
             return json.dumps({"status": "error", "message": "Failed to create vision instance."})

        spec_instance.name = "VISION_INSPECTOR"
        spec_instance.set_config(
            system_prompt="You are a Vision Analyst. Analyze the attached image and answer the user's query accurately.",
            model=model_name,
            temp=0.1 # Low temperature for factual visual analysis
        )
        
        # 4. Attach the image to the temporary instance
        # The API clients look for files in instance._latest_uploaded_files
        file_info = {
            'filename': filename,
            'path': temp_image_path,
            'mimetype': f'image/{ext}' if ext != 'jpg' else 'image/jpeg'
        }
        spec_instance._latest_uploaded_files = [file_info]
        
        # 5. Execute the vision task
        result = spec_instance.execute_headless_turn(query)
        
        if result['status'] == 'success':
            return json.dumps({
                "status": "success",
                "analysis": result['content'],
                "url": url
            }, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "message": result['content']
            }, indent=2)

    except Exception as e:
        logger.error(f"Vision Error: {e}")
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        # 6. Cleanup
        if spec_instance:
            chat_manager.remove_instance(spec_instance.instance_id)
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.remove(temp_image_path)
            except: pass
