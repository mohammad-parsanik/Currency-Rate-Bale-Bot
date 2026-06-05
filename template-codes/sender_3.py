import pandas as pd
import requests
import time
import logging
import os

# --- Configuration ---
EXCEL_FILE_PATH = "your_data.xlsx"  # <-- FILL THIS
API_ACCESS_KEY_SEND = "XTmHKjABsvhHK5Nk" # <-- FILL THIS
USER_ACCESS_TOKEN_UPLOAD = "XTmHKjABsvhHK5Nk" # <-- FILL THIS
BOT_ID = 852830801 # <-- FILL THIS
MESSAGE_TEXT = """با سلام و احترام

کلاس رشته‌های هوش مصنوعی و اقتصاد در دوره زمستان و بهار ژرفا به حد نصاب نرسیده و تشکیل نخواهد شد."""

RETRY_DELAY = 5
MAX_RETRIES = 1

# --- Setup Logging ---
logging.basicConfig(
    filename='messaging_log.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- API Endpoints ---
UPLOAD_URL = 'https://safir.bale.ai/api/v3/upload_file'
SEND_URL = 'https://safir.bale.ai/api/v3/send_message'

def upload_file(file_path: str) -> str | None:
    """Uploads a file and returns the file_id."""
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return None
        
    headers = {
        'api-access-key': USER_ACCESS_TOKEN_UPLOAD
    }
    files = {
        'file': (os.path.basename(file_path), open(file_path, 'rb'))
    }
    
    for attempt in range(MAX_RETRIES + 1):
        try:
            logging.info(f"Attempt {attempt + 1}: Uploading file: {file_path}")
            response = requests.post(UPLOAD_URL, headers=headers, files=files)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            
            result = response.json()
            if result != {}:
                file_id = result.get("file_id")
                logging.info(f"Successfully uploaded {file_path}. File ID: {file_id}")
                return file_id
            else:
                logging.warning(f"Upload failed for {file_path}. Server message: {result.get('message', 'Unknown error')}")
                
        except requests.exceptions.RequestException as e:
            logging.error(f"HTTP error during upload for {file_path}: {e}")
        
        if attempt < MAX_RETRIES:
            logging.info(f"Retrying upload for {file_path} in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
            
    logging.error(f"Failed to upload file {file_path} after {MAX_RETRIES + 1} attempts.")
    return None

def send_message(phone_number: str, link: str) -> bool:
    """Sends a message to a specific phone number with the file_id."""
    headers = {
        'api-access-key': API_ACCESS_KEY_SEND,
        'Content-Type': 'application/json'
    }
    payload = {
        "bot_id": BOT_ID,
        "phone_number": str(phone_number), # Ensure phone number is string
        "message_data": {
            "message": {
                "text": MESSAGE_TEXT,
                #"file_id": file_id
            }
        }
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            logging.info(f"Attempt {attempt + 1}: Sending message to {phone_number} with Link {link}")
            response = requests.post(SEND_URL, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()
            if result.get("message_id") != None:
                logging.info(f"Successfully sent message to {phone_number}.")
                return True
            else:
                logging.warning(f"Message send failed for {phone_number}. Server message: {result.get('message', 'Unknown error')}")

        except requests.exceptions.RequestException as e:
            logging.error(f"HTTP error during message send to {phone_number}: {e}")

        if attempt < MAX_RETRIES:
            logging.info(f"Retrying message send to {phone_number} in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)

    logging.error(f"Failed to send message to {phone_number} after {MAX_RETRIES + 1} attempts.")
    return False

def process_excel(file_path: str):
    """Reads the Excel file and processes each row."""
    try:
        # Assuming the columns are: Phone1, Phone2, FilePath
        df = pd.read_excel(file_path)
        
        # Rename columns for clarity based on your description (adjust if your actual headers differ)
        df.columns = ['Phone1', 'Phone2'] 
        
        if not all(col in df.columns for col in ['Phone1', 'Phone2']):
            logging.error("Excel columns do not match expected structure: Phone1, Phone2.")
            print("Error: Check the column names in your Excel file match the script's expectation (or adjust the script).")
            return
        
        df ['Phone1'] = df['Phone1'].fillna(0).astype('Int64')
        df ['Phone2'] = df['Phone2'].fillna(0).astype('Int64')

    except FileNotFoundError:
        logging.critical(f"Excel file not found at: {file_path}")
        print(f"Critical Error: Excel file not found at: {file_path}")
        return
    except Exception as e:
        logging.critical(f"Error reading Excel file: {e}")
        print(f"Critical Error reading Excel file: {e}")
        return

    
    print(f"Starting processing for {len(df)} rows. See messaging_log.log for details.")

    for index, row in df.iterrows():
        if row['Phone1'] != float('nan'):
            phone1 = int(row['Phone1'])
        else:
            phone1 = row['Phone1']
        
        if row['Phone2'] != float('nan'):
            phone2 = int(row['Phone2'])
        else:
            phone2 = row['Phone2']
        #file_path_to_send = "Data/" + row['FilePath']
        #link = row['Link']
        
        print(f"\n--- Processing Row {index + 1} ---")
        logging.info(f"--- Starting processing for Row {index + 1} ---")
        
        """# 1. Upload the file
        file_id = upload_file(file_path_to_send)
        
        if not file_id:
            logging.error(f"Skipping messages for Row {index + 1} due to file upload failure.")
            print(f"Skipped sending for Row {index + 1}. File upload failed.")
            continue
        """

        # 2. Send to Phone 1
        send_message(phone1, link="")
        
        # 3. Send to Phone 2
        send_message(phone2, link="")
        
        # Optional: Small pause between processing *rows* to respect rate limits, though not explicitly required.
        # time.sleep(1) 

if __name__ == "__main__":
    # !!! REMINDER: Fill in the constants at the top of the script before running !!!
    process_excel(EXCEL_FILE_PATH)
    print("\nProcessing complete. Check 'messaging_log.log' for detailed results.")
