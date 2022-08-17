import requests
import json
import sqlite3
import os
import time

from datetime import datetime
from bs4 import BeautifulSoup

	
	
def getProfitDaily(coin = 'ethereum', hashrate=328, power=650, electricityPrice=0.1):
	hashrate = hashrate*1000000 # h/s	
	response = requests.get('https://www.coincalculators.io/api?name='+str(coin)+'&hashrate='+str(hashrate)+'&power='+str(power)+'&powercost='+str(electricityPrice), timeout=1)
	profitDaily = json.loads(response.text)['profitInDayUSD']
	print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] API for "+coin+" done! Value: "+str(profitDaily))
	return profitDaily
	

	
def getPriceFromShop(link, name = "default_name"):
	price_int = 1000000
	try:
		r = requests.get(link, timeout = 3)
		soup = BeautifulSoup(r.text, "html.parser")
		price = soup.find('em', {'class': 'main-price'})
		price_int = int(''.join(price.text.split())[:-5].upper())
		print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] BS for "+name+" done!")
		
		return price_int
	except:
		print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Can't get price for "+name+", using default")
		return price_int
 


def createDirIfNotExist(path):

	if not os.path.exists(path):
		print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Creating cache directory")
		os.makedirs(path)
 
 
		
def createPriceCache(link, rigModel, tableName):
	timestamp = 0
	final_price = 999999
	
	db_path = "db/cachePriceFromShop.db"
	
	path = 'db'
	createDirIfNotExist(path)
	
	if os.path.exists(db_path):
		conn = sqlite3.connect(db_path)
		c = conn.cursor()
		c.execute("""CREATE TABLE IF NOT EXISTS """+tableName+""" (
			timestamp TEXT,
			price TEXT
			)""")
		c.execute("""SELECT timestamp, price FROM """+tableName+""" ORDER BY timestamp DESC LIMIT 1""")
		for row in c.fetchall():
			timestamp = int(row[0])
			final_price = int(row[1])
			
	timeNow = int(time.time()) 
	if timestamp + 60 < timeNow:
		final_price = getPriceFromShop(link, rigModel)
		conn = sqlite3.connect(db_path)
		c = conn.cursor()
		c.execute("""CREATE TABLE IF NOT EXISTS """+tableName+""" (
			timestamp TEXT,
			price TEXT
			)""")
		c.execute("""INSERT INTO """+tableName+""" VALUES(
			?, ?)""", (timeNow, final_price))
		c.execute("""Delete from """+tableName+""" where timestamp <> (Select max (timestamp) from """+tableName+""")""")
		conn.commit()
		c.close()
		conn.close()
		print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Updating cache for "+str(rigModel))
	else:
		print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] Using cache for "+str(rigModel))

	return int(final_price)
		
		
	
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
	cDict['rigPricePLN_6xRX570_4gb_used'] = createPriceCache(link_6xRX570_4gb_used, cDict['rigName_6xRX570_4gb_used'], "_6xRX570_4gb_used")
	cDict['hashrate_6xRX570_4gb_used'] = 170 # Mh/s
	cDict['power_6xRX570_4gb_used'] = 800
	cDict['profitDailyPLN_6xRX570_4gb_used'] = round((profitPerMHsDaily_ETC * PLNperUSD * cDict.get('hashrate_6xRX570_4gb_used')) - (cDict.get('power_6xRX570_4gb_used') *24 / 1000 * cDict.get('electricityPricePLN')), 2)
	cDict['roi_6xRX570_4gb_used'] = int(cDict.get('rigPricePLN_6xRX570_4gb_used')/(cDict.get('profitDailyPLN_6xRX570_4gb_used')))
	if cDict['roi_6xRX570_4gb_used'] < 0:
		cDict['roi_6xRX570_4gb_used'] = "Never :("

	cDict['rigName_8xRX6600'] = "8x RX6600XT"
	link_8xRX6600 = "https://shop.zet-tech.eu/pl/p/8x-RX-6600XT-Koparka-kryptowalut-NOWOSC/118"
	cDict['rigPricePLN_8xRX6600'] = createPriceCache(link_8xRX6600, cDict['rigName_8xRX6600'], "_8xRX6600")
	cDict['hashrate_8xRX6600'] = 250 # Mh/s
	cDict['power_8xRX6600'] = 580
	cDict['profitDailyPLN_8xRX6600'] = round((profitPerMHsDaily_ETH * PLNperUSD * cDict.get('hashrate_8xRX6600')) - (cDict.get('power_8xRX6600') * 24 / 1000 * cDict.get('electricityPricePLN')), 2)
	cDict['roi_8xRX6600'] = int(cDict.get('rigPricePLN_8xRX6600')/(cDict.get('profitDailyPLN_8xRX6600')))
	if cDict['roi_8xRX6600'] < 0:
		cDict['roi_8xRX6600'] = "Never :("	
		
	
	print(cDict)
	