from chat_instance import ChatInstance
import os
import json
import time
import api_clients

# --- Registry ---

API_CLIENT_CLASSES = {
    "OpenRouter": api_clients.openrouter_client.OpenRouterClient,
    "Google": api_clients.google_client.GoogleClient,
    "Ollama": api_clients.ollma_client.OllamaClient,
    # "OpenAI": openai_client.OpenAIClient,
}
DEFAULT_PROVIDER = "Google"
# --- End Registry ---

class ChatManager:
    def __init__(self, save_dir="chat_sessions"):
        self.instances = {} # {instance_id: ChatInstance}
        self.save_dir = save_dir
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

    def create_instance(self, provider_name=None, api_key=None):
        provider_name = provider_name or DEFAULT_PROVIDER
        client_class = API_CLIENT_CLASSES.get(provider_name)

        if not client_class:
             print(f"Error: Provider '{provider_name}' not found.")
             return None # Or raise error

        # If API key not provided, try loading from environment
        if not api_key:
             env_var_name = f"{provider_name.upper().replace('CLIENT','').replace('.','_')}_API_KEY"
             api_key = os.getenv(env_var_name)
             if not api_key:
                  print(f"Warning: API Key for {provider_name} not provided and not found in env var {env_var_name}.")
                  # Allow creating instance without connection? Or fail? Let's allow for now.
                  # return None # Fail if key is absolutely required immediately

        instance = ChatInstance(api_client_class=client_class, api_key=api_key)
        self.instances[instance.instance_id] = instance
        print(f"Created instance: {instance.instance_id} with {provider_name if instance.api_client else 'NO Connection'}")
        return instance

    def get_instance(self, instance_id) -> ChatInstance | None:
        return self.instances.get(instance_id)
    
    def get_all_instances_sorted(self) -> list[ChatInstance]:
        """
        Returns a list of all chat instances, sorted by last_used time descending.
        """
        if not self.instances:
            return []
        
        # Sort the dictionary items by the 'last_used' attribute of the ChatInstance object
        sorted_instances = sorted(
            self.instances.values(), 
            key=lambda instance: instance.last_used, 
            reverse=True
        )
        return sorted_instances

    def get_all_instance_ids(self): # This method is now used less
        return list(self.instances.keys())

    def get_all_instance_ids(self):
        return list(self.instances.keys())

    def remove_instance(self, instance_id):
        instance = self.instances.pop(instance_id, None)
        if instance:
            instance.stop_generation()
            instance.save_edit_log()
            print(f"Removed instance: {instance_id}")
        return instance is not None

    def save_instance_state(self, instance_id):
         instance = self.get_instance(instance_id)
         if not instance:
             print(f"Save failed: Instance {instance_id} not found.")
             return None

         try:
             state = instance.get_state()
             filename = os.path.join(self.save_dir, f"{instance_id}.json")
             with open(filename, 'w', encoding='utf-8') as f:
                 json.dump(state, f, indent=2)
             print(f"Saved instance {instance_id} to {filename}")
             return filename
         except Exception as e:
             print(f"Error saving instance {instance_id}: {e}")
             return None

    def load_instance_state(self, filename):
        try:
            filepath = os.path.join(self.save_dir, filename)
            if not os.path.exists(filepath):
                print(f"Load failed: File not found {filepath}")
                return None

            with open(filepath, 'r', encoding='utf-8') as f:
                state = json.load(f)

            # Use the factory method on ChatInstance
            instance = ChatInstance.from_state(state, API_CLIENT_CLASSES)

            # Attempt to reconnect if not connected
            if not instance.api_client and instance.api_client_class_name:
                client_class = None
                # Map class name back to provider key
                for provider_name, cls in API_CLIENT_CLASSES.items():
                    if cls.__name__ == instance.api_client_class_name:
                        client_class = cls
                        break
                if client_class:
                    env_var_name = f"{provider_name.upper().replace('CLIENT','').replace('.','_')}_API_KEY"
                    api_key = os.getenv(env_var_name)
                    if api_key:
                        print(f"Reconnecting loaded instance {instance.instance_id} with {provider_name}")
                        instance.connect(client_class, api_key)
                    else:
                        print(f"No API key found in env for {provider_name}, cannot reconnect {instance.instance_id}")
                else:
                    print(f"Client class {instance.api_client_class_name} not found in registry for {instance.instance_id}")

            if instance.instance_id in self.instances:
                print(f"Warning: Overwriting existing instance {instance.instance_id} in memory.")
            self.instances[instance.instance_id] = instance
            print(f"Loaded instance {instance.instance_id} from {filename}")
            return instance
        except Exception as e:
            print(f"Error loading instance from {filename}: {e}")
            return None

    def load_all_instances(self):
         """Loads all .json files from the save directory."""
         loaded_count = 0
         for filename in os.listdir(self.save_dir):
             if filename.endswith(".json"):
                 if self.load_instance_state(filename):
                     loaded_count += 1
         print(f"Loaded {loaded_count} instances from {self.save_dir}")


# Global instance
chat_manager = ChatManager()
# Load existing sessions on startup
chat_manager.load_all_instances()