# rig_profit_calc
This program scrapes data from auction listings and calculates the return of investment (ROI) of mining rigs. It uses Python Flask to display the data in a web browser.


## Features:
- Web scraping with Beautiful Soup
- Async calls with aiohttp and asyncio
- SQLite database for cache
- API calls to external services for profitability data of popular graphic cards

![alt text](https://github.com/dawmro/rig_profit_calc/blob/main/images/console.PNG?raw=true)

## Setup:
1. Create new virtual env:
``` sh
python -m venv env
```
2. Activate your virtual env:
``` sh
env/Scripts/activate
```
3. Install packages from included requirements.txt:
``` sh
pip install -r .\requirements.txt
```

4. Get your API key from [hashrate.no](https://hashrate.no/account) and place it into config.ini file


## Usage:
``` sh
python -m flask --app rig_profit_calc run
```

Open your web browser and go to http://localhost:5000
Input Your electricity price into the box and press "GO". You will see a table with the following columns:

- Model: The name of the mining rig and also link to the auction
- Price: The price of the mining rig in PLN
- Hashrate: The hashrate of the mining rig in MH/s
- Power: The power consumption of the mining rig in W
- Profit: The daily profit of the mining rig in PLN
- ROI: The return of investment of the mining rig in days



![alt text](https://github.com/dawmro/rig_profit_calc/blob/main/images/view2.PNG?raw=true)

