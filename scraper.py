import requests
from bs4 import BeautifulSoup

from pymongo import MongoClient
from email.message import EmailMessage
from dotenv import load_dotenv
import os
import json
import time
import smtplib

load_dotenv()

EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING')

def send_notification(item, message):
    msg = EmailMessage()
    msg['Subject'] = "!!! NEW " + item + " LISTING !!!"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_ADDRESS
    msg.set_content(message)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

def get_database():
   client = MongoClient(MONGO_CONNECTION_STRING)
   return client['Listings']

db = get_database()
items =['manga', 'nintendo']

while(True):
    for listing in items:
        url_p1 = "https://www.goodwillfinds.com/on/demandware.store/Sites-goodwill-Site/en_US/Search-UpdateGrid?q="
        url_p2 = "&srule=new-arrivals&start=0&sz=48&selectedUrl=https%3A%2F%2Fwww.goodwillfinds.com%2Fon%2Fdemandware.store%2FSites-goodwill-Site%2Fen_US%2FSearch-UpdateGrid%3Fq%3D"
        url_p3 = "%26srule%3Dnew-arrivals%26start%3D48%26sz%3D48&ajax=true"
        response = requests.get(url_p1+listing+url_p2+listing+url_p3)

        if response.status_code == 200:
            scraper = BeautifulSoup(response.content, 'html.parser')
            
        listings = scraper.find_all(class_='b-product_tile js-analytics-item')
        listingdata = []
        for element in listings:
            data = element.get('data-analytics')
            listingdata.append(json.loads(data))

        current_item = db[listing]

        # If we want to report a new batch has been listed, we need a lock for it
        batchlock = 0

        for i in listingdata:
            price = i.get('price')

            # Batch Listings
            if listing == "nintendo":
                if bool(current_item.find_one({"_id": i.get('id')})) == True:
                    batchlock = 0
                    break
                else:
                    item = {
                        "_id": i.get('id'),
                        "name": i.get('name'),
                        "price": price,
                    }
                    batchlock += 1
                    if batchlock == 1:
                        print("!!!New Batch Added!!!     Item: " + listing)
                        send_notification(listing.upper(),"New batch of listings has been posted." + "\nhttps://www.goodwillfinds.com/search/?q=nintendo")
                    current_item.insert_one(item)
            
            
            # Normal Listings
            else:
                if bool(current_item.find_one({"_id": i.get('id')})) == True:
                    break
                else:
                    item = {
                        "_id": i.get('id'),
                        "name": i.get('name'),
                        "price": price,
                    }
                    print("!!!New Listing Added!!!     Item: " + listing)
                    send_notification(listing.upper(), "Price: " + str(price) + "\nName: " + i.get('name') + "\nPrice: " + price + "\n\nhttps://www.goodwillfinds.com/search/?q=manga")
                    current_item.insert_one(item)
    print("Nothing yet...")
    time.sleep(60)
