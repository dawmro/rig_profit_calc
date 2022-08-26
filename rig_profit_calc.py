from flask import Flask, render_template, request

import requests
import aiohttp
import asyncio
import time
import os
import sqlite3
import json
import ast


from datetime import datetime
from bs4 import BeautifulSoup


caching_time = 60

app = Flask(__name__)




def getUsdPln():
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting USDPLN  ...")  
    response = requests.get('http://api.nbp.pl/api/exchangerates/rates/c/usd/', timeout = 3)
    usdpln = str(json.loads(response.text)['rates']).replace("[", "").replace("]", "")
    usdpln = ast.literal_eval(usdpln)['ask']
    
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] USDPLN done! Value: "+str(usdpln))
    return usdpln

  
    
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

    
def getPriceFromSoup(soup, name = "default_name", vendor = "ZET"):
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting getPrice for "+name+" ...")
    price_int = 1000000
    
    try:
        if vendor == "ZET":
            price = soup.find('em', {'class': 'main-price'})
            price_int = int(''.join(price.text.split())[:-5].upper()) 
            
        elif vendor == "OBM":
            price = soup.find(class_ = 'price').select_one("bdi").text
            price_int = int(price.split(",")[0].replace(" ", ""))
            
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] getPrice for "+name+" done!")
        return price_int
        
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't get price for "+name+", using default")
        return price_int



def getHashrateFromSoup(soup, name = "default_name", vendor = "ZET"):
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting getHashrate for "+name+" ...")
    hashrate = 1
    try:
        if vendor == "ZET":
            p_tag = soup.find_all("p")
            for i in p_tag:
                
                text = i.get_text()
                
                if "Moc obliczeniowa:" in text:

                    text = text.split("Moc obliczeniowa:")[1].strip()
                    text = text.split("(")[0].strip()
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
                        
        elif vendor == "OBM": 
            div_tag = soup.find_all("div", class_ = "item item-6")
            for i in div_tag:
                text = i.get_text()

                if "Mining GPU ETH/ETC =" in text:
                    text = text.split("Mining GPU ETH/ETC =")[1].strip().split("MH")[0]
                    hashrate = int(text)
                    
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] getHashrate for "+name+" done!")
        return hashrate
        
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't get hashrate for "+name+", using default")
        return hashrate
        
        
def getWattageFromSoup(soup, name = "default_name", vendor = "ZET"):
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting getWattage for "+name+" ...")
    wattage = 1000000
    try:
        if vendor == "ZET":
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
        elif vendor == "OBM": 
            div_tag = soup.find_all("div", class_ = "item item-6")
            for i in div_tag:
                text = i.get_text()

                if "Realny pobór pradu:" in text:
                    text = text.split("Realny pobór pradu:")[1].strip().split("W")[0]
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
 


def useShopCache(link, rigModel, tableName, vendor = "ZET"):
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
    if timestamp + caching_time < timeNow:
        soup = getSoup(link, rigModel)
        final_price = getPriceFromSoup(soup, rigModel, vendor)
        final_hashrate = getHashrateFromSoup(soup, rigModel, vendor)
        final_wattage = getWattageFromSoup(soup, rigModel, vendor)
        
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
    
    
    

def useProfitCache(coin, hashrate, power, electricityPrice):
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting useProfitCache for "+str(coin)+" ...")
    timestamp = 0
    
    db_path = "db/cacheFromProfit.db"
    path = 'db'
    createDirIfNotExist(path)
    
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS """+coin+""" (
            timestamp TEXT,
            profitability TEXT
            )""")
        c.execute("""SELECT timestamp, profitability FROM """+coin+""" ORDER BY timestamp DESC LIMIT 1""")
        for row in c.fetchall():
            timestamp = int(row[0])
            profitDaily = float(row[1])
            
    timeNow = int(time.time())
    if timestamp + caching_time < timeNow:
        profitDaily = getProfitDaily(coin, hashrate, power, electricityPrice)
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS """+coin+""" (
            timestamp TEXT,
            profitability TEXT
            )""")     
            
        c.execute("""INSERT INTO """+coin+""" VALUES(
            ?,  ?)""", (timeNow, profitDaily))
            
        c.execute("""Delete from """+coin+""" where timestamp <> (Select max (timestamp) from """+coin+""")""")
        
        conn.commit()
        c.close()
        conn.close()        

        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Updating ProfitCache, using new values for "+str(coin))
        
    else:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Using cached values for "+str(coin))
        
    return profitDaily
 
    
    

def doCalculationsForElectricityPrice(electricityPricePLN_gr):

    
    # defaults
    PLNperUSD = 4.7
    profitPerMHsDaily_ETH = 0.02721
    profitPerMHsDaily_ETC = 0.02185
    profitPerMHsDaily_RVN = 0.05123


    try:
        PLNperUSD = getUsdPln()
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't fetch USDPLN, using: " + str(PLNperUSD))

    try:
        profitPerMHsDaily_ETH = useProfitCache('ethereum', 1, 0, 0)
    except:    
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't fetch profits for ETH, using: " + str(profitPerMHsDaily_ETH))

    try:
        profitPerMHsDaily_ETC = useProfitCache('ethereumclassic', 1, 0, 0)
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't fetch profits for ETC, using: " + str(profitPerMHsDaily_ETC))
    
    try:
        profitPerMHsDaily_RVN = useProfitCache('ravencoin', 1, 0, 0)
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't fetch profits for RVN, using: " + str(profitPerMHsDaily_RVN))
        
        
    cDict = {}
    cDict['electricityPricePLN_gr'] = float(electricityPricePLN_gr)
    cDict['electricityPricePLN'] = cDict.get('electricityPricePLN_gr') / 100
    cDict['electricityPrice'] = cDict.get('electricityPricePLN')/PLNperUSD

    cDict['rigName_6xRX570_4gb_used'] = "6x RX570 4GB Used"
    link_6xRX570_4gb_used = "https://shop.zet-tech.eu/pl/p/6x-RX-470-4GB-Koparka-kryptowalut/116"
    cDict['link_6xRX570_4gb_used'] = link_6xRX570_4gb_used
    cDict['rigPricePLN_6xRX570_4gb_used'], cDict['hashrate_6xRX570_4gb_used'], cDict['power_6xRX570_4gb_used']  = useShopCache(link_6xRX570_4gb_used, cDict['rigName_6xRX570_4gb_used'], "_6xRX570_4gb_used")
    cDict['profitDailyPLN_6xRX570_4gb_used'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_6xRX570_4gb_used')) - (cDict.get('power_6xRX570_4gb_used') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xRX570_4gb_used'] = int(cDict.get('rigPricePLN_6xRX570_4gb_used')/(cDict.get('profitDailyPLN_6xRX570_4gb_used')))
    if cDict['roi_6xRX570_4gb_used'] < 0:
        cDict['roi_6xRX570_4gb_used'] = "Never :("
    
    
    cDict['rigName_8xRX6600'] = "8x RX6600XT"
    link_8xRX6600 = "https://shop.zet-tech.eu/pl/p/8x-RX-6600XT-Koparka-kryptowalut-NOWOSC/118"
    cDict['link_8xRX6600'] = link_8xRX6600
    cDict['rigPricePLN_8xRX6600'], cDict['hashrate_8xRX6600'], cDict['power_8xRX6600'] = useShopCache(link_8xRX6600, cDict['rigName_8xRX6600'], "_8xRX6600")
    cDict['profitDailyPLN_8xRX6600'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_8xRX6600')) - (cDict.get('power_8xRX6600') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_8xRX6600'] = int(cDict.get('rigPricePLN_8xRX6600')/(cDict.get('profitDailyPLN_8xRX6600')))
    if cDict['roi_8xRX6600'] < 0:
        cDict['roi_8xRX6600'] = "Never :("  
       
       
    cDict['rigName_12xRX6600_octo'] = "OCTOMINER 12x RX6600XT"
    link_12xRX6600_octo = "https://shop.zet-tech.eu/pl/p/OCTOMINER-12x-RX6600/146"
    cDict['link_12xRX6600_octo'] = link_12xRX6600_octo
    cDict['rigPricePLN_12xRX6600_octo'], cDict['hashrate_12xRX6600_octo'], cDict['power_12xRX6600_octo'] = useShopCache(link_12xRX6600_octo, cDict['rigName_12xRX6600_octo'], "_12xRX6600_octo")
    cDict['profitDailyPLN_12xRX6600_octo'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_12xRX6600_octo')) - (cDict.get('power_12xRX6600_octo') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_12xRX6600_octo'] = int(cDict.get('rigPricePLN_12xRX6600_octo')/(cDict.get('profitDailyPLN_12xRX6600_octo')))
    if cDict['roi_12xRX6600_octo'] < 0:
        cDict['roi_12xRX6600_octo'] = "Never :("  
        
        
    cDict['rigName_6xGTX1660TI'] = "6x GTX1660 Super"
    link_6xGTX1660TI = "https://shop.zet-tech.eu/pl/p/6x-GTX-1660-SUPER-Koparka-kryptowalut/74"
    cDict['link_6xGTX1660TI'] = link_6xGTX1660TI
    cDict['rigPricePLN_6xGTX1660TI'], cDict['hashrate_6xGTX1660TI'], cDict['power_6xGTX1660TI'] = useShopCache(link_6xGTX1660TI, cDict['rigName_6xGTX1660TI'], "_6xGTX1660TI")
    cDict['profitDailyPLN_6xGTX1660TI'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_6xGTX1660TI')) - (cDict.get('power_6xGTX1660TI') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xGTX1660TI'] = int(cDict.get('rigPricePLN_6xGTX1660TI')/(cDict.get('profitDailyPLN_6xGTX1660TI')))
    if cDict['roi_6xGTX1660TI'] < 0:
        cDict['roi_6xGTX1660TI'] = "Never :(" 


    cDict['rigName_6xRX6700XT'] = "6x RX6700XT"
    link_6xRX6700XT = "https://shop.zet-tech.eu/pl/p/6x-RX-6700XT-Koparka-kryptowalut-NOWOSC-/94"
    cDict['link_6xRX6700XT'] = link_6xRX6700XT
    cDict['rigPricePLN_6xRX6700XT'], cDict['hashrate_6xRX6700XT'], cDict['power_6xRX6700XT'] = useShopCache(link_6xRX6700XT, cDict['rigName_6xRX6700XT'], "_6xRX6700XT")
    cDict['profitDailyPLN_6xRX6700XT'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_6xRX6700XT')) - (cDict.get('power_6xRX6700XT') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xRX6700XT'] = int(cDict.get('rigPricePLN_6xRX6700XT')/(cDict.get('profitDailyPLN_6xRX6700XT')))
    if cDict['roi_6xRX6700XT'] < 0:
        cDict['roi_6xRX6700XT'] = "Never :("  
        
        
    cDict['rigName_8xRX6700XT_octo'] = "OCTOMINER 8x RX6700XT"
    link_8xRX6700XT_octo = "https://shop.zet-tech.eu/pl/p/OCTOMINER-8x-RX-6700XT/147"
    cDict['link_8xRX6700XT_octo'] = link_8xRX6700XT_octo
    cDict['rigPricePLN_8xRX6700XT_octo'], cDict['hashrate_8xRX6700XT_octo'], cDict['power_8xRX6700XT_octo'] = useShopCache(link_8xRX6700XT_octo, cDict['rigName_8xRX6700XT_octo'], "_8xRX6700XT_octo")
    cDict['profitDailyPLN_8xRX6700XT_octo'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_8xRX6700XT_octo')) - (cDict.get('power_8xRX6700XT_octo') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_8xRX6700XT_octo'] = int(cDict.get('rigPricePLN_8xRX6700XT_octo')/(cDict.get('profitDailyPLN_8xRX6700XT_octo')))
    if cDict['roi_8xRX6700XT_octo'] < 0:
        cDict['roi_8xRX6700XT_octo'] = "Never :(" 


    cDict['rigName_8xRTX2060Super'] = "8x RTX2060 Super"
    link_8xRTX2060Super = "https://shop.zet-tech.eu/pl/p/8x-RTX-2060-SUPER-Koparka-kryptowalut-NOWOSC/145"
    cDict['link_8xRTX2060Super'] = link_8xRTX2060Super
    cDict['rigPricePLN_8xRTX2060Super'], cDict['hashrate_8xRTX2060Super'], cDict['power_8xRTX2060Super'] = useShopCache(link_8xRTX2060Super, cDict['rigName_8xRTX2060Super'], "_8xRTX2060Super")
    cDict['profitDailyPLN_8xRTX2060Super'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_8xRTX2060Super')) - (cDict.get('power_8xRTX2060Super') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_8xRTX2060Super'] = int(cDict.get('rigPricePLN_8xRTX2060Super')/(cDict.get('profitDailyPLN_8xRTX2060Super')))
    if cDict['roi_8xRTX2060Super'] < 0:
        cDict['roi_8xRTX2060Super'] = "Never :("    


    cDict['rigName_6xRTX3060ti'] = "6x RTX3060 TI"
    link_6xRTX3060ti = "https://shop.zet-tech.eu/pl/p/6x-RTX-3060-Ti-Koparka-kryptowalut/119"
    cDict['link_6xRTX3060ti'] = link_6xRTX3060ti
    cDict['rigPricePLN_6xRTX3060ti'], cDict['hashrate_6xRTX3060ti'], cDict['power_6xRTX3060ti'] = useShopCache(link_6xRTX3060ti, cDict['rigName_6xRTX3060ti'], "_6xRTX3060ti")
    cDict['profitDailyPLN_6xRTX3060ti'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_6xRTX3060ti')) - (cDict.get('power_6xRTX3060ti') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xRTX3060ti'] = int(cDict.get('rigPricePLN_6xRTX3060ti')/(cDict.get('profitDailyPLN_6xRTX3060ti')))
    if cDict['roi_6xRTX3060ti'] < 0:
        cDict['roi_6xRTX3060ti'] = "Never :("   
        

    cDict['rigName_3xRTX3070ti'] = "3x RTX3070 TI"
    link_3xRTX3070ti = "https://shop.zet-tech.eu/pl/p/3x-RTX-3070-Ti-Koparka-kryptowalut/124"
    cDict['link_3xRTX3070ti'] = link_3xRTX3070ti
    cDict['rigPricePLN_3xRTX3070ti'], cDict['hashrate_3xRTX3070ti'], cDict['power_3xRTX3070ti'] = useShopCache(link_3xRTX3070ti, cDict['rigName_3xRTX3070ti'], "_3xRTX3070ti")
    cDict['profitDailyPLN_3xRTX3070ti'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_3xRTX3070ti')) - (cDict.get('power_3xRTX3070ti') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_3xRTX3070ti'] = int(cDict.get('rigPricePLN_3xRTX3070ti')/(cDict.get('profitDailyPLN_3xRTX3070ti')))
    if cDict['roi_3xRTX3070ti'] < 0:
        cDict['roi_3xRTX3070ti'] = "Never :(" 
        

    cDict['rigName_6xRTX3070ti'] = "6x RTX3070 TI"
    link_6xRTX3070ti = "https://shop.zet-tech.eu/pl/p/6x-RTX-3070-Ti-Koparka-kryptowalut/89"
    cDict['link_6xRTX3070ti'] = link_6xRTX3070ti
    cDict['rigPricePLN_6xRTX3070ti'], cDict['hashrate_6xRTX3070ti'], cDict['power_6xRTX3070ti'] = useShopCache(link_6xRTX3070ti, cDict['rigName_6xRTX3070ti'], "_6xRTX3070ti")
    cDict['profitDailyPLN_6xRTX3070ti'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_6xRTX3070ti')) - (cDict.get('power_6xRTX3070ti') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xRTX3070ti'] = int(cDict.get('rigPricePLN_6xRTX3070ti')/(cDict.get('profitDailyPLN_6xRTX3070ti')))
    if cDict['roi_6xRTX3070ti'] < 0:
        cDict['roi_6xRTX3070ti'] = "Never :(" 


    cDict['rigName_6xRX6800'] = "6x RX6800"
    link_6xRX6800 = "https://shop.zet-tech.eu/pl/p/6x-RX-6800-Koparka-kryptowalut-NOWOSC/140"
    cDict['link_6xRX6800'] = link_6xRX6800
    cDict['rigPricePLN_6xRX6800'], cDict['hashrate_6xRX6800'], cDict['power_6xRX6800'] = useShopCache(link_6xRX6800, cDict['rigName_6xRX6800'], "_6xRX6800")
    cDict['profitDailyPLN_6xRX6800'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_6xRX6800')) - (cDict.get('power_6xRX6800') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xRX6800'] = int(cDict.get('rigPricePLN_6xRX6800')/(cDict.get('profitDailyPLN_6xRX6800')))
    if cDict['roi_6xRX6800'] < 0:
        cDict['roi_6xRX6800'] = "Never :("   


    cDict['rigName_3xRTX3090'] = "3x RTX3090"
    link_3xRTX3090 = "https://shop.zet-tech.eu/pl/p/3x-RTX-3090-Koparka-kryptowalut/111"
    cDict['link_3xRTX3090'] = link_3xRTX3090
    cDict['rigPricePLN_3xRTX3090'], cDict['hashrate_3xRTX3090'], cDict['power_3xRTX3090'] = useShopCache(link_3xRTX3090, cDict['rigName_3xRTX3090'], "_3xRTX3090")
    cDict['profitDailyPLN_3xRTX3090'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_3xRTX3090')) - (cDict.get('power_3xRTX3090') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_3xRTX3090'] = int(cDict.get('rigPricePLN_3xRTX3090')/(cDict.get('profitDailyPLN_3xRTX3090')))
    if cDict['roi_3xRTX3090'] < 0:
        cDict['roi_3xRTX3090'] = "Never :("
        
        
    cDict['rigName_6xRTX3090'] = "6x RTX3090"
    link_6xRTX3090 = "https://shop.zet-tech.eu/pl/p/6x-RTX-3090-Koparka-kryptowalut-/72"
    cDict['link_6xRTX3090'] = link_6xRTX3090
    cDict['rigPricePLN_6xRTX3090'], cDict['hashrate_6xRTX3090'], cDict['power_6xRTX3090'] = useShopCache(link_6xRTX3090, cDict['rigName_6xRTX3090'], "_6xRTX3090")
    cDict['profitDailyPLN_6xRTX3090'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_6xRTX3090')) - (cDict.get('power_6xRTX3090') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xRTX3090'] = int(cDict.get('rigPricePLN_6xRTX3090')/(cDict.get('profitDailyPLN_6xRTX3090')))
    if cDict['roi_6xRTX3090'] < 0:
        cDict['roi_6xRTX3090'] = "Never :("
        
        
    cDict['rigName_8xRTX3080_octo'] = "OCTOMINER 8x RTX3080"
    link_8xRTX3080_octo = "https://shop.zet-tech.eu/pl/p/OCTOMINER-8x-RTX-3080/148"
    cDict['link_8xRTX3080_octo'] = link_8xRTX3080_octo
    cDict['rigPricePLN_8xRTX3080_octo'], cDict['hashrate_8xRTX3080_octo'], cDict['power_8xRTX3080_octo'] = useShopCache(link_8xRTX3080_octo, cDict['rigName_8xRTX3080_octo'], "_8xRTX3080_octo")
    cDict['profitDailyPLN_8xRTX3080_octo'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_8xRTX3080_octo')) - (cDict.get('power_8xRTX3080_octo') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_8xRTX3080_octo'] = int(cDict.get('rigPricePLN_8xRTX3080_octo')/(cDict.get('profitDailyPLN_8xRTX3080_octo')))
    if cDict['roi_8xRTX3080_octo'] < 0:
        cDict['roi_8xRTX3080_octo'] = "Never :("
        
        
    cDict['rigName_8xRTX3090_octo'] = "OCTOMINER 8x RTX3090"
    link_8xRTX3090_octo = "https://shop.zet-tech.eu/pl/p/OCTOMINER-8x-RTX-3090/149"
    cDict['link_8xRTX3090_octo'] = link_8xRTX3090_octo
    cDict['rigPricePLN_8xRTX3090_octo'], cDict['hashrate_8xRTX3090_octo'], cDict['power_8xRTX3090_octo'] = useShopCache(link_8xRTX3090_octo, cDict['rigName_8xRTX3090_octo'], "_8xRTX3090_octo")
    cDict['profitDailyPLN_8xRTX3090_octo'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_8xRTX3090_octo')) - (cDict.get('power_8xRTX3090_octo') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_8xRTX3090_octo'] = int(cDict.get('rigPricePLN_8xRTX3090_octo')/(cDict.get('profitDailyPLN_8xRTX3090_octo')))
    if cDict['roi_8xRTX3090_octo'] < 0:
        cDict['roi_8xRTX3090_octo'] = "Never :("
        
        
    cDict['rigName_48xRX6700'] = "48x RX6700"
    link_48xRX6700 = "https://shop.zet-tech.eu/pl/p/48-x-RX-6700-Koparka-kryptowalut-NAJMOCNIEJSZA/44"
    cDict['link_48xRX6700'] = link_48xRX6700
    cDict['rigPricePLN_48xRX6700'], cDict['hashrate_48xRX6700'], cDict['power_48xRX6700'] = useShopCache(link_48xRX6700, cDict['rigName_48xRX6700'], "_48xRX6700")
    cDict['profitDailyPLN_48xRX6700'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_48xRX6700')) - (cDict.get('power_48xRX6700') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_48xRX6700'] = int(cDict.get('rigPricePLN_48xRX6700')/(cDict.get('profitDailyPLN_48xRX6700')))
    if cDict['roi_48xRX6700'] < 0:
        cDict['roi_48xRX6700'] = "Never :("
        
    
    cDict['rigName_200xRX6700'] = "Mining Farm RX6700" # 90x 6x6700
    link_200xRX6700 = "https://shop.zet-tech.eu/pl/p/Kopalnia-kryptowalut/103"
    cDict['link_200xRX6700'] = link_200xRX6700
    cDict['rigPricePLN_200xRX6700'], cDict['hashrate_200xRX6700'], cDict['power_200xRX6700'] = useShopCache(link_200xRX6700, cDict['rigName_200xRX6700'], "_200xRX6700")
    cDict['profitDailyPLN_200xRX6700'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_200xRX6700')) - (cDict.get('power_200xRX6700') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_200xRX6700'] = int(cDict.get('rigPricePLN_200xRX6700')/(cDict.get('profitDailyPLN_200xRX6700')))
    if cDict['roi_200xRX6700'] < 0:
        cDict['roi_200xRX6700'] = "Never :("
        
        
    cDict['rigName_540xRTX3070'] = "Mining Farm RTX3070"
    link_540xRTX3070 = "https://shop.zet-tech.eu/pl/p/Kopalnia-kryptowalut-RTX-3070/153"
    cDict['link_540xRTX3070'] = link_540xRTX3070
    cDict['rigPricePLN_540xRTX3070'], cDict['hashrate_540xRTX3070'], cDict['power_540xRTX3070'] = useShopCache(link_540xRTX3070, cDict['rigName_540xRTX3070'], "_540xRTX3070")
    cDict['profitDailyPLN_540xRTX3070'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_540xRTX3070')) - (cDict.get('power_540xRTX3070') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_540xRTX3070'] = int(cDict.get('rigPricePLN_540xRTX3070')/(cDict.get('profitDailyPLN_540xRTX3070')))
    if cDict['roi_540xRTX3070'] < 0:
        cDict['roi_540xRTX3070'] = "Never :("
    
    
    # ---------------------------- OBM -----------------------------
    

    cDict['rigName_obm_10xRTX3070'] = "10x RTX3070"
    link_obm_10xRTX3070 = "https://onlybestminers.com/pl_pl/produkt/gpu-obm10xrtx3070/"
    cDict['link_obm_10xRTX3070'] = link_obm_10xRTX3070
    cDict['rigPricePLN_obm_10xRTX3070'], cDict['hashrate_obm_10xRTX3070'], cDict['power_obm_10xRTX3070'] = useShopCache(link_obm_10xRTX3070, cDict['rigName_obm_10xRTX3070'], "_obm_10xRTX3070", "OBM")
    cDict['profitDailyPLN_obm_10xRTX3070'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_obm_10xRTX3070')) - (cDict.get('power_obm_10xRTX3070') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_obm_10xRTX3070'] = int(cDict.get('rigPricePLN_obm_10xRTX3070')/(cDict.get('profitDailyPLN_obm_10xRTX3070')))
    if cDict['roi_obm_10xRTX3070'] < 0:
        cDict['roi_obm_10xRTX3070'] = "Never :("    

    return cDict
    
    

    
@app.route('/', defaults={'electricityPricePLN_gr': 0}, methods=['GET', 'POST'])
@app.route('/<int:electricityPricePLN_gr>', methods=['GET', 'POST'])
def profitCalculator(electricityPricePLN_gr):
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Calculator Started!")
    
    if request.method == 'POST':
        print("request.method == POST!")
        electricityPricePLN_gr = request.form['electricityPricePLN_gr']
        cDict = doCalculationsForElectricityPrice(electricityPricePLN_gr)
        
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Calculator Done!")
        return render_template('calculator.html', electricityPricePLN_gr=electricityPricePLN_gr, cDict=cDict)

        
    else:
        print("request.method == GET!")
        cDict = doCalculationsForElectricityPrice(electricityPricePLN_gr)
        
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Calculator Done!") 
        return render_template('calculator.html', electricityPricePLN_gr=electricityPricePLN_gr, cDict=cDict)


if __name__ == '__main__':
    app.run(debug = False)
        
        
        
    


    