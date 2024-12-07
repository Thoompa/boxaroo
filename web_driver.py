from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def get_web_driver(headless:bool = False):
    # Use headless option to run Chrome in the background without GUI
    chrome_options = Options()
    if (headless):
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920, 1080")
    return webdriver.Chrome(options=chrome_options)