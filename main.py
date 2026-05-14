# ==============================================================================
# VIP HUMAN GOD - REAL ACCOUNT AI SYSTEM
# SINGLE-FILE ARCHITECTURE | TERMUX + RENDER READY
# ==============================================================================

import os
import json
import time
import random
import asyncio
import re
import sys
from datetime import datetime
import aiohttp
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import User
import colorama
from colorama import Fore, Style, Back

colorama.init(autoreset=True)

# ---------------------------------------------------------
# [1] ENVIRONMENT & CORE CONFIG
# ---------------------------------------------------------
CONFIG_FILE = "config.json"
SESSION_NAME = "vip_human_god"

DEFAULT_CONFIG = {
    "api_id": "",
    "api_hash": "",
    "phone": "",
    "openrouter_key": "",
    "ai_model": "mistralai/mistral-7b-instruct",
    "targets": [],
    "memory": {},
    "is_render": os.environ.get("RENDER", "false").lower() == "true"
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

config = load_config()

# ---------------------------------------------------------
# [2] MEMORY ENGINE
# ---------------------------------------------------------
class MemoryEngine:
    @staticmethod
    def add_context(user_id, role, text):
        user_id = str(user_id)
        if user_id not in config["memory"]:
            config["memory"][user_id] = []
        
        config["memory"][user_id].append({"role": role, "content": text})
        
        # Keep only last 15 messages to save tokens
        if len(config["memory"][user_id]) > 15:
            config["memory"][user_id].pop(0)
        save_config(config)

    @staticmethod
    def get_context(user_id):
        return config["memory"].get(str(user_id), [])

# ---------------------------------------------------------
# [3] AI ENGINE & OPENROUTER
# ---------------------------------------------------------
class AIEngine:
    SYSTEM_PROMPT = """You are a real human from Bangladesh chatting on Telegram. 
Rules:
1. NEVER reveal you are an AI, chatbot, program, or language model.
2. Speak exactly like a normal human (mix of Bengali and English).
3. Use casual emojis occasionally.
4. Keep replies short and natural like a text message.
5. If someone asks "Are you AI?", act confused or mock them playfully."""

    @staticmethod
    async def generate_reply(user_id, text):
        # 1. Mandatory Replies Check
        mandatory_checks = {
            "আমি তোমার সাথে কথা বলে চাই": "এখন কল করা সম্ভব না 🙂 এখানে কথা বলো",
            "why this is ai not a real human": "তুমি যেভাবে কথা বলতে চাও সেভাবেই কথা বলছি ✨",
            "আমি তোমার সাথে দেখতা করতে চাই": "এখন দেখা করা সম্ভব না 😄 তবে কথা বলতে পারো"
        }
        
        lower_text = text.lower()
        for key, reply in mandatory_checks.items():
            if key in lower_text:
                return reply

        # 2. OpenRouter API Call
        context = MemoryEngine.get_context(user_id)
        messages = [{"role": "system", "content": AIEngine.SYSTEM_PROMPT}] + context
        messages.append({"role": "user", "content": text})

        headers = {
            "Authorization": f"Bearer {config['openrouter_key']}",
            "HTTP-Referer": "https://github.com/viphuman",
            "X-Title": "VIP Human God"
        }
        
        payload = {
            "model": config["ai_model"],
            "messages": messages,
            "max_tokens": 150,
            "temperature": 0.7
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload) as resp:
                    data = await resp.json()
                    reply = data['choices'][0]['message']['content']
                    
                    # Safety check to prevent AI breakdown
                    bad_words = ["I am an AI", "language model", "OpenAI", "I'm a virtual"]
                    if any(bad in reply for bad in bad_words):
                        return "আমি এখন একটু ব্যস্ত আছি, পরে কথা বলি 😅"
                    
                    MemoryEngine.add_context(user_id, "user", text)
                    MemoryEngine.add_context(user_id, "assistant", reply)
                    return reply
        except Exception as e:
            return "নেট প্রবলেম করছে মনে হয়... মেসেজ যাচ্ছে না ঠিকমতো 🥲"

# ---------------------------------------------------------
# [4] HUMAN BEHAVIOR SIMULATOR
# ---------------------------------------------------------
class HumanSimulator:
    @staticmethod
    async def simulate(client, chat, text):
        # 1. Seen Simulation (Wait before reading)
        read_delay = min(len(text) * 0.05, 3.0)
        await asyncio.sleep(read_delay)
        await client.send_read_acknowledge(chat)

        # 2. Typing Simulation
        async with client.action(chat, 'typing'):
            type_delay = min(len(text) * 0.08, 5.0)
            await asyncio.sleep(type_delay)

# ---------------------------------------------------------
# [5] TASK MANAGER (RANDOM MESSAGES)
# ---------------------------------------------------------
async def random_human_pings(client):
    greetings = [
        "কি করো?",
        "ঘুমাও নাই এখনো?",
        "আজকে দিন কেমন গেল?",
        "খাইছো?",
        "তোমার সাথে কথা বলতে ভালো লাগে"
    ]
    
    while True:
        # Delay between 15 mins to 3 hours
        delay = random.randint(15 * 60, 180 * 60)
        await asyncio.sleep(delay)
        
        if not config["targets"]:
            continue
            
        target = random.choice(config["targets"])
        msg = random.choice(greetings)
        
        try:
            entity = await client.get_entity(int(target))
            await HumanSimulator.simulate(client, entity, msg)
            await client.send_message(entity, msg)
            MemoryEngine.add_context(target, "assistant", msg)
            print(f"[{Fore.GREEN}TASK{Style.RESET_ALL}] Random message sent to {target}")
        except Exception as e:
            print(f"[{Fore.RED}ERROR{Style.RESET_ALL}] Random task failed: {e}")

# ---------------------------------------------------------
# [6] MAIN TELETHON LOGIC
# ---------------------------------------------------------
async def run_bot():
    if not config["api_id"] or not config["api_hash"]:
        print(f"{Fore.RED}API ID and Hash missing! Go to settings.{Style.RESET_ALL}")
        return

    client = TelegramClient(SESSION_NAME, config["api_id"], config["api_hash"])
    
    # Event Handler
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        sender = await event.get_sender()
        if not event.is_private or sender.bot:
            return
            
        user_id = str(event.chat_id)
        if user_id not in config["targets"]:
            return # Only reply to allowed targets

        text = event.raw_text
        print(f"\n[{Fore.CYAN}IN{Style.RESET_ALL}] {sender.first_name}: {text}")

        # AI Generate
        reply_text = await AIEngine.generate_reply(user_id, text)
        
        # Human Action
        await HumanSimulator.simulate(client, event.chat_id, reply_text)
        
        # Send Reply
        await event.reply(reply_text)
        print(f"[{Fore.GREEN}OUT{Style.RESET_ALL}] You: {reply_text}")

    # Login Logic
    print(f"{Fore.YELLOW}Connecting to Telegram...{Style.RESET_ALL}")
    await client.connect()
    
    if not await client.is_user_authorized():
        print(f"{Fore.YELLOW}Authorization required.{Style.RESET_ALL}")
        if config["is_render"]:
            print(f"{Fore.RED}Cannot authenticate in Render! Generate session.session locally first.{Style.RESET_ALL}")
            sys.exit(1)
            
        await client.send_code_request(config["phone"])
        try:
            otp = input(f"{Fore.CYAN}Enter Telegram OTP: {Style.RESET_ALL}")
            await client.sign_in(config["phone"], otp)
        except SessionPasswordNeededError:
            pwd = input(f"{Fore.CYAN}Enter 2FA Password: {Style.RESET_ALL}")
            await client.sign_in(password=pwd)

    print(f"\n{Fore.GREEN}✅ AI SYSTEM ONLINE & LISTENING!{Style.RESET_ALL}")
    
    # Start Random Ping Task
    asyncio.create_task(random_human_pings(client))
    
    # Render Keep-Alive Server (Dummy Web)
    if config["is_render"]:
        app = aiohttp.web.Application()
        app.router.add_get('/', lambda r: aiohttp.web.Response(text="VIP HUMAN GOD ONLINE"))
        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
        await site.start()

    await client.run_until_disconnected()

# ---------------------------------------------------------
# [7] TERMINAL UI ENGINE
# ---------------------------------------------------------
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_menu():
    clear_screen()
    print(f"{Fore.MAGENTA}╔══════════════════════════════════╗")
    print(f"║          {Fore.CYAN}VIP HUMAN GOD{Fore.MAGENTA}           ║")
    print(f"╚══════════════════════════════════╝{Style.RESET_ALL}\n")
    print(f"{Fore.YELLOW}[1] START")
    print(f"[2] AI SETTING")
    print(f"[3] ACCOUNT SETTING")
    print(f"[4] MEMORY")
    print(f"[5] INSTRUCTIONS")
    print(f"[6] SET TARGET (CHAT ONLY)")
    print(f"{Fore.RED}[00] EXIT{Style.RESET_ALL}\n")

def menu_loop():
    if config["is_render"]:
        # Skip UI in Render, directly start
        asyncio.run(run_bot())
        return

    while True:
        show_menu()
        choice = input(f"{Fore.GREEN}Select Option ❯ {Style.RESET_ALL}")

        if choice == '1':
            try:
                asyncio.run(run_bot())
            except KeyboardInterrupt:
                print("\nStopped.")
                
        elif choice == '2':
            print("\n--- AI SETTING ---")
            config["openrouter_key"] = input("Enter OpenRouter API Key: ")
            config["ai_model"] = input(f"Enter Model [{config['ai_model']}]: ") or config['ai_model']
            save_config(config)
            print("✅ AI Setup Done")
            time.sleep(1)
            
        elif choice == '3':
            print("\n--- ACCOUNT SETTING ---")
            config["api_id"] = int(input("Enter api_id: "))
            config["api_hash"] = input("Enter api_hash: ")
            config["phone"] = input("Enter phone number (with country code): ")
            save_config(config)
            print("✅ Account Setup Done")
            time.sleep(1)

        elif choice == '4':
            print("\n--- MEMORY CLEAR ---")
            config["memory"] = {}
            save_config(config)
            print("✅ Memory Wiped Successfully!")
            time.sleep(1)
            
        elif choice == '5':
            print("\n--- INSTRUCTIONS ---")
            print("1. Set Account Settings (API ID/Hash/Phone).")
            print("2. Set AI Settings (OpenRouter Key).")
            print("3. Set Targets (Telegram User IDs).")
            print("4. Press START. It will ask for OTP once.")
            print("5. After first login, a 'vip_human_god.session' file is created.")
            input("\nPress Enter to go back...")

        elif choice == '6':
            print("\n--- SET TARGET ---")
            print("Current Targets:", config["targets"])
            tid = input("Enter Target Telegram User ID (e.g. 123456789): ")
            if tid not in config["targets"]:
                config["targets"].append(tid)
                save_config(config)
                print("✅ Target Added!")
            time.sleep(1)

        elif choice == '00':
            sys.exit()

if __name__ == "__main__":
    menu_loop()