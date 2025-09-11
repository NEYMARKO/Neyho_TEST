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
import datetime
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

def format_sending_data(cells_text_array):
    data = {}
    topics = ["wind_direction", "wind_velocity", "air_temperature",
              "relative_moisture", "air_pressure", "air_tendency",
              "weather_state", "time"]
    types = [Type.STRING, Type.STRING, Type.FLOAT, Type.FLOAT, Type.INT, Type.FLOAT, Type.FLOAT, Type.STRING]

    data["station"] = {"name": cells_text_array[0]}
    for i in range(1, len(cells_text_array)):
        #clean input
        cleaned = re.sub(r'[^a-zA-Z0-9.čžšČŽŠ\-\s]','',cells_text_array[i]).strip()
        if (not cleaned or cleaned == '-'):
            continue
        elif (types[i] == Type.FLOAT):
            # print(f"{cleaned} will be float")
            cleaned = float(cleaned.replace('\u2212', '-'))
        elif (types[i] == Type.INT):
            cleaned = int(cleaned)
        data[topics[i - 1]] = cleaned
    data[topics[-1]] = datetime.datetime.fromtimestamp(time.time(), datetime.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    # print(f"DATA: {data}")
    return data

async def import_measures(data):
    return await eywa.graphql("""
    mutation($measurements:[MeasurementInput])
    {
        stackMeasurementList(data:$measurements)
        {
            euuid
        }
    }
    
    """, {"measurements": data})

async def fetch_all_measurements():
    return await eywa.graphql("""
    {
        searchMeasurement
        {
            euuid
        }
    }
    """)

async def delete_all_measurements(measurements_list):
    for element in measurements_list:
        euuid = element.get("euuid", {})
        await eywa.graphql("""
        mutation($euuid:UUID)
        {
            deleteMeasurement(euuid:$euuid)
        }
        """, {"euuid": euuid})
    print("ALL VALUES DELETED")

async def fetch_all_stations():
    return await eywa.graphql("""
    {
        searchStation
        {
            euuid
        }
    }
    """)

async def delete_all_stations(stations_list):
    for element in stations_list:
        euuid = element.get("euuid", {})
        await eywa.graphql("""
        mutation($euuid: UUID)
        {
            deleteStation(euuid:$euuid)
        }
        """, {"euuid": euuid})

async def check_if_model_deployed():
    result = await eywa.graphql("""
    query
    {
      searchDatasetVersion(_where:{euuid: {_eq: "da7acea5-fc8a-4682-98cb-16d936e0c9ee"}})
      {
        euuid
        name
        dataset
        {
          name
        }
        deployed
      }
    }
    """)

    temp = result.get("data", {}).get("searchDatasetVersion", {})
    if not temp:
        return False
    elif temp[0].get("deployed", {}) == True:
        print(temp[0].get("deployed", {}) == True)
        return True
    print(temp[0].get("deployed", {}) == True)

async def deploy_model():
    dataset = None
    with open("Neyho_DHMZ_Test_1_2_1.json") as file:
        dataset = file.read()
    # print(dataset)
    return await eywa.graphql("""
    mutation($dataset: Transit)
    {
        importDataset(dataset:$dataset)
        {
            euuid
        }
    }
    """, {"dataset": dataset})

async def main():
    eywa.open_pipe()

    link = "https://meteo.hr/naslovnica_aktpod.php?tab=aktpod"
    data_array = []

    driver = setup_driver()

    driver.get(link)
    wait = WebDriverWait(driver, driver_wait_time)

    #wait until whole page is loaded
    try:
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    except:
        print("PAGE NOT LOADED SUCCESSFULLY")
        return

    if await check_if_model_deployed() == False:
        print("Deploying model")
        await deploy_model()
    else:
        print("Model already deployed")

    table = driver.find_element(By.XPATH, '//table[@class="fd-c-table1 table--aktualni-podaci sortable"]')
    table_body = table.find_element(By.XPATH, "./tbody")
    rows = table_body.find_elements(By.TAG_NAME, "tr")

    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        cells_text = [driver.execute_script("""
                    let clone = arguments[0].cloneNode(true);
                    const tagsToRemove = ['SUP'];
                    tagsToRemove.forEach(tag => {
                        clone.querySelectorAll(tag).forEach(e => e.remove());
                    });
                    return clone.textContent.trim();
                """, cell) for cell in cells]
        data_array.append(format_sending_data(cells_text))
    await import_measures(data_array)
    print("IMPORTED MEASUREMENTS TO DB")

    # #DELETING ALL STATIONS
    # all_station_euuids = await fetch_all_stations()
    # await delete_all_stations(all_station_euuids.get("data", {}).get("searchStation", {}))
    #
    # #DELETING ALL MEASUREMENTS
    # all_measurement_euuids = await fetch_all_measurements()
    # await delete_all_measurements(all_measurement_euuids.get("data", {}).get("searchMeasurement", {}))

    driver.quit()
    eywa.exit()
    return

if __name__ == "__main__":
    asyncio.run(main())