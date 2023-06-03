import csv
import os
import time
import ujson
from random import randint
from typing import Dict, List, Any
import json

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By


# Delete files if present
try:
    os.remove('crawlurl.txt')
    os.remove('scrapers_dump.json')
except OSError:
    pass

def write_authors(list1, file_name):
    with open(file_name, 'w', encoding='utf-8') as f:
        for i in range(0, len(list1)):
            f.write(list1[i] + '\n')


def initCrawlerScraper(seed, page_limit):
    # Initialize driver for Chrome
    webOpt = webdriver.ChromeOptions()
    webOpt.add_experimental_option('excludeSwitches', ['enable-logging'])
    webOpt.add_argument('--ignore-certificate-errors')
    webOpt.add_argument('--incognito')
    webOpt.add_argument('--headless')  # Set headless mode
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=webOpt, service_log_path=os.devnull)

    driver.get(seed)  # Start with the original link

    Links = []  # Array with pureportal profiles URL
    pub_data = []  # To store publication information for each pureportal profile
    next_link = driver.find_element(By.CSS_SELECTOR, ".nextLink")
    next_link_enabled = next_link.is_enabled()

    page_count = 0  # Counter for the number of pages crawled

    while next_link_enabled and page_count < page_limit:
        page_count += 1

        page = driver.page_source
        bs = BeautifulSoup(page, "lxml")

        # Extracting exact URL by accessing the href attribute
        for link in bs.findAll('a', class_='link person'):
            url = link['href']
            Links.append(url)

        # Click on Next button to visit the next page
        try:
            if driver.find_element(By.CSS_SELECTOR, ".nextLink"):
                element = driver.find_element(By.CSS_SELECTOR, ".nextLink")
                driver.execute_script("arguments[0].click();", element)
            else:
                next_link_enabled = False
        except NoSuchElementException:
            break

    print("Crawler has found", len(Links), "pureportal profiles")
    write_authors(Links, 'crawlurl.txt')

    print("Scraping publication data for", len(Links), "pureportal profiles...")

    # Load the URLs from the file
    with open('crawlurl.txt', 'r') as f:
        urls = f.read().splitlines()

    # Crawl data from 10 URLs
    for i in range(8):
        if i >= len(urls):
            break

        url = urls[i]

        # Visit each link to get data
        time.sleep(1)
        driver.get(url)
        try:
            if driver.find_elements(By.CSS_SELECTOR, ".portal_link.btn-primary.btn-large span"):
                elements = driver.find_elements(By.CSS_SELECTOR, ".portal_link.btn-primary.btn-large span")
                for span in elements:
                    try:
                        if span.text:
                            if "research output".lower() in span.text.lower():
                                driver.execute_script("arguments[0].click();", span)
                                driver.get(driver.current_url)
                                # Get name of Author
                                name = driver.find_element(By.CSS_SELECTOR, "div[class='header person-details']>h1")
                                r = requests.get(driver.current_url)
                                page = r.content
                                bs = BeautifulSoup(page, "lxml")
                                rows = bs.findAll("div", {"class": "result-container"})
                                for row in rows:
                                    data: Dict[str, Any] = {}
                                    data['name'] = row.h3.a.text.strip()
                                    data['pub_url'] = row.h3.a['href']
                                    date = row.find("span", class_="date")
                                    data['cu_author'] = name.text if name else ''
                                    data['date'] = date.text if date else ''
                                    pub_data.append(data)
                                    print("Publication Name:", data['name'])
                                    print("Publication URL:", data['pub_url'])
                                    print("CU Author:", data['cu_author'])
                                    print("Date:", data['date'])
                                    print("\n")
                    except StaleElementReferenceException:
                        continue

        except NoSuchElementException:
            break

    # Writing publication data to a JSON file
    with open('scrapers_dump.json', 'w', encoding='utf-8') as json_file:
        json.dump(pub_data, json_file, ensure_ascii=False, indent=4)


seed_link = 'https://pureportal.coventry.ac.uk/en/publications/'
page_limit = 1

initCrawlerScraper(seed_link, page_limit)
