import json
import sys
import io
import os
import eywa
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from enum import Enum
import time
import re

if os.name == 'nt':
    os.system('chcp 65001') #set utf-8 in windows terminal


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

driver_wait_time = 5

class Type(Enum):
    INT = 0
    FLOAT = 1
    STRING = 2

def setup_driver(headless = False):
    chrome_options = Options()

    if headless:
        chrome_options.add_argument('--headless')
        # eywa.info("Running in headless mode")
    # else:
        # eywa.info("Running with visible browser window")

        # Common options for both modes
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')

    # Additional options for better visibility when not headless
    if not headless:
        chrome_options.add_argument('--start-maximized')

    # Auto-install ChromeDriver
    # eywa.info("Setting up ChromeDriver...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver

def parse_data_to_json(cells_text_array):
    data = {}
    topics = ["wind_direction", "wind_velocity", "air_temperature",
              "relative_moisture", "air_pressure", "air_tendency",
              "weather_state", "time"]
    types = [Type.STRING, Type.STRING, Type.FLOAT, Type.FLOAT, Type.INT, Type.FLOAT, Type.FLOAT, Type.STRING]

    for i in range(1, len(cells_text_array) - 1):
        #clean input
        cleaned = re.sub(r'[^a-zA-Z0-9.\-\s]','',cells_text_array[i]).strip()
        if (not cleaned or cleaned == '-'):
            continue
        elif (types[i] == Type.FLOAT):
            print(f"{cleaned} will be float")
            cleaned = float(cleaned.replace('\u2212', '-'))
        elif (types[i] == Type.INT):
            cleaned = int(cleaned)
        data[topics[i - 1]] = cleaned
    data[topics[-1]] = time.time()
    return data

async def station_exists(name):
    result = await eywa.graphql("""
    query($name: String!)
    {
        searchStation
        {
            name
        }
    }
    """)
    # print(f"RESULT: {result}")
    # print(result.get("data", {}).get("searchStation", {}))
    return {"name": name} in result.get("data", {}).get("searchStation", {})
async def get_id(name):
    result = await eywa.graphql("""
    query($name: String!)
    {
        searchStation(name: {_eq:$name})
        {
            euuid
            name
        }
    }
    """, {"name": name})
    print(result)
    if (result.get('data', {}).get('searchStation', {})):
        print(f"EUUID: {result.get('data', {}).get('searchStation', {})[0].get('euuid', {})}, \
        NAME: {result.get('data', {}).get('searchStation', {})[0].get('name', {})}")

async def import_measures(data):
    result = await eywa.graphql("""
    
    mutation($data:[MeasurmentInput])
    {
        syncMeasurmentList(data:$data)
        {
            wind_direction
        }
    }
    
    """, {"data": data})
    print(result)
async def import_station(name):

    print("GOT TO INSERTION")
    return await eywa.graphql("""
    mutation($station: StationInput)
    {
        syncStation(data:$station)
        {
            name
        }
    }

    """, {"station": {"name": name}})

async def link_measurements():
    return await eywa.graphql("""
    mutation(stations:[StationInput])
    {
        syncStationList(data:$measurements)
        {
            name
        }
    }
    """, {"measurements" : {""}})
async def main():
    eywa.open_pipe()

    data_array = []
    # stations_dict = {}

    driver = setup_driver()

    driver.get("https://meteo.hr/naslovnica_aktpod.php?tab=aktpod")
    wait = WebDriverWait(driver, driver_wait_time)

    #wait until whole page is loaded
    try:
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    except:
        print("PAGE NOT LOADED SUCESSFULLY")

    table = driver.find_element(By.XPATH, '//table[@class="fd-c-table1 table--aktualni-podaci sortable"]')
    table_body = table.find_element(By.XPATH, "./tbody")
    rows = table_body.find_elements(By.TAG_NAME, "tr")
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        cells_text = [cell.text for cell in cells]
        # print(cells_text)
        # await get_id(cells_text[0])
        if await station_exists(cells_text[0]) == False:
            await import_station(cells_text[0])
            print(f"STATION {cells_text[0]} SHOULD GET ADDED")
        else:
            print(f"SKIP ADD FOR {cells_text[0]}")
        data_array.append(parse_data_to_json(cells_text))
        # print("ROW DONE")
    print(data_array)
    # print(json.dumps(data_dict, ensure_ascii=False))
    # await import_measures(data_array)
    driver.quit()
    eywa.exit()
    return

if __name__ == "__main__":
    asyncio.run(main())