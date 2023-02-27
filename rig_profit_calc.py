from flask import Flask, render_template, request

import requests
import aiohttp
import asyncio
import time
import os
import sqlite3
import json
import ast

from bs4 import BeautifulSoup
from datetime import datetime


shop_caching_time = 60 * 30 # 30 minutes
profit_caching_time = 60 * 60 # 60 minutes
usdpln_caching_time = 60 * 60 * 6 # 6 hours

app = Flask(__name__)


def getUsdPln():
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting USDPLN  ...")  
    response = requests.get('https://api.nbp.pl/api/exchangerates/rates/a/usd/?format=json', timeout = 3)
    usdpln = json.loads(response.text)['rates'][0]['mid']
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] USDPLN done! Value: "+str(usdpln))
    return usdpln


def useUsdPlnCache():
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting useUsdPlnCache ...")
    timestamp = 0
    
    db_path = "db/cacheFromUsdPln.db"
    path = 'db'
    createDirIfNotExist(path)
    
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS UsdPln (
            timestamp TEXT,
            usdpln TEXT
            )""")
        c.execute("""SELECT timestamp, usdpln FROM UsdPln ORDER BY timestamp DESC LIMIT 1""")
        for row in c.fetchall():
            timestamp = int(row[0])
            usdpln = float(row[1])
         
        c.close()
        conn.close() 
         
    timeNow = int(time.time())
    if timestamp + profit_caching_time < timeNow:
        usdpln = getUsdPln()
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS UsdPln (
            timestamp TEXT,
            usdpln TEXT
            )""")     
            
        c.execute("""INSERT INTO UsdPln VALUES(
            ?,  ?)""", (timeNow, usdpln))
            
        c.execute("""Delete from UsdPln where timestamp <> (Select max (timestamp) from UsdPln)""")
        
        conn.commit()
        c.close()
        conn.close()        

        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Updating UsdPlnCache")
        
    else:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Using cached values for usdpln")
        
    return usdpln  
  
  
def getProfitDaily(coin ='162', hashrate=1, power=0, electricityPrice=0.0):
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting API for "+coin+" ...")
    hashrate = hashrate*10**3 # 1 Gh/s for ETC 
    response = requests.get("https://whattomine.com/coins/"+str(coin)+".json?hr="+str(hashrate)+"&p="+str(power)+"&fee=0.0&cost={electricityPrice}&cost_currency=USD&hcost=0.0&span_br=&span_d=24", timeout=2)
    profitDaily = float(json.loads(response.text)['profit'].replace('$', '').replace(',', ''))/10**3
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] API for "+coin+" done! Value: "+str(profitDaily))
    return profitDaily
    

def useProfitCache(coin, hashrate, power, electricityPrice):
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting useProfitCache for "+str(coin)+" ...")
    timestamp = 0
    
    db_path = "db/cacheFromProfit.db"
    path = 'db'
    createDirIfNotExist(path)
    
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS coin_"""+coin+""" (
            timestamp TEXT,
            profitability TEXT
            )""")
        c.execute("""SELECT timestamp, profitability FROM coin_"""+coin+""" ORDER BY timestamp DESC LIMIT 1""")
        for row in c.fetchall():
            timestamp = int(row[0])
            profitDaily = float(row[1])
         
        c.close()
        conn.close()
         
    timeNow = int(time.time())
    if timestamp + profit_caching_time < timeNow:
        profitDaily = getProfitDaily(coin, hashrate, power, electricityPrice)
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS coin_"""+coin+""" (
            timestamp TEXT,
            profitability TEXT
            )""")     
            
        c.execute("""INSERT INTO coin_"""+coin+""" VALUES(
            ?,  ?)""", (timeNow, profitDaily))
            
        c.execute("""Delete from coin_"""+coin+""" where timestamp <> (Select max (timestamp) from coin_"""+coin+""")""")
        
        conn.commit()

        c.close()
        conn.close()        

        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Updating ProfitCache, using new values for "+str(coin))
        
    else:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Using cached values for "+str(coin))
        
    return profitDaily
    
 

async def get_page(session, url, name): 
    async with session.get(url) as r:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Calling "+name+" ...")
        return await r.text()
  
  
async def get_all(session, urls, names):
    tasks = []
    i = 0
    for url in urls:
        task = asyncio.create_task(get_page(session, url, names[i]))
        tasks.append(task)
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Addes task for: "+names[i])
        i = i + 1
    results = await asyncio.gather(*tasks)
    return results
    
    
async def main(urls, names):
    async with aiohttp.ClientSession() as session:
        data = await get_all(session, urls, names)
        return data
   
   
def makeSoup(results, names):
  
    jars_of_soup = []
    i = 0
    for html in results:
        soup = BeautifulSoup(html, "html.parser")
        jars_of_soup.append(soup)
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] soup from "+names[i]+" added to jar!")
        i = i + 1
    return jars_of_soup
          
        
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
         
 

def readAndUpdateCache(names, urls, tableNames, vendors):
    db_path = "db/cacheFromShop.db"
    path = 'db'
    createDirIfNotExist(path)
    
    # read data from db
    
    timestamp = 0 
    
    final_prices = []
    final_hashrates = []
    final_wattages = []
   
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        for tableName in tableNames:
            c.execute("""CREATE TABLE IF NOT EXISTS """+tableName+""" (
                timestamp TEXT,
                price TEXT,
                hashrate TEXT,
                wattage TEXT
                )""")
            c.execute("""SELECT timestamp, price, hashrate, wattage FROM """+tableName+""" ORDER BY timestamp DESC LIMIT 1""")
            for row in c.fetchall():
                timestamp = int(row[0])
                final_prices.append(int(row[1]))
                final_hashrates.append(int(row[2]))
                final_wattages.append(int(row[3]))
    
        c.close()
        conn.close()
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Got data from cache") 

    # update data in db
        
    timeNow = int(time.time())   
    if timestamp + shop_caching_time < timeNow:
        final_prices = []
        final_hashrates = []
        final_wattages = []
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        results = asyncio.run(main(urls, names))
        jars_of_soup = makeSoup(results, names)
        
        i = 0
        for soup in jars_of_soup:
            final_price = getPriceFromSoup(soup, names[i], vendors[i])
            final_hashrate = getHashrateFromSoup(soup, names[i], vendors[i])
            final_wattage = getWattageFromSoup(soup, names[i], vendors[i])
            
            final_prices.append(final_price)
            final_hashrates.append(final_hashrate)
            final_wattages.append(final_wattage)
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("""CREATE TABLE IF NOT EXISTS """+tableNames[i]+""" (
                timestamp TEXT,
                price TEXT,
                hashrate TEXT,
                wattage TEXT
                )""")
                
            c.execute("""INSERT INTO """+tableNames[i]+""" VALUES(
                ?, ?, ?, ?)""", (timeNow, final_price, final_hashrate, final_wattage))
                
            c.execute("""Delete from """+tableNames[i]+""" where timestamp <> (Select max (timestamp) from """+tableNames[i]+""")""")
            
            conn.commit() 
            c.close()
            conn.close()
            
            print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Updating cache for "+str(names[i]))
            i=i+1
        
    
    return final_prices, final_hashrates, final_wattages
    
   
def doCalculationsForElectricityPrice(electricityPricePLN_gr):



    # defaults
    PLNperUSD = 4.5
    profitPerMHsDaily_ETC = 0.02185
    #profitPerMHsDaily_RVN = 0.05123


    try:
        PLNperUSD = useUsdPlnCache()
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't fetch USDPLN, using: " + str(PLNperUSD))


    try:
        # ethereumclassic
        profitPerMHsDaily_ETC = useProfitCache('162', 1, 0, 0) 
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't fetch profits for ETC, using: " + str(profitPerMHsDaily_ETC))
    '''
    try:
        profitPerMHsDaily_RVN = useProfitCache('ravencoin', 1, 0, 0)
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't fetch profits for RVN, using: " + str(profitPerMHsDaily_RVN))
    '''    
        
    cDict = {}
    cDict['electricityPricePLN_gr'] = float(electricityPricePLN_gr)
    cDict['electricityPricePLN'] = cDict.get('electricityPricePLN_gr') / 100
    cDict['electricityPrice'] = cDict.get('electricityPricePLN')/PLNperUSD

    
    cDict['rigName_6xRX570_4gb_used'] = "ZET 6x RX570 4GB Used "
    link_6xRX570_4gb_used = "https://shop.zet-tech.eu/pl/p/6x-RX-470-4GB-Koparka-kryptowalut/116"
    cDict['link_6xRX570_4gb_used'] = link_6xRX570_4gb_used
    
    cDict['rigName_8xRX6600'] = "ZET 8x RX6600XT"
    link_8xRX6600 = "https://shop.zet-tech.eu/pl/p/8x-RX-6600XT-Koparka-kryptowalut-NOWOSC/118"
    cDict['link_8xRX6600'] = link_8xRX6600
    
    cDict['rigName_12xRX6600_octo'] = "ZET OCTOMINER 12x RX6600XT"
    link_12xRX6600_octo = "https://shop.zet-tech.eu/pl/p/OCTOMINER-12x-RX6600/146"
    cDict['link_12xRX6600_octo'] = link_12xRX6600_octo
    
    cDict['rigName_6xGTX1660TI'] = "ZET 6x GTX1660 Super"
    link_6xGTX1660TI = "https://shop.zet-tech.eu/pl/p/6x-GTX-1660-SUPER-Koparka-kryptowalut/74"
    cDict['link_6xGTX1660TI'] = link_6xGTX1660TI
    
    cDict['rigName_6xRX6700XT'] = "ZET 6x RX6700XT"
    link_6xRX6700XT = "https://shop.zet-tech.eu/pl/p/6x-RX-6700XT-Koparka-kryptowalut-NOWOSC-/94"
    cDict['link_6xRX6700XT'] = link_6xRX6700XT
    
    cDict['rigName_8xRX6700XT_octo'] = "ZET OCTOMINER 8x RX6700XT"
    link_8xRX6700XT_octo = "https://shop.zet-tech.eu/pl/p/OCTOMINER-8x-RX-6700XT/147"
    cDict['link_8xRX6700XT_octo'] = link_8xRX6700XT_octo
    
    cDict['rigName_8xRTX2060Super'] = "ZET 8x RTX2060 Super"
    link_8xRTX2060Super = "https://shop.zet-tech.eu/pl/p/8x-RTX-2060-SUPER-Koparka-kryptowalut-NOWOSC/145"
    cDict['link_8xRTX2060Super'] = link_8xRTX2060Super
    
    cDict['rigName_6xRTX3060ti'] = "ZET 6x RTX3060 TI"
    link_6xRTX3060ti = "https://shop.zet-tech.eu/pl/p/6x-RTX-3060-Ti-Koparka-kryptowalut/119"
    cDict['link_6xRTX3060ti'] = link_6xRTX3060ti
    
    cDict['rigName_3xRTX3070ti'] = "ZET 3x RTX3070 TI"
    link_3xRTX3070ti = "https://shop.zet-tech.eu/pl/p/3x-RTX-3070-Ti-Koparka-kryptowalut/124"
    cDict['link_3xRTX3070ti'] = link_3xRTX3070ti
    
    cDict['rigName_6xRTX3070ti'] = "ZET 6x RTX3070 TI"
    link_6xRTX3070ti = "https://shop.zet-tech.eu/pl/p/6x-RTX-3070-Ti-Koparka-kryptowalut/89"
    cDict['link_6xRTX3070ti'] = link_6xRTX3070ti
    
    cDict['rigName_6xRX6800'] = "ZET 6x RX6800"
    link_6xRX6800 = "https://shop.zet-tech.eu/pl/p/6x-RX-6800-Koparka-kryptowalut-NOWOSC/140"
    cDict['link_6xRX6800'] = link_6xRX6800
    
    cDict['rigName_3xRTX3090'] = "ZET 3x RTX3090"
    link_3xRTX3090 = "https://shop.zet-tech.eu/pl/p/3x-RTX-3090-Koparka-kryptowalut/111"
    cDict['link_3xRTX3090'] = link_3xRTX3090
    
    cDict['rigName_6xRTX3090'] = "ZET 6x RTX3090"
    link_6xRTX3090 = "https://shop.zet-tech.eu/pl/p/6x-RTX-3090-Koparka-kryptowalut-/72"
    cDict['link_6xRTX3090'] = link_6xRTX3090
    
    cDict['rigName_8xRTX3080_octo'] = "ZET OCTOMINER 8x RTX3080"
    link_8xRTX3080_octo = "https://shop.zet-tech.eu/pl/p/OCTOMINER-8x-RTX-3080/148"
    cDict['link_8xRTX3080_octo'] = link_8xRTX3080_octo
    
    cDict['rigName_8xRTX3090_octo'] = "ZET OCTOMINER 8x RTX3090"
    link_8xRTX3090_octo = "https://shop.zet-tech.eu/pl/p/OCTOMINER-8x-RTX-3090/149"
    cDict['link_8xRTX3090_octo'] = link_8xRTX3090_octo
    
    cDict['rigName_48xRX6700'] = "ZET 48x RX6700"
    link_48xRX6700 = "https://shop.zet-tech.eu/pl/p/48-x-RX-6700-Koparka-kryptowalut-NAJMOCNIEJSZA/44"
    cDict['link_48xRX6700'] = link_48xRX6700
    
    cDict['rigName_200xRX6700'] = "ZET Mining Farm RX6700" # 90x 6x6700
    link_200xRX6700 = "https://shop.zet-tech.eu/pl/p/Kopalnia-kryptowalut/103"
    cDict['link_200xRX6700'] = link_200xRX6700
    
    cDict['rigName_540xRTX3070'] = "ZET Mining Farm RTX3070"
    link_540xRTX3070 = "https://shop.zet-tech.eu/pl/p/Kopalnia-kryptowalut-RTX-3070/153"
    cDict['link_540xRTX3070'] = link_540xRTX3070
    
    cDict['rigName_obm_10xRTX3070'] = "OBM 10x RTX3070"
    link_obm_10xRTX3070 = "https://onlybestminers.com/pl_pl/produkt/gpu-obm10xrtx3070/"
    cDict['link_obm_10xRTX3070'] = link_obm_10xRTX3070
    
    cDict['rigName_6xRTX3070'] = "ZET 10x RTX3070"
    link_6xRTX3070 = "https://shop.zet-tech.eu/pl/p/6x-RTX-3070-Koparka-kryptowalut/150"
    cDict['link_6xRTX3070'] = link_6xRTX3070

    
    names = [cDict['rigName_6xRX570_4gb_used'], cDict['rigName_8xRX6600'],cDict['rigName_12xRX6600_octo'], cDict['rigName_6xGTX1660TI'],
        cDict['rigName_6xRX6700XT'], cDict['rigName_8xRX6700XT_octo'], cDict['rigName_8xRTX2060Super'], cDict['rigName_6xRTX3060ti'],
        cDict['rigName_3xRTX3070ti'], cDict['rigName_6xRTX3070ti'], cDict['rigName_6xRX6800'], cDict['rigName_3xRTX3090'],
        cDict['rigName_6xRTX3090'], cDict['rigName_8xRTX3080_octo'], cDict['rigName_8xRTX3090_octo'], cDict['rigName_48xRX6700'],
        cDict['rigName_200xRX6700'], cDict['rigName_540xRTX3070'], cDict['rigName_obm_10xRTX3070'], cDict['rigName_6xRTX3070']
    ]
    
    tableNames = []
    vendors = []
    for name in names:
        tableNames.append(str("_"+name.replace(" ", "")))
        vendors.append(name[0:3])
        
    
    urls = [link_6xRX570_4gb_used, link_8xRX6600, link_12xRX6600_octo, link_6xGTX1660TI, 
        link_6xRX6700XT, link_8xRX6700XT_octo, link_8xRTX2060Super, link_6xRTX3060ti,
        link_3xRTX3070ti, link_6xRTX3070ti, link_6xRX6800, link_3xRTX3090,
        link_6xRTX3090, link_8xRTX3080_octo, link_8xRTX3090_octo, link_48xRX6700,
        link_200xRX6700, link_540xRTX3070, link_obm_10xRTX3070, link_6xRTX3070
    ] 
    

    
    final_prices, final_hashrates, final_wattages = readAndUpdateCache(names, urls, tableNames, vendors)

    cDict['rigPricePLN_6xRX570_4gb_used'] = final_prices.pop(0)
    cDict['hashrate_6xRX570_4gb_used'] = final_hashrates.pop(0)
    cDict['power_6xRX570_4gb_used'] = final_wattages.pop(0)
    cDict['profitDailyPLN_6xRX570_4gb_used'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_6xRX570_4gb_used')) - (cDict.get('power_6xRX570_4gb_used') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xRX570_4gb_used'] = int(cDict.get('rigPricePLN_6xRX570_4gb_used')/(cDict.get('profitDailyPLN_6xRX570_4gb_used')))
    if cDict['roi_6xRX570_4gb_used'] < 0:
        cDict['roi_6xRX570_4gb_used'] = "Never :("
        
    cDict['rigPricePLN_8xRX6600'] = final_prices.pop(0)
    cDict['hashrate_8xRX6600'] = final_hashrates.pop(0)
    cDict['power_8xRX6600'] = final_wattages.pop(0)
    cDict['profitDailyPLN_8xRX6600'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_8xRX6600')) - (cDict.get('power_8xRX6600') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_8xRX6600'] = int(cDict.get('rigPricePLN_8xRX6600')/(cDict.get('profitDailyPLN_8xRX6600')))
    if cDict['roi_8xRX6600'] < 0:
        cDict['roi_8xRX6600'] = "Never :("
        
    cDict['rigPricePLN_12xRX6600_octo'] = final_prices.pop(0)
    cDict['hashrate_12xRX6600_octo'] = final_hashrates.pop(0)
    cDict['power_12xRX6600_octo'] = final_wattages.pop(0)
    cDict['profitDailyPLN_12xRX6600_octo'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_12xRX6600_octo')) - (cDict.get('power_12xRX6600_octo') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_12xRX6600_octo'] = int(cDict.get('rigPricePLN_12xRX6600_octo')/(cDict.get('profitDailyPLN_12xRX6600_octo')))
    if cDict['roi_12xRX6600_octo'] < 0:
        cDict['roi_12xRX6600_octo'] = "Never :("
    
    cDict['rigPricePLN_6xGTX1660TI'] = final_prices.pop(0)
    cDict['hashrate_6xGTX1660TI'] = final_hashrates.pop(0)
    cDict['power_6xGTX1660TI'] = final_wattages.pop(0)
    cDict['profitDailyPLN_6xGTX1660TI'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_6xGTX1660TI')) - (cDict.get('power_6xGTX1660TI') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xGTX1660TI'] = int(cDict.get('rigPricePLN_6xGTX1660TI')/(cDict.get('profitDailyPLN_6xGTX1660TI')))
    if cDict['roi_6xGTX1660TI'] < 0:
        cDict['roi_6xGTX1660TI'] = "Never :("
    
    cDict['rigPricePLN_6xRX6700XT'] = final_prices.pop(0)
    cDict['hashrate_6xRX6700XT'] = final_hashrates.pop(0)
    cDict['power_6xRX6700XT'] = final_wattages.pop(0)
    cDict['profitDailyPLN_6xRX6700XT'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_6xRX6700XT')) - (cDict.get('power_6xRX6700XT') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xRX6700XT'] = int(cDict.get('rigPricePLN_6xRX6700XT')/(cDict.get('profitDailyPLN_6xRX6700XT')))
    if cDict['roi_6xRX6700XT'] < 0:
        cDict['roi_6xRX6700XT'] = "Never :("
        
    cDict['rigPricePLN_8xRX6700XT_octo'] = final_prices.pop(0)
    cDict['hashrate_8xRX6700XT_octo'] = final_hashrates.pop(0)
    cDict['power_8xRX6700XT_octo'] = final_wattages.pop(0)
    cDict['profitDailyPLN_8xRX6700XT_octo'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_8xRX6700XT_octo')) - (cDict.get('power_8xRX6700XT_octo') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_8xRX6700XT_octo'] = int(cDict.get('rigPricePLN_8xRX6700XT_octo')/(cDict.get('profitDailyPLN_8xRX6700XT_octo')))
    if cDict['roi_8xRX6700XT_octo'] < 0:
        cDict['roi_8xRX6700XT_octo'] = "Never :("
        
    cDict['rigPricePLN_8xRTX2060Super'] = final_prices.pop(0)
    cDict['hashrate_8xRTX2060Super'] = final_hashrates.pop(0)
    cDict['power_8xRTX2060Super'] = final_wattages.pop(0)
    cDict['profitDailyPLN_8xRTX2060Super'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_8xRTX2060Super')) - (cDict.get('power_8xRTX2060Super') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_8xRTX2060Super'] = int(cDict.get('rigPricePLN_8xRTX2060Super')/(cDict.get('profitDailyPLN_8xRTX2060Super')))
    if cDict['roi_8xRTX2060Super'] < 0:
        cDict['roi_8xRTX2060Super'] = "Never :("
        
    cDict['rigPricePLN_6xRTX3060ti'] = final_prices.pop(0)
    cDict['hashrate_6xRTX3060ti'] = final_hashrates.pop(0)
    cDict['power_6xRTX3060ti'] = final_wattages.pop(0)
    cDict['profitDailyPLN_6xRTX3060ti'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_6xRTX3060ti')) - (cDict.get('power_6xRTX3060ti') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xRTX3060ti'] = int(cDict.get('rigPricePLN_6xRTX3060ti')/(cDict.get('profitDailyPLN_6xRTX3060ti')))
    if cDict['roi_6xRTX3060ti'] < 0:
        cDict['roi_6xRTX3060ti'] = "Never :("
        
    cDict['rigPricePLN_3xRTX3070ti'] = final_prices.pop(0)
    cDict['hashrate_3xRTX3070ti'] = final_hashrates.pop(0)
    cDict['power_3xRTX3070ti'] = final_wattages.pop(0)
    cDict['profitDailyPLN_3xRTX3070ti'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_3xRTX3070ti')) - (cDict.get('power_3xRTX3070ti') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_3xRTX3070ti'] = int(cDict.get('rigPricePLN_3xRTX3070ti')/(cDict.get('profitDailyPLN_3xRTX3070ti')))
    if cDict['roi_3xRTX3070ti'] < 0:
        cDict['roi_3xRTX3070ti'] = "Never :("
        
    cDict['rigPricePLN_6xRTX3070ti'] = final_prices.pop(0)
    cDict['hashrate_6xRTX3070ti'] = final_hashrates.pop(0)
    cDict['power_6xRTX3070ti'] = final_wattages.pop(0)
    cDict['profitDailyPLN_6xRTX3070ti'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_6xRTX3070ti')) - (cDict.get('power_6xRTX3070ti') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xRTX3070ti'] = int(cDict.get('rigPricePLN_6xRTX3070ti')/(cDict.get('profitDailyPLN_6xRTX3070ti')))
    if cDict['roi_6xRTX3070ti'] < 0:
        cDict['roi_6xRTX3070ti'] = "Never :("
        
    cDict['rigPricePLN_6xRX6800'] = final_prices.pop(0)
    cDict['hashrate_6xRX6800'] = final_hashrates.pop(0)
    cDict['power_6xRX6800'] = final_wattages.pop(0)
    cDict['profitDailyPLN_6xRX6800'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_6xRX6800')) - (cDict.get('power_6xRX6800') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xRX6800'] = int(cDict.get('rigPricePLN_6xRX6800')/(cDict.get('profitDailyPLN_6xRX6800')))
    if cDict['roi_6xRX6800'] < 0:
        cDict['roi_6xRX6800'] = "Never :("
        
    cDict['rigPricePLN_3xRTX3090'] = final_prices.pop(0)
    cDict['hashrate_3xRTX3090'] = final_hashrates.pop(0)
    cDict['power_3xRTX3090'] = final_wattages.pop(0)
    cDict['profitDailyPLN_3xRTX3090'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_3xRTX3090')) - (cDict.get('power_3xRTX3090') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_3xRTX3090'] = int(cDict.get('rigPricePLN_3xRTX3090')/(cDict.get('profitDailyPLN_3xRTX3090')))
    if cDict['roi_3xRTX3090'] < 0:
        cDict['roi_3xRTX3090'] = "Never :("
        
    cDict['rigPricePLN_6xRTX3090'] = final_prices.pop(0)
    cDict['hashrate_6xRTX3090'] = final_hashrates.pop(0)
    cDict['power_6xRTX3090'] = final_wattages.pop(0)
    cDict['profitDailyPLN_6xRTX3090'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_6xRTX3090')) - (cDict.get('power_6xRTX3090') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xRTX3090'] = int(cDict.get('rigPricePLN_6xRTX3090')/(cDict.get('profitDailyPLN_6xRTX3090')))
    if cDict['roi_6xRTX3090'] < 0:
        cDict['roi_6xRTX3090'] = "Never :("
        
    cDict['rigPricePLN_8xRTX3080_octo'] = final_prices.pop(0)
    cDict['hashrate_8xRTX3080_octo'] = final_hashrates.pop(0)
    cDict['power_8xRTX3080_octo'] = final_wattages.pop(0)
    cDict['profitDailyPLN_8xRTX3080_octo'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_8xRTX3080_octo')) - (cDict.get('power_8xRTX3080_octo') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_8xRTX3080_octo'] = int(cDict.get('rigPricePLN_8xRTX3080_octo')/(cDict.get('profitDailyPLN_8xRTX3080_octo')))
    if cDict['roi_8xRTX3080_octo'] < 0:
        cDict['roi_8xRTX3080_octo'] = "Never :("
        
    cDict['rigPricePLN_8xRTX3090_octo'] = final_prices.pop(0)
    cDict['hashrate_8xRTX3090_octo'] = final_hashrates.pop(0)
    cDict['power_8xRTX3090_octo'] = final_wattages.pop(0)
    cDict['profitDailyPLN_8xRTX3090_octo'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_8xRTX3090_octo')) - (cDict.get('power_8xRTX3090_octo') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_8xRTX3090_octo'] = int(cDict.get('rigPricePLN_8xRTX3090_octo')/(cDict.get('profitDailyPLN_8xRTX3090_octo')))
    if cDict['roi_8xRTX3090_octo'] < 0:
        cDict['roi_8xRTX3090_octo'] = "Never :("
        
    cDict['rigPricePLN_48xRX6700'] = final_prices.pop(0)
    cDict['hashrate_48xRX6700'] = final_hashrates.pop(0)
    cDict['power_48xRX6700'] = final_wattages.pop(0)
    cDict['profitDailyPLN_48xRX6700'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_48xRX6700')) - (cDict.get('power_48xRX6700') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_48xRX6700'] = int(cDict.get('rigPricePLN_48xRX6700')/(cDict.get('profitDailyPLN_48xRX6700')))
    if cDict['roi_48xRX6700'] < 0:
        cDict['roi_48xRX6700'] = "Never :("
        
    cDict['rigPricePLN_200xRX6700'] = final_prices.pop(0)
    cDict['hashrate_200xRX6700'] = final_hashrates.pop(0)
    cDict['power_200xRX6700'] = final_wattages.pop(0)
    cDict['profitDailyPLN_200xRX6700'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_200xRX6700')) - (cDict.get('power_200xRX6700') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_200xRX6700'] = int(cDict.get('rigPricePLN_200xRX6700')/(cDict.get('profitDailyPLN_200xRX6700')))
    if cDict['roi_200xRX6700'] < 0:
        cDict['roi_200xRX6700'] = "Never :("
        
    cDict['rigPricePLN_540xRTX3070'] = final_prices.pop(0)
    cDict['hashrate_540xRTX3070'] = final_hashrates.pop(0)
    cDict['power_540xRTX3070'] = final_wattages.pop(0)
    cDict['profitDailyPLN_540xRTX3070'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_540xRTX3070')) - (cDict.get('power_540xRTX3070') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_540xRTX3070'] = int(cDict.get('rigPricePLN_540xRTX3070')/(cDict.get('profitDailyPLN_540xRTX3070')))
    if cDict['roi_540xRTX3070'] < 0:
        cDict['roi_540xRTX3070'] = "Never :("
        
    cDict['rigPricePLN_obm_10xRTX3070'] = final_prices.pop(0)
    cDict['hashrate_obm_10xRTX3070'] = final_hashrates.pop(0)
    cDict['power_obm_10xRTX3070'] = final_wattages.pop(0)
    cDict['profitDailyPLN_obm_10xRTX3070'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_obm_10xRTX3070')) - (cDict.get('power_obm_10xRTX3070') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_obm_10xRTX3070'] = int(cDict.get('rigPricePLN_obm_10xRTX3070')/(cDict.get('profitDailyPLN_obm_10xRTX3070')))
    if cDict['roi_obm_10xRTX3070'] < 0:
        cDict['roi_obm_10xRTX3070'] = "Never :("
        
    cDict['rigPricePLN_6xRTX3070'] = final_prices.pop(0)
    cDict['hashrate_6xRTX3070'] = final_hashrates.pop(0)
    cDict['power_6xRTX3070'] = final_wattages.pop(0)
    cDict['profitDailyPLN_6xRTX3070'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_6xRTX3070')) - (cDict.get('power_6xRTX3070') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['roi_6xRTX3070'] = int(cDict.get('rigPricePLN_6xRTX3070')/(cDict.get('profitDailyPLN_6xRTX3070')))
    if cDict['roi_6xRTX3070'] < 0:
        cDict['roi_6xRTX3070'] = "Never :("
    
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