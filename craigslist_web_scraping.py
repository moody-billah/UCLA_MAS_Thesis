#Importing libraries

import itertools
import requests
from sqlalchemy import create_engine
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup

# Database connection

conn = create_engine('mysql://root:root@localhost/craigslist_web_scraping')

#Getting the webpages from the database

q1 = 'select page_ID from webpages'
q2 = 'select page_url from webpages'
page_id = pd.read_sql(q1, conn)['page_ID']
page_url = pd.read_sql(q2, conn)['page_url']

#Defining web scraping function

def web_scraping(index, page_url, page_id):
    
    #Initiating the web scraper for the url
    
    url = page_url[0]
    page = requests.get(url)
    parser = BeautifulSoup(page.content, "html.parser")
    
    #Getting all the listings data into a dataframe
    
    listings = pd.DataFrame(parser.find_all(class_="result-meta"), dtype=object)
    
    #Defining fuction to parse separate sections of the listings data
    
    def parse_listings(listings, col_name, class_name):  
        var = list(itertools.repeat(0, len(listings)))   
        for i in range(len(listings)):
            var[i] = listings.iloc[i,0].find(class_=class_name)
            i += 1   
        var = pd.DataFrame(var, columns=[col_name])
        return var
    
    #Getting and cleaning all the rental price data into a dataframe
    
    price = parse_listings(listings, "rent", "result-price")
    price["rent"] = price["rent"].str.replace("$", "")
    price["rent"] = price["rent"].str.replace(",", "")
    price = price.astype(int)
    
    #Getting and cleaning all the property size data into a dataframe
    
    size = parse_listings(listings, "size", "housing")
    size = size.astype("str")
    size["size"] = size["size"].str.replace('<span class="housing">\n                    ', '')
    size["size"] = size["size"].str.replace('<sup>2</sup> -\n                </span>', '')
    size["size"] = size["size"].str.replace(' -\n                </span>', '')
    size["size"] = size["size"].str.split(' -\n                    ')
    
    #Separating and cleaning bedrooms and square feet data
    
    beds = pd.DataFrame(index=range(len(size)), columns=["bedrooms"], dtype="str")
    sq_ft = pd.DataFrame(index=range(len(size)), columns=["sq_feet"], dtype="str")

    for i in range(len(size)):
        if len(size["size"][i]) == 2:
            beds["bedrooms"][i] = size["size"][i][0]
            sq_ft["sq_feet"][i] = size["size"][i][1]
        elif "br" in size["size"][i][0]:
            beds["bedrooms"][i] = size["size"][i][0]
            sq_ft["sq_feet"][i] = -1
        elif "ft" in size["size"][i][0]:
            beds["bedrooms"][i] = -1
            sq_ft["sq_feet"][i] = size["size"][i][0]
        else:
            beds["bedrooms"][i] = -1
            sq_ft["sq_feet"][i] = -1        
        i += 1
    
    beds["bedrooms"] = beds["bedrooms"].str.replace("br", "")
    sq_ft["sq_feet"] = sq_ft["sq_feet"].str.replace("ft", "")
    beds = beds.fillna(-1).astype(int)
    sq_ft = sq_ft.fillna(-1).astype(int)
    
     #Getting and cleaning all the neighborhood data into a dataframe
    
    hood = parse_listings(listings, "location", "result-hood")
    hood = hood.astype("str")
    hood["location"] = hood["location"].str.replace('<span class="result-hood"> ', '')
    hood["location"] = hood["location"].str.replace('</span>', '')
    hood["location"] = hood["location"].str.replace('nan', '')
    hood["location"] = hood["location"].str.replace('(', '')
    hood["location"] = hood["location"].str.replace(')', '')
    
    #Generating the IDs for the final dataset
    
    pid = pd.DataFrame(itertools.repeat(page_id[index], len(listings)), columns=["page_id"])
    
    #Creating the final dataset and and adding it to the database
    
    dataset = pd.concat([pid, price, beds, sq_ft, hood], axis=1)
    dataset.to_sql(name='listings', con=conn, schema='craigslist_web_scraping', index=False, if_exists='append')

#Running web scraping function

for i in range(len(page_url)):
    web_scraping(i, page_url, page_id)
    i += 1