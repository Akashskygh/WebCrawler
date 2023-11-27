import requests
from bs4 import BeautifulSoup
import smtplib
from email.message import EmailMessage
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

# Fetches all documents from the Open Canada website
# Returns a list of URLs pointing to all documents
def get_latest_documents():
    base_url = "https://open.canada.ca/en/search/ati"
    all_links = []

    # Set the number of pages you want to scrape
    num_pages = 2  # Change this to the desired number of pages

    for page in range(1, num_pages + 1):
        url = f"{base_url}?page={page}"
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching the URL: {e}")
            continue

        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.select('div.col-sm-8 h4.mrgn-tp-0 a')
        all_links.extend([link.get('href') for link in links])

    return all_links

# Reads the previous links from a file and returns a set
def read_previous_links(file_path):
    try:
        with open(file_path, "r") as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()

def write_new_links(file_path, new_links):
    full_links = [link for link in new_links]
    with open(file_path, "a") as f:
        f.write('\n'.join(full_links) + '\n')

# Sends an email with the provided list of new links
def send_email(new_links):
    email = "your@gmail.com"
    password = "appPassword"
    recipient_email = "receiver@gmail.com"

    # Add the prefix to each link
    full_links = [f"{link}\n" for link in new_links]

    msg_content = "Here are the new documents uploaded on Open Canada:\n\n" + "\n".join(full_links)

    msg = EmailMessage()
    msg.set_content(msg_content)
    msg["Subject"] = "New Documents Uploaded on Open Canada"
    msg["From"] = email
    msg["To"] = recipient_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email, password)
            server.send_message(msg)
    except Exception as e:
        print(f"Error sending email: {e}")

class DatabaseOperations:
    def __init__(self, database_name, collection_name):
        self.client = MongoClient('localhost', 27017)
        self.db = self.client[database_name]
        self.collection = self.db[collection_name]

    def link_exists(self, link):
        """Check if a link already exists in the database."""
        count = self.collection.count_documents({"link": link})
        return count > 0

    def insert_link(self, link, date_scraped):
        link_document = {
            "link": link,
            "dateScraped": date_scraped
        }
        self.collection.insert_one(link_document)

    def insert_links_to_database(self, links):
        current_time_utc = datetime.utcnow()
        for link in links:
            self.insert_link(link, current_time_utc)

    def create_dataframe(self, links):
        current_time_utc = datetime.utcnow()
        data = {
            "link": links,
            "dateScraped": [current_time_utc] * len(links)
        }
        df = pd.DataFrame(data)
        return df

# Main function
def main():
    database_name = 'LinksDB'
    collection_name = 'links'
    db_operations = DatabaseOperations(database_name=database_name, collection_name=collection_name)

    try:
        current_links = set(get_latest_documents())
        previous_links = read_previous_links("previous_links.txt")

        if not current_links:
            print("Failed to fetch latest documents.")
            return

        current_links = {f'https://open.canada.ca{link}' for link in current_links}
        new_links = current_links - previous_links

        if new_links:
            send_email(list(new_links))
            full_links = [f"https://open.canada.ca{link}" for link in new_links]

            db_operations.insert_links_to_database(new_links)

            write_new_links("previous_links.txt", list(new_links))

            new_links_df = db_operations.create_dataframe(list(new_links))
            print("DataFrame for new link main.py:")
            print(new_links_df)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        db_operations.client.close()

if __name__ == "__main__":
    main()
