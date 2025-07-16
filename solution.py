from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

driver_wait_time = 5
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
def main():

    driver = setup_driver()

    driver.get("https://meteo.hr/naslovnica_aktpod.php?tab=aktpod")
    wait = WebDriverWait(driver, driver_wait_time)
    #wait until whole page is loaded
    try:
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    except:
        print("PAGE NOT LOADED SUCESSFULLY")

    tables = driver.find_elements(By.XPATH, "//table")

    print(f"Found {len(tables)} tables")

    for table in tables:
        #not all tables have <thead> element
        try:
            thead = table.find_element(By.XPATH, "thead")
            header_rows = thead.find_elements(By.XPATH, "tr")
            for row in header_rows:
                headers = [cell.text.strip() for cell in row.find_elements(By.XPATH, "th")
                           if cell.text.strip() != '']
                if headers:
                    print("Headers:", headers)
        except NoSuchElementException:
            print("No <thead> in this table.")

        tbody = table.find_element(By.XPATH, "tbody")
        rows = tbody.find_elements(By.XPATH, "tr")

        for row in rows:
            cells = row.find_elements(By.XPATH, "./td")
            cells_text = [cell.text.strip() for cell in cells if cell.text.strip() != '']
            if cells_text:
                print(cells_text)

        print("\n")

    time.sleep(10)
    driver.quit()
    return

if __name__ == "__main__":
    main()