from flask import Flask, render_template, request
from flask_caching import Cache

import requests
import aiohttp
import asyncio
import time
import os
import sqlite3
import json
import ast
import pathlib
import configparser

from bs4 import BeautifulSoup
from datetime import datetime



shop_caching_time = 60 * 30 # 30 minutes
profit_caching_time = 60 * 60 # 60 minutes
usdpln_caching_time = 60 * 60 * 6 # 6 hours


config_path = pathlib.Path(__file__).parent.absolute() / "config.ini"
config = configparser.ConfigParser()
config.read(config_path)

HASHRATE_NO_API_KEY = config["SECRETS"]["HASHRATE_NO_API_KEY"]


app = Flask(__name__)

cache = Cache(app, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'db/cache-dir', 
    'CACHE_DEFAULT_TIMEOUT': 86400, # 1 day
    'CACHE_THRESHOLD': 86400 # 1 day
})
cache.init_app(app)


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
  
  
@cache.cached(timeout=86400, key_prefix='gpu_estimates')
def getGPUEstimates(electricityPrice=0.0):
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Starting API for GPU Estimates...")
    response = requests.get("https://api.hashrate.no/v1/gpuEstimates?apiKey="+str(HASHRATE_NO_API_KEY)+"&powerCost="+str(electricityPrice), timeout=2)
    print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" API for GPU Estimates done!")
    return response.text
    

        
'''  
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
'''    
 

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
            
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] getPrice for "+name+" done: "+str(price_int))
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

                if "Mining GPU ETC =" in text:
                    text = text.split("Mining GPU ETC =")[1].strip().split("MH")[0]
                    hashrate = int(text)
                        
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] getHashrate for "+name+" done: "+str(hashrate))
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
                    
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] getWattage for "+name+" done: "+str(wattage))
        return wattage
        
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't get wattage for "+name+", using default")
        return wattage



def createDirIfNotExist(path):

    if not os.path.exists(path):
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Creating cache directory")
        os.makedirs(path)
         
 

def readAndUpdateShopCache(names, urls, tableNames, vendors):
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
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Got data from shop cache") 

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
            
            print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Updating shop cache for "+str(names[i]))
            i=i+1
        
    
    return final_prices, final_hashrates, final_wattages
 
 
   
def doCalculationsForElectricityPrice(electricityPricePLN_gr):



    # defaults
    PLNperUSD = 4.5
    '''
    profitPerMHsDaily_ETC = 0.00279
    profitPerMHsDaily_ZIL = 0.00070
    profitPerMHsDaily_KAS = 0.00062
    profitPerMHsDaily_RVN = 0.05123
    '''


    try:
        PLNperUSD = useUsdPlnCache()
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't fetch USDPLN, using: " + str(PLNperUSD))

    '''
    try:
        # ethereumclassic
        profitPerMHsDaily_ETC = useProfitCache('162', 1, 0, 0) 
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't fetch profits for ETC, using: " + str(profitPerMHsDaily_ETC))
        
    try:
        # kaspa
        profitPerMHsDaily_KAS = useProfitCache('352', 1, 0, 0) 
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't fetch profits for KAS, using: " + str(profitPerMHsDaily_KAS))
        
    try:
        profitPerMHsDaily_RVN = useProfitCache('ravencoin', 1, 0, 0)
    except:
        print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't fetch profits for RVN, using: " + str(profitPerMHsDaily_RVN))
    '''    
        
    cDict = {}
    cDict['electricityPricePLN_gr'] = float(electricityPricePLN_gr)
    cDict['electricityPricePLN'] = cDict.get('electricityPricePLN_gr') / 100
    cDict['electricityPrice'] = cDict.get('electricityPricePLN')/PLNperUSD
    
    try:
        GPUEstimates = getGPUEstimates()
    except:
        GPUEstimates = None
    #print(GPUEstimates)    
    

    
    names = []
    urls = []
    
    
    cDict['rigName_6xRX570_4gb_used'] = "ZET 6x RX570 4GB Used"
    names.append(cDict['rigName_6xRX570_4gb_used'])
    link_6xRX570_4gb_used = "https://shop.zet-tech.eu/pl/p/6x-RX-570-4GB-Koparka-kryptowalut/155"
    urls.append(link_6xRX570_4gb_used)
    cDict['link_6xRX570_4gb_used'] = link_6xRX570_4gb_used
    cDict['kas_hashrate_6xRX570_4gb_used'] = 600
    
    cDict['rigName_12xRX6600_octo'] = "ZET OCTOMINER 12x RX6600XT"
    names.append(cDict['rigName_12xRX6600_octo'])
    link_12xRX6600_octo = "https://shop.zet-tech.eu/pl/p/OCTOMINER-12x-RX6600/146"
    urls.append(link_12xRX6600_octo)
    cDict['link_12xRX6600_octo'] = link_12xRX6600_octo
    cDict['kas_hashrate_12xRX6600_octo'] = 1440
    
    cDict['rigName_obm_10xRTX3070'] = "OBM 10x RTX3070"
    names.append(cDict['rigName_obm_10xRTX3070'])
    link_obm_10xRTX3070 = "https://onlybestminers.com/pl_pl/produkt/gpu-obm10xrtx3070/"
    urls.append(link_obm_10xRTX3070)
    cDict['link_obm_10xRTX3070'] = link_obm_10xRTX3070
    cDict['kas_hashrate_obm_10xRTX3070'] = 3200

    
   
    
    tableNames = []
    vendors = []
    for name in names:
        tableNames.append(str("_"+name.replace(" ", "").replace("-", "_")))
        vendors.append(name[0:3])
          

    
    final_prices, final_hashrates, final_wattages = readAndUpdateShopCache(names, urls, tableNames, vendors)

    cDict['rigPricePLN_6xRX570_4gb_used'] = final_prices.pop(0)
    cDict['hashrate_6xRX570_4gb_used'] = final_hashrates.pop(0)
    cDict['power_6xRX570_4gb_used'] = int(final_wattages.pop(0))
    cDict['best_coin_6xRX570_4gb_used'] = str(json.loads(GPUEstimates)['570']['profit24']['coin'])
    cDict['number_of_cards_6xRX570_4gb_used'] = 6
    cDict['best_profitDailyPLN_6xRX570_4gb_used'] = round( 
        json.loads(GPUEstimates)['570']['profit24']['profitUSD24'] * PLNperUSD * cDict.get('number_of_cards_6xRX570_4gb_used')
        - (cDict.get('power_6xRX570_4gb_used') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['best_roi_6xRX570_4gb_used'] = int(cDict.get('rigPricePLN_6xRX570_4gb_used')/(cDict.get('best_profitDailyPLN_6xRX570_4gb_used')))
    if cDict['best_roi_6xRX570_4gb_used'] < 0:
        cDict['best_roi_6xRX570_4gb_used'] = "Never :("
    
        
    cDict['rigPricePLN_12xRX6600_octo'] = final_prices.pop(0)
    cDict['hashrate_12xRX6600_octo'] = final_hashrates.pop(0)
    cDict['power_12xRX6600_octo'] = int(final_wattages.pop(0))
    cDict['best_coin_12xRX6600_octo'] = str(json.loads(GPUEstimates)['6600']['profit24']['coin'])
    cDict['number_of_cards_12xRX6600_octo'] = 12
    cDict['best_profitDailyPLN_12xRX6600_octo'] = round( 
        json.loads(GPUEstimates)['6600']['profit24']['profitUSD24'] * PLNperUSD * cDict.get('number_of_cards_12xRX6600_octo')
        - (cDict.get('power_12xRX6600_octo') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['best_roi_12xRX6600_octo'] = int(cDict.get('rigPricePLN_12xRX6600_octo')/(cDict.get('best_profitDailyPLN_12xRX6600_octo')))
    if cDict['best_roi_12xRX6600_octo'] < 0:
        cDict['best_roi_12xRX6600_octo'] = "Never :("
    
        
    cDict['rigPricePLN_obm_10xRTX3070'] = final_prices.pop(0)
    cDict['hashrate_obm_10xRTX3070'] = final_hashrates.pop(0)
    cDict['power_obm_10xRTX3070'] = int(final_wattages.pop(0))
    cDict['best_coin_obm_10xRTX3070'] = str(json.loads(GPUEstimates)['3070']['profit24']['coin'])
    cDict['number_of_cards_obm_10xRTX3070'] = 10
    cDict['best_profitDailyPLN_obm_10xRTX3070'] = round( 
        json.loads(GPUEstimates)['3070']['profit24']['profitUSD24'] * PLNperUSD * cDict.get('number_of_cards_obm_10xRTX3070')
        - (cDict.get('power_obm_10xRTX3070') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
    cDict['best_roi_obm_10xRTX3070'] = int(cDict.get('rigPricePLN_obm_10xRTX3070')/(cDict.get('best_profitDailyPLN_obm_10xRTX3070')))
    if cDict['best_roi_obm_10xRTX3070'] < 0:
        cDict['best_roi_obm_10xRTX3070'] = "Never :("

    
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