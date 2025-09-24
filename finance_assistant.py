import sqlite3
import datetime
import speech_recognition as sr
import pyttsx3
import json
import os
from dotenv import load_dotenv
import groq

print("imported all modules")
class FinanceAssistant:
    def __init__(self):
        self.initialize_db()
        self.engine = pyttsx3.init()
        self.recognizer = sr.Recognizer()
        load_dotenv()
        self.groq_client = groq.Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )

    def initialize_db(self):
        conn = sqlite3.connect('finances.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL,
                description TEXT,
                account TEXT,
                date TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def speak(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

    def listen(self):
        with sr.Microphone() as source:
            print("Listening...")
            self.speak("I'm listening")
            try:
                audio = self.recognizer.listen(source)
                text = self.recognizer.recognize_google(audio)
                return text.lower()
            except:
                return None

    def add_transaction(self, amount, description, account, date=None):
        if date is None:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        conn = sqlite3.connect('finances.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (amount, description, account, date)
            VALUES (?, ?, ?, ?)
        ''', (amount, description, account, date))
        conn.commit()
        conn.close()

    def get_transactions(self, days=None):
        conn = sqlite3.connect('finances.db')
        cursor = conn.cursor()
        
        if days:
            date_limit = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
            cursor.execute('''
                SELECT * FROM transactions 
                WHERE date >= ?
                ORDER BY date DESC
            ''', (date_limit,))
        else:
            cursor.execute('SELECT * FROM transactions ORDER BY date DESC')
        
        transactions = cursor.fetchall()
        conn.close()
        return transactions

    def get_ai_analysis(self, transactions):
        """Get AI analysis of spending patterns"""
        if not transactions:
            return "No transactions to analyze."
        
        # Prepare transaction data for AI analysis
        transaction_text = "\n".join([
            f"Amount: {t[1]}, Description: {t[2]}, Account: {t[3]}, Date: {t[4]}"
            for t in transactions
        ])

        prompt = f"""Analyze these financial transactions and provide insights:
        {transaction_text}
        
        Please provide:
        1. Total spending
        2. Main spending categories
        3. Spending patterns
        4. Recommendations for savings
        """

        try:
            completion = self.groq_client.chat.completions.create(
                model="llama3-70b",
                messages=[
                    {"role": "system", "content": "You are a financial advisor analyzing transaction data."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error getting AI analysis: {str(e)}"

    def process_voice_input(self):
        text = self.listen()
        if text: 
            self.process_input(text)
        else:
            self.speak("Sorry, I couldn't understand that. Please try again.")

    def process_text_input(self, text):
        self.process_input(text.lower())

    def process_input(self, text):
        if "spent" in text or "spend" in text:
            try:
                amount = float(''.join(filter(str.isdigit, text)))
                words = text.split()
                account_index = words.index("account") if "account" in words else -1
                account = words[account_index + 1] if account_index != -1 else "default"
                
                self.add_transaction(amount, text, account)
                response = f"Recorded expense of {amount} from {account} account"
                print(response)
                self.speak(response)
            except:
                self.speak("Sorry, I couldn't process that transaction")
        
        elif "where" in text and "spend" in text:
            days = 30  # default to last 30 days
            if "days" in text:
                try:
                    days = int(''.join(filter(str.isdigit, text)))
                except:
                    pass
            
            transactions = self.get_transactions(days)
            if transactions:
                response = f"Here are your expenses for the last {days} days:\n"
                for t in transactions:
                    response += f"Amount: {t[1]}, Description: {t[2]}, Account: {t[3]}, Date: {t[4]}\n"
                
                # Add AI analysis
                ai_analysis = self.get_ai_analysis(transactions)
                response += "\nAI Analysis:\n" + ai_analysis
            else:
                response = "No transactions found for this period"
            
            print(response)
            self.speak(response)
        
        elif "analyze" in text or "analysis" in text:
            days = 30
            if "days" in text:
                try:
                    days = int(''.join(filter(str.isdigit, text)))
                except:
                    pass
            
            transactions = self.get_transactions(days)
            analysis = self.get_ai_analysis(transactions)
            print(analysis)
            self.speak(analysis)

def main():
    assistant = FinanceAssistant()
    
    while True:
        print("\n1. Voice Mode")
        print("2. Text Mode")
        print("3. Exit")
        choice = input("Select mode (1-3): ")
        
        if choice == "1":
            assistant.process_voice_input()
        elif choice == "2":
            text = input("Enter your query: ")
            assistant.process_text_input(text)
        elif choice == "3":
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    print("main function called")
    main()
