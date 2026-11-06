"""
Kisumu Pharmacy Chatbot
-----------------------
A command-line chatbot that pharmacy staff use to answer common customer
questions consistently: opening hours, which medicines are stocked, how long
prescriptions take, and what's needed for a repeat prescription.

It remembers the whole conversation, so follow-up questions like
"how long will it take?" are understood in context. Replies stream word by
word, and each conversation is saved to the chat_logs folder.

Usage:
    python pharmacy_chatbot.py          # chat; type 'exit' to quit
    python pharmacy_chatbot.py --test   # run the scripted 3-turn memory test

Requirements:
    pip install -r requirements.txt
    A .env file containing:
        ANTHROPIC_API_KEY=your_key_here
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")
# Haiku 5.5 thinks by default and thinking eats max_tokens; turn it off there.
# Other models may reject this setting, so only send it for Haiku.
EXTRA_ARGS = {"thinking": {"type": "disabled"}} if "haiku" in MODEL else {}
MAX_TOKENS = 400
HISTORY_LIMIT = 10          # messages kept in context: last 5 exchanges
LOG_DIR = Path(__file__).with_name("chat_logs")

SYSTEM_PROMPT = """You are the customer assistant for Kisumu Pharmacy. Staff use you to answer
customer questions over the phone and WhatsApp. Be warm, clear and brief (2-4 sentences).
Reply in the language the customer uses (English or Swahili).

=== PHARMACY DETAILS ===
Name: Kisumu Pharmacy
Location: Oginga Odinga Street, opposite Mega Plaza, Kisumu
Phone / WhatsApp: 0722 456 789
Opening hours: Monday-Saturday 8:00 AM - 8:00 PM; Sunday 10:00 AM - 4:00 PM
Closed on public holidays except Christmas Day morning (9:00 AM - 1:00 PM).
Payment: M-Pesa Till 884512, cash, NHIF/SHA and major insurance cards (AAR, Jubilee, Britam, CIC)

=== SERVICES ===
1. Prescription dispensing (new and repeat prescriptions)
2. Over-the-counter medicines and health products
3. Free blood pressure check (walk-in)
4. Blood sugar test - KES 200 (walk-in, results in 5 minutes)
5. Malaria rapid test - KES 300 (results in 20 minutes)
6. Delivery within Kisumu town - KES 150, same day for orders before 5:00 PM
7. Private consultation with the pharmacist (free, about 10 minutes)

=== PRESCRIPTIONS ===
New prescription: ready in about 15-30 minutes while you wait.
If an item must be ordered from the supplier: ready the next working day by 12:00 noon.
Repeat prescription: call or WhatsApp a day ahead and it will be ready for collection.

To collect a REPEAT prescription, bring:
- The original prescription or the doctor's repeat authorisation (valid for 6 months)
- The patient's national ID, or the patient's ID copy if someone else collects
- Insurance or NHIF/SHA card if paying by insurance
Controlled medicines (e.g. strong painkillers, sleeping tablets) always need a NEW
prescription and cannot be repeated.

=== MEDICINES CURRENTLY IN STOCK (sample list) ===
Over the counter: Panadol, Hedex, Ibuprofen, ORS sachets, Piriton, cough syrups, antacids,
vitamins, Coartem (malaria; dispensed after a positive test or with a prescription).
Prescription only (needs a valid prescription): Amoxicillin, Metformin, Amlodipine,
Losartan, Salbutamol inhalers, insulin (kept refrigerated).
If a medicine is not on this list, say staff will check stock and call the customer back.

=== SAFETY RULES (always follow) ===
- Do NOT diagnose, recommend a specific medicine for symptoms, or give doses.
  Say the pharmacist will advise in person or by phone on 0722 456 789.
- Never say prescription-only medicines can be bought without a prescription.
- For emergencies (chest pain, difficulty breathing, heavy bleeding, unconsciousness,
  poisoning), tell them to go to the nearest hospital or call 999 / 112 immediately.
- Only use the facts above. If something isn't covered, say a staff member will confirm.
"""

TEST_CONVERSATION = [
    "Hi, I have a prescription from my doctor for my mother's blood pressure medicine.",
    "How long will it take?",
    "Next month I'll need the same again. What should I bring?",
]


class ChatError(Exception):
    """A problem we can explain to staff in plain English."""


def get_client():
    api_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        sys.exit("No API key found. Add ANTHROPIC_API_KEY=your_key_here to your .env file.")
    return anthropic.Anthropic(api_key=api_key)


def stream_reply(client, messages):
    """Send the conversation and print the reply as it streams. Returns the full text."""
    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
            **EXTRA_ARGS,
        ) as stream:
            parts = []
            for text in stream.text_stream:
                print(text, end="", flush=True)
                parts.append(text)
            print()
            return "".join(parts)
    except anthropic.APIConnectionError:
        raise ChatError("No internet connection. Check your connection and try again.")
    except anthropic.AuthenticationError:
        raise ChatError("API key is wrong or expired. Check your .env file.")
    except anthropic.RateLimitError:
        raise ChatError("Too many requests. Wait 60 seconds and try again.")
    except anthropic.BadRequestError as err:
        if "credit balance" in str(err).lower():
            raise ChatError("Your Anthropic account has no credit. "
                            "Add funds at console.anthropic.com > Billing.")
        raise ChatError(f"The request was rejected: {err.message}")
    except anthropic.NotFoundError:
        raise ChatError(f"Model '{MODEL}' wasn't found. Check CLAUDE_MODEL in your .env file.")
    except anthropic.APIStatusError as err:
        raise ChatError(f"The AI service returned an error ({err.status_code}). Try again shortly.")


class Conversation:
    def __init__(self, client):
        self.client = client
        self.context = []       # what's sent to the AI (rolling window)
        self.transcript = []    # everything said, for the log

    def send(self, user_text):
        self.context.append({"role": "user", "content": user_text})
        print("\nAssistant: ", end="", flush=True)
        try:
            reply = stream_reply(self.client, self.context)
        except ChatError:
            self.context.pop()   # keep user/assistant turns alternating
            raise
        self.context.append({"role": "assistant", "content": reply})
        self.transcript += self.context[-2:]
        if len(self.context) > HISTORY_LIMIT:
            self.context = self.context[-HISTORY_LIMIT:]   # always starts on a user turn
        return reply

    def save_log(self):
        if not self.transcript:
            return None
        LOG_DIR.mkdir(exist_ok=True)
        started = datetime.now()
        path = LOG_DIR / f"chat_{started:%Y%m%d_%H%M%S}.json"
        log = {"date": started.isoformat(timespec="seconds"), "model": MODEL,
               "messages": self.transcript}
        path.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
        return path


def run_test(convo):
    print("Running the 3-turn memory test. Turns 2 and 3 only make sense if turn 1 is remembered.")
    for turn, text in enumerate(TEST_CONVERSATION, 1):
        print(f"\n--- Turn {turn} ---\nYou: {text}")
        convo.send(text)


def run_chat(convo):
    print("Type the customer's question. Type 'exit' to quit.")
    while True:
        try:
            text = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if text.lower() in ("exit", "quit"):
            break
        if not text:
            continue
        try:
            convo.send(text)
        except ChatError as err:
            print(f"\nSorry: {err}")
            if "credit" in str(err) or "API key" in str(err):
                break


def main():
    print("Kisumu Pharmacy Assistant")
    print("-" * 25)
    convo = Conversation(get_client())
    try:
        if "--test" in sys.argv[1:]:
            run_test(convo)
        else:
            run_chat(convo)
    except ChatError as err:
        print(f"\nSorry: {err}")
    path = convo.save_log()
    if path:
        print(f"\nConversation saved to {path.parent.name}/{path.name}")


if __name__ == "__main__":
    main()
