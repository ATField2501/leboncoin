#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re
import time
import sqlite3
import requests
from bs4 import BeautifulSoup

def scan(url, max_nb_connection=10):
    nb_connection = 0
    connected = False

    while not connected and nb_connection <= max_nb_connection:
        try:
            nb_connection += 1
            r = requests.get(url)
        except ConnectionError as e:
            print(e)
        else:
            connected = True

    if nb_connection > max_nb_connection:
        raise ConnectionError("{} failed connections, aborting.".format(max_nb_connection))

    soup = BeautifulSoup(r.text, "lxml")
    ad_list = soup.find("div", class_="list-lbc").find_all("a")

    ads = []

    for ad in ad_list:
        title = ad["title"].strip("\n\t ")
        link = ad["href"]
        date_tag = ad.find("div", class_="date").find_all("div")
        date = []

        for d in date_tag:
            date.append(d.string.strip("\n\t "))

        price = ad.find("div", class_="price")
        if price is not None:
            price = price.string.strip("\n\t ")

        category = ad.find("div", class_="category")
        if category is not None:
            category = category.string.strip("\n\t ")

        placement = ad.find("div", class_="placement")
        if placement is not None:
            placement = placement.string.strip("\n\t ")


        ads.append({"title": title,
                    "category": category,
                    "price": price,
                    "placement": placement,
                    "date": date
                    })

    for ad in ads:
        print(ad)

def send_email(ad):
    pass

def get_links_db():
    pass

def create_db(db_name="ads.db"):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute()

def watch(url, time_interval=5):
    ad_list = scan(url)
    links = get_links_db()

    for ad in ad_list:
        if ad["href"] not in links:
            send_email(ad)
            add_ad(ad)

    time.sleep(time_interval * 60)
