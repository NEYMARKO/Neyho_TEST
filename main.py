import sys
import json
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

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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
            cells_text_array[i] = float(cleaned.replace('\u2212', '-'))
        elif (types[i] == Type.INT):
            cells_text_array[i] = int(cleaned)
        data[topics[i - 1]] = cleaned
    data[topics[-1]] = time.time()
    return data

async def station_exists(name):
    result = eywa.graphql("""
    {
        searchStation(name: {_eq: $name})
        {
            name
        }
    }
    """, name)
    await result
    if (result["data"]["station"]["name"]):
        return True
    return False
async def import_measures(data):
    return await eywa.graphql("""
    {
        mutation($measurements:[MeasurementInput])
        {
            syncMeasurementsList(measure:$measures)
            {
                wind_direction
                wind_velocity
                air_temperature
                relative_moisture
                air_pressure
                air_tendency",
                weather_state
                time
            }
        }
    }
    """, data)
async def import_station(name):
    return await eywa.graphql("""
    {
        mutation($station: StationInput)
        {
            syncStation(station:$station)
            {
                name
            }
        }
    }
    """, name)
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
        if (await station_exists(cells_text[0]) == False):
            import_station(cells_text[0])
        data_array.append(parse_data_to_json(cells_text))
    print(data_array)
    # print(json.dumps(data_dict, ensure_ascii=False))
    await import_measures(json.dumps(data_array, ensure_ascii=False))
    driver.quit()
    eywa.exit()
    return

if __name__ == "__main__":
    asyncio.run(main())