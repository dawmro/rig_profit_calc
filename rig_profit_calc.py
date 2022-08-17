import requests
import json

from datetime import datetime

	
	
def getProfitDaily(coin = 'ethereum', hashrate=328, power=650, electricityPrice=0.1):
	hashrate = hashrate*1000000 # h/s	
	response = requests.get('https://www.coincalculators.io/api?name='+str(coin)+'&hashrate='+str(hashrate)+'&power='+str(power)+'&powercost='+str(electricityPrice), timeout=1)
	profitDaily = json.loads(response.text)['profitInDayUSD']
	print("["+datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')+" UTC] API for "+coin+" done! Value: "+str(profitDaily))
	return profitDaily



if __name__ == "__main__":

	# defaults
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
	