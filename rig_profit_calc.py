import requests
import json
import sqlite3
import os
import time
import re

from datetime import datetime
from bs4 import BeautifulSoup

  
    
def getProfitDaily(coin = 'ethereum', hashrate=328, power=650, electricityPrice=0.1):
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting API for "+coin+" ...")
    hashrate = hashrate*10**6 # Mh/s   
    response = requests.get('https://www.coincalculators.io/api?name='+str(coin)+'&hashrate='+str(hashrate)+'&power='+str(power)+'&powercost='+str(electricityPrice), timeout=1)
    profitDaily = json.loads(response.text)['profitInDayUSD']
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] API for "+coin+" done! Value: "+str(profitDaily))
    return profitDaily



def getSoup(link, name = "default_name"):
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting getSoup for "+name+" ...")
    soup = """<em class="main-price color">300&nbsp;600,00&nbsp;zł</em>
        <p><span style="font-family:'trebuchet ms', geneva, sans-serif;font-size:12pt;">Moc obliczeniowa:&nbsp;<strong>12-15&nbsp;Mh/s</strong></span></p>
        <p><span style="font-family:'trebuchet ms', geneva, sans-serif;font-size:12pt;">Pobór energii:<strong>&nbsp;11700-11750W</strong></span></p>"""
    try:
        r = requests.get(link, timeout = 3)
        soup = BeautifulSoup(r.text, "html.parser")
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] getSoup for "+name+" done!")
        
        return soup
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't get soup for "+name+", using default")
        return soup

    
def getPriceFromSoup(soup, name = "default_name"):
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting getPrice for "+name+" ...")
    price_int = 1000000
    try:
        price = soup.find('em', {'class': 'main-price'})
        price_int = int(''.join(price.text.split())[:-5].upper())     
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] getPrice for "+name+" done!")
        
        return price_int
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't get price for "+name+", using default")
        return price_int



def getHashrateFromSoup(soup, name = "default_name"):
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting getHashrate for "+name+" ...")
    hashrate = 1
    try:
        p_tag = soup.find_all("p")
        for i in p_tag:
            
            text = i.get_text()
            
            if "Moc obliczeniowa:" in text:

                text = text.split("Moc obliczeniowa:")[1].strip()
                if "Ph/s" in text:
                    multiplier = 10**15
                    split_mul = "Ph/s"
                elif "Th/s" in text:
                    multiplier = 10**12
                    split_mul = "Th/s"
                elif "Gh/s" in text:
                    multiplier = 10**9
                    split_mul = "Gh/s"
                elif "Mh/s" in text:
                    multiplier = 10**6
                    split_mul = "Mh/s"
                elif "kh/s" in text:
                    multiplier = 10**3
                    split_mul = "kh/s"
                elif "h/s" in text:
                    multiplier = 10**0
                    split_mul = "h/s"
                    
                text = text.split(split_mul)[0].strip()
                if "-" in text:
                    text = text.split("-")
                    hashrate = int((int(text[0]) + int(text[1])) / 2)
                
                else:
                    hashrate = int(text)
                    
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] getHashrate for "+name+" done!")
        return hashrate
        
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't get hashrate for "+name+", using default")
        return hashrate
        
        
def getWattageFromSoup(soup, name = "default_name"):
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting getWattage for "+name+" ...")
    wattage = 1000
    try:
        p_tag = soup.find_all("p")
        for i in p_tag:
            
            text = i.get_text()
            
            if "Pobór energii:" in text:

                text = text.split("Pobór energii:")[1].strip()
                    
                text = text.split("W")[0].strip()
                if "-" in text:
                    text = text.split("-")
                    wattage = int((int(text[0]) + int(text[1])) / 2)
                
                else:
                    wattage = int(text)
                    
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] getWattage for "+name+" done!")
        return wattage
        
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't get wattage for "+name+", using default")
        return wattage



def createDirIfNotExist(path):

    if not os.path.exists(path):
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Creating cache directory")
        os.makedirs(path)
 


def useShopCache(link, rigModel, tableName):
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting useShopCache for "+str(rigModel)+" ...")
    timestamp = 0
    
    db_path = "db/cacheFromShop.db"
    path = 'db'
    createDirIfNotExist(path)
    
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS """+tableName+""" (
            timestamp TEXT,
            price TEXT,
            hashrate TEXT,
            wattage TEXT
            )""")
        c.execute("""SELECT timestamp, price, hashrate, wattage FROM """+tableName+""" ORDER BY timestamp DESC LIMIT 1""")
        for row in c.fetchall():
            timestamp = int(row[0])
            final_price = int(row[1])
            final_hashrate = int(row[2])
            final_wattage = int(row[3])
    
    timeNow = int(time.time())
    if timestamp + 10 < timeNow:
        soup = getSoup(link, rigModel)
        final_price = getPriceFromSoup(soup, rigModel)
        final_hashrate = getHashrateFromSoup(soup, rigModel)
        final_wattage = getWattageFromSoup(soup, rigModel)
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS """+tableName+""" (
            timestamp TEXT,
            price TEXT,
            hashrate TEXT,
            wattage TEXT
            )""")
            
        c.execute("""INSERT INTO """+tableName+""" VALUES(
            ?, ?, ?, ?)""", (timeNow, final_price, final_hashrate, final_wattage))
            
        c.execute("""Delete from """+tableName+""" where timestamp <> (Select max (timestamp) from """+tableName+""")""")
        
        conn.commit()
        c.close()
        conn.close()
        
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Updating cache, using new values for "+str(rigModel))
    else:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Using cached values for "+str(rigModel))
    return int(final_price), int(final_hashrate), int(final_wattage)

 
        
    
# TODO:
# http://api.nbp.pl/api/exchangerates/rates/c/usd/today/

if __name__ == "__main__":
    
    # defaults
    electricityPricePLN_gr = 80
    PLNperUSD = 4.5
    profitPerMHsDaily_ETH = 0.02721
    profitPerMHsDaily_ETC = 0.02185
    profitPerMHsDaily_RVN = 0.05123


    try:
        profitPerMHsDaily_ETH = getProfitDaily('ethereum', 1, 0, 0)
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't fetch profits for ETH, using: " + str(profitPerMHsDaily_ETH))

    try:
        profitPerMHsDaily_ETC = getProfitDaily('ethereumclassic', 1, 0, 0)
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't fetch profits for ETC, using: " + str(profitPerMHsDaily_ETC))
    
    try:
        profitPerMHsDaily_RVN = getProfitDaily('ravencoin', 1, 0, 0)
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't fetch profits for RVN, using: " + str(profitPerMHsDaily_RVN))
        
        
    cDict = {}
    cDict['electricityPricePLN_gr'] = float(electricityPricePLN_gr)
    cDict['electricityPricePLN'] = cDict.get('electricityPricePLN_gr') / 100
    cDict['electricityPrice'] = cDict.get('electricityPricePLN')/PLNperUSD

    cDict['rigName_6xRX570_4gb_used'] = "6x RX570 4GB Used"
    link_6xRX570_4gb_used = "https://shop.zet-tech.eu/pl/p/6x-RX-470-4GB-Koparka-kryptowalut/116"
    cDict['rigPricePLN_6xRX570_4gb_used'], cDict['hashrate_6xRX570_4gb_used'], cDict['power_6xRX570_4gb_used']  = useShopCache(link_6xRX570_4gb_used, cDict['rigName_6xRX570_4gb_used'], "_6xRX570_4gb_used")
    cDict['profitDailyPLN_6xRX570_4gb_used'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_6xRX570_4gb_used')) - (cDict.get('power_6xRX570_4gb_used') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xRX570_4gb_used'] = int(cDict.get('rigPricePLN_6xRX570_4gb_used')/(cDict.get('profitDailyPLN_6xRX570_4gb_used')))
    if cDict['roi_6xRX570_4gb_used'] < 0:
        cDict['roi_6xRX570_4gb_used'] = "Never :("
    
    
    cDict['rigName_8xRX6600'] = "8x RX6600XT"
    link_8xRX6600 = "https://shop.zet-tech.eu/pl/p/8x-RX-6600XT-Koparka-kryptowalut-NOWOSC/118"
    cDict['rigPricePLN_8xRX6600'], cDict['hashrate_8xRX6600'], cDict['power_8xRX6600'] = useShopCache(link_8xRX6600, cDict['rigName_8xRX6600'], "_8xRX6600")
    cDict['profitDailyPLN_8xRX6600'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_8xRX6600')) - (cDict.get('power_8xRX6600') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_8xRX6600'] = int(cDict.get('rigPricePLN_8xRX6600')/(cDict.get('profitDailyPLN_8xRX6600')))
    if cDict['roi_8xRX6600'] < 0:
        cDict['roi_8xRX6600'] = "Never :("  
        
    
    
    
    print(cDict)

    

        
        
        
    


    