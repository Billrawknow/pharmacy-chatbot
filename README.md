# Kisumu Pharmacy Chatbot

A command-line chatbot that pharmacy staff use to answer customers' common questions quickly and consistently. It covers opening hours, which medicines are stocked, how long prescriptions take, what's needed for a repeat prescription, and the pharmacy's services. It uses Claude (Anthropic API).

## The problem it solves

A small pharmacy in Kisumu gets calls all day with the same questions, and different staff give slightly different answers. With this chatbot, every staff member gives the same accurate answer, taken from one place: the pharmacy's information in the system prompt.

## Features

- **Remembers the conversation.** If a customer says *"I have a prescription"* and later asks *"how long will it take?"*, the chatbot knows they mean the prescription. The full conversation history is sent with every request, because the AI keeps no memory between calls.
- **Streams replies** word by word as they're generated, so staff aren't left waiting for a whole answer.
- **Rolling window:** only the last 10 messages (5 exchanges) are sent to the AI, which keeps the cost of long conversations under control.
- **Conversation logs:** each session is saved as JSON in `chat_logs/`.
- **Safety rules:** it never diagnoses, recommends medicines for symptoms or gives doses (those go to the pharmacist). It never says prescription-only medicines can be bought without a prescription, and it directs emergencies to hospital or 999 / 112.

## Pharmacy information (in the system prompt)

- **Hours:** Mon–Sat 8:00 AM – 8:00 PM, Sun 10:00 AM – 4:00 PM
- **Services:**
  1. Prescription dispensing
  2. Over-the-counter medicines
  3. Free blood pressure check
  4. Blood sugar test (KES 200)
  5. Malaria rapid test (KES 300)
  6. Same-day delivery in Kisumu (KES 150)
  7. Private pharmacist consultation
- **Prescription times:** 15–30 minutes, or the next working day if an item has to be ordered
- **Repeat prescriptions:** bring the original prescription or the doctor's repeat authorisation, the patient's ID, and an insurance card if applicable
- **Stock list:** a sample of over-the-counter and prescription-only medicines

To update any of this, edit `SYSTEM_PROMPT` in `pharmacy_chatbot.py`. You don't need to change any other code.

## Setup

1. Get an API key at [console.anthropic.com](https://console.anthropic.com) and add credit.
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Create your `.env` file and paste in your key:
   ```bash
   cp .env.example .env
   ```

## Run

Chat with it, typing `exit` to quit:
```bash
python pharmacy_chatbot.py
```

Run the scripted three-turn memory test. Turns 2 and 3 only make sense if turn 1 is remembered:
```bash
python pharmacy_chatbot.py --test
```

## Example: three-turn memory test

```
Kisumu Pharmacy Assistant
-------------------------
Running the 3-turn memory test. Turns 2 and 3 only make sense if turn 1 is remembered.

--- Turn 1 ---
You: Hi, I have a prescription from my doctor for my mother's blood pressure medicine.

Assistant: Hello, and thank you for reaching out to Kisumu Pharmacy! We'd be happy to help with your mother's prescription. Could you tell us whether this is a new prescription or a repeat, and please bring her national ID if you're collecting on her behalf. You can also call or WhatsApp us on 0722 456 789, and we'll have it ready for you.

--- Turn 2 ---
You: How long will it take?

Assistant: For a new prescription, it's usually ready in about 15-30 minutes while you wait. If an item needs to be ordered from our supplier, it will be ready the next working day by 12:00 noon. If it's a repeat prescription, you can call or WhatsApp us a day ahead so it's ready when you arrive.

--- Turn 3 ---
You: Next month I'll need the same again. What should I bring?

Assistant: For a repeat collection next month, please bring:

- The original prescription or your doctor's repeat authorisation, which is valid for 6 months
- Your mother's national ID, or a copy of it if you're collecting on her behalf
- Her insurance or NHIF/SHA card if you're paying by insurance

It's also helpful to call or WhatsApp us on 0722 456 789 a day ahead so it's ready when you arrive.

Conversation saved to chat_logs/chat_20261106_092421.json
```

## Privacy

Conversation logs can contain customers' health information, so `chat_logs/` is excluded from git and should stay on the pharmacy's computer. All names, prices and stock in this project are sample data.
