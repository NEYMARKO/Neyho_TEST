import json

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from enum import Enum
import time
import re
import datetime

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
    return {cells_text_array[0] : data}
def main():

    data_dict = {}
    temp_dict = {}
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
        data_dict.update(parse_data_to_json(cells_text))
    print(json.dumps(data_dict, ensure_ascii=False))
    driver.quit()
    return

if __name__ == "__main__":
    main()