#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re
import time
import sqlite3
import json
import logging
from outbox import Outbox, Email
import requests
from bs4 import BeautifulSoup

logger = logging.basicConfig(format='%(asctime)s :: %(levelname)s :: %(message)s', level=logging.DEBUG)


def scan(url, max_nb_connection=10):
    nb_connection = 0
    connected = False

    while not connected and nb_connection <= max_nb_connection:
        try:
            nb_connection += 1
            r = requests.get(url)
        except ConnectionError as e:
            logging.error(e)
        else:
            connected = True

    if nb_connection > max_nb_connection:
        connection_error_message = "{} failed connections, aborting.".format(max_nb_connection)
        logging.error(connection_error_message)
        raise ConnectionError(connection_error_message) from e

    soup = BeautifulSoup(r.text, "lxml")

    is_ad = lambda tag: tag.name == "a" and "alertsLink" not in tag.get("class", [])
    ad_list = soup.find("div", class_="list-lbc").find_all(is_ad)

    ads = []

    for ad in ad_list:
        title = ad["title"].strip("\n\t ")
        link = ad["href"]
        date_tag = ad.find("div", class_="date").find_all("div")
        date = []

        for d in date_tag:
            date.append(d.string.strip("\n\t "))

        date = ", ".join(date)

        price = ad.find("div", class_="price")
        if price is not None:
            price = price.string.strip("\n\t ")

        category = ad.find("div", class_="category")
        if category is not None:
            category = category.string.strip("\n\t ")
            category = category.replace("\n", "")
            category = category.replace("\t", "")
            category = category.replace("\r", "")

        placement = ad.find("div", class_="placement")
        if placement is not None:
            placement = placement.string.strip("\n\t ")
            placement = placement.replace("\n", "")
            placement = placement.replace("\t", "")
            placement = placement.replace("\r", "")


        ads.append({"title": title,
                    "category": category,
                    "price": price,
                    "placement": placement,
                    "date": date,
                    "link": link
                    })

    return ads

def send_email(ad, config_file):

    with open(config_file, 'r') as f:
        config = json.load(f)

    port = config["port"]
    server = config["server"]
    fromaddr = config["fromaddr"]
    toaddrs = config["toaddrs"]
    username = config["username"]
    password = config["password"]

    subject = "Nouvelle annonce sur Leboncoin : {}".format(ad["title"])

    body = """Bonjour,\nUne nouvelle annonce sur Leboncoin satisfaisant vos critères de recherche vient d'être publiée.\n\n
    Titre : {title}\nDate de publication : {date}\nPrix : {price}\nCatégorie : {category}\nLocalisation : {placement}\nLien : {link}""".format(**ad)

    outbox = Outbox(username=username, password=password, server=server, port=port)
    email = Email(subject=subject, body=body, recipients=toaddrs)
    outbox.send(email)


def add_ad(ad, db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    links = c.execute("""INSERT INTO ADS VALUES (:title, :link, :category, :price, :placement, :date)""", ad)
    conn.commit()
    conn.close()

def get_links_db(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    links = list(c.execute("""SELECT LINK FROM ADS"""))
    links = [tup[0] for tup in links]
    conn.close()
    return links

def create_db(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("""CREATE TABLE ADS
               (TITLE TEXT, LINK TEXT, CATEGORY TEXT, PRICE TEXT, PLACEMENT TEXT, DATE_PUBLICATION TEXT)""")
    conn.commit()
    conn.close()

def watch(url, db_name, config_file, init=False):
    logging.info("Scanning web page...")
    ad_list = scan(url)
    logging.info("Getting URL from database...")
    links = get_links_db(db_name)

    for ad in ad_list:
        if ad["link"] not in links:
            if not init:
                send_email(ad, config_file)

            logging.debug("Adding ad '{}' to database".format(ad["title"]))
            add_ad(ad, db_name)


def start(url, db_name, config_file="config.json", time_interval=5):
    create_db(db_name)
    watch(url, db_name, config_file, init=True)

    while True:
        logging.info("Sleeping for {} min".format(time_interval))
        time.sleep(time_interval * 60)
        watch(url, db_name, config_file)
