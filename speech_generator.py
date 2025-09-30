import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import json
import wave
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

class SpeechGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Speech Generator")
        self.root.geometry("800x600")

        # The list of voices you provided
        self.available_voices = [
            'Zephyr', 'Kore', 'Orus', 'Autonoe', 'Umbriel', 'Puck', 'Fenrir',
            'Aoede', 'Enceladus', 'Algieba', 'Charon', 'Leda', 'Callirrhoe',
            'Iapetus', 'Despina'
        ]

        # --- UI Elements ---
        self.conversation_label = ttk.Label(root, text="Select Conversation:")
        self.conversation_label.pack(pady=5)
        self.conversation_var = tk.StringVar()
        self.conversation_dropdown = ttk.Combobox(root, textvariable=self.conversation_var, state="readonly")
        self.conversation_dropdown.pack(pady=5, padx=10, fill=tk.X)
        self.conversation_dropdown.bind("<<ComboboxSelected>>", self.load_conversation)

        self.editor_label = ttk.Label(root, text="Conversation Content (User and Assistant only):")
        self.editor_label.pack(pady=5)
        self.editor = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=15)
        self.editor.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.voices_frame = ttk.LabelFrame(root, text="Voice Assignments")
        self.voices_frame.pack(pady=10, padx=10, fill=tk.X)
        self.voice_comboboxes = {}

        self.generate_button = ttk.Button(root, text="Generate Speech", command=self.generate_speech)
        self.generate_button.pack(pady=20)

        # --- Initialization ---
        self.populate_conversations()

    def populate_conversations(self):
        try:
            chat_sessions_dir = "chat_sessions"
            if not os.path.exists(chat_sessions_dir):
                messagebox.showerror("Error", "The 'chat_sessions' directory was not found.")
                return
            
            json_files = [f for f in os.listdir(chat_sessions_dir) if f.endswith('.json')]
            self.conversation_dropdown['values'] = json_files
            if json_files:
                self.conversation_var.set(json_files[0])
                self.load_conversation()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load conversations: {e}")

    def load_conversation(self, event=None):
        filename = self.conversation_var.get()
        if not filename: return

        try:
            filepath = os.path.join("chat_sessions", filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            chat_history = data.get("chat_history", [])
            
            conversation_text = ""
            speakers = set()
            for message in chat_history:
                role = message.get("role", "unknown").lower()
                # Filter for only user and assistant roles
                if role in ["user", "assistant"]:
                    content = message.get("content", "")
                    if content:
                        # Using capitalize() for speaker names to match later logic
                        conversation_text += f"{role.capitalize()}: {content}\n\n"
                        speakers.add(role)
            
            self.editor.delete('1.0', tk.END)
            self.editor.insert('1.0', conversation_text)
            
            self.setup_voice_inputs(speakers)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read or parse {filename}: {e}")

    def setup_voice_inputs(self, speakers):
        for widget in self.voices_frame.winfo_children():
            widget.destroy()
        self.voice_comboboxes = {}

        # Assign a default voice to each speaker
        for i, speaker in enumerate(sorted(list(speakers))):
            frame = ttk.Frame(self.voices_frame)
            frame.pack(fill=tk.X, padx=5, pady=2)
            
            label = ttk.Label(frame, text=f"Voice for {speaker.capitalize()}:")
            label.pack(side=tk.LEFT, padx=(0, 10))
            
            combo = ttk.Combobox(frame, values=self.available_voices, state="readonly")
            combo.pack(side=tk.LEFT, expand=True, fill=tk.X)
            # Set a different default voice for each speaker to avoid errors
            combo.set(self.available_voices[i % len(self.available_voices)])
            self.voice_comboboxes[speaker] = combo

    def generate_speech(self):
        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                messagebox.showerror("API Key Error", "GOOGLE_API_KEY not found in .env file.")
                return
            
            # The new client will automatically use the GOOGLE_API_KEY from the environment
            client = genai.Client()

            conversation_text = self.editor.get("1.0", tk.END).strip()
            if not conversation_text:
                messagebox.showwarning("Input Error", "Conversation content is empty.")
                return

            # --- REVISED API CALL LOGIC (Sept 2025) ---

            # 1. The prompt includes the instruction for the model.
            prompt = f"This conversation is between two people who are very intregigued by the topic. \n{conversation_text}"
            
            # 2. Build the speaker voice configurations using the `types` module.
            speaker_voice_configs = []
            for speaker, combo in self.voice_comboboxes.items():
                voice_name = combo.get()
                if not voice_name:
                    messagebox.showwarning("Input Error", f"Please select a voice for {speaker.capitalize()}.")
                    return
                
                speaker_config = types.SpeakerVoiceConfig(
                    speaker=speaker.capitalize(),
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                           voice_name=voice_name,
                        )
                    )
                )
                speaker_voice_configs.append(speaker_config)


            # 3. Define the main generation configuration.
            config = types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=speaker_voice_configs
                    )
                )
            )

            # 4. Use the new client to call the correct model.
            response = client.models.generate_content(
               model="gemini-2.5-flash-preview-tts",
               contents=prompt,
               config=config
            )

            # 5. Extract audio data from the response.
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            output_filename = "generated_speech.wav"
            self.save_wave_file(output_filename, audio_data)
            messagebox.showinfo("Success", f"Speech audio saved to {output_filename}")

        except Exception as e:
            messagebox.showerror("API Error", f"An error occurred: {e}")

    def save_wave_file(self, filename, pcm_data, channels=1, rate=24000, sample_width=2):
        """Saves PCM audio data to a WAV file."""
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width) # 2 bytes for 16-bit audio
            wf.setframerate(rate)
            wf.writeframes(pcm_data)

if __name__ == "__main__":
    root = tk.Tk()
    app = SpeechGeneratorApp(root)
    root.mainloop()