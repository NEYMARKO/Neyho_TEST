from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

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

    table = driver.find_element(By.XPATH, '//table[@class="fd-c-table1 table--aktualni-podaci sortable"]')
    rows = table.find_elements(By.TAG_NAME, "tr")
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        cells_text = [cell.text for cell in cells]
        print(cells_text)
    driver.quit()
    return

if __name__ == "__main__":
    main()