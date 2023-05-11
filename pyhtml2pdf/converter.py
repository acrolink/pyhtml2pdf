import sys
import json
import base64

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import staleness_of
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.core.utils import ChromeType

from .compressor import __compress


def convert(
    source: str,
    target: str,
    timeout: int = 2,
    compress: bool = False,
    power: int = 0,
    install_driver: bool = True,
    print_options: dict = {},
):
    """
    Convert a given html file or website into PDF

    :param str source: source html file or website link
    :param str target: target location to save the PDF
    :param int timeout: timeout in seconds. Default value is set to 2 seconds
    :param bool compress: whether PDF is compressed or not. Default value is False
    :param int power: power of the compression. Default value is 0. This can be 0: default, 1: prepress, 2: printer, 3: ebook, 4: screen
    :param dict print_options: options for the printing of the PDF. This can be any of the params in here:https://vanilla.aslushnikov.com/?Page.printToPDF
    """

    result = __get_pdf_from_html(
        source, timeout, install_driver, print_options)

    if compress:
        __compress(result, target, power)
    else:
        with open(target, "wb") as file:
            file.write(result)


def __send_devtools(driver, cmd, params={}):
    resource = "/session/%s/chromium/send_command_and_get_result" % driver.session_id
    url = driver.command_executor._url + resource
    body = json.dumps({"cmd": cmd, "params": params})
    response = driver.command_executor._request("POST", url, body)

    if not response:
        raise Exception(response.get("value"))

    return response.get("value")


def __get_pdf_from_html(
    path: str, timeout: int, install_driver: bool, print_options: dict
):
    chrome_driver_service = Service(ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install())
    webdriver_options = Options()
    webdriver_prefs = {}
    driver = None

    webdriver_options.binary_location = '/opt/google/chrome'
    webdriver_options.add_argument("--headless")
    webdriver_options.add_argument("--disable-gpu")
    webdriver_options.add_argument("--no-sandbox")
    webdriver_options.add_argument("--disable-dev-shm-usage")
    webdriver_options.add_argument("--single-process")
    webdriver_options.add_argument("--disable-application-cache")
    webdriver_options.add_argument("--disable-infobars")
    webdriver_options.add_argument("--ignore-certificate-errors")
    webdriver_options.add_argument("--enable-logging")
    webdriver_options.add_argument("--log-level=0")
    webdriver_options.add_argument("--homedir=/tmp")
    webdriver_options.add_argument("--disable-setuid-sandbox")
    webdriver_options.add_argument("--no-first-run")
    webdriver_options.add_argument("--remote-debugging-port=9230")
    webdriver_options.experimental_options["prefs"] = webdriver_prefs

    webdriver_prefs["profile.default_content_settings"] = {"images": 2}

    if install_driver:
        driver = webdriver.Chrome(
            ChromeDriverManager().install(), options=webdriver_options
        )
    else:
        driver = webdriver.Chrome(options=webdriver_options)
    driver.maximize_window()
    driver.get(path)
    driver.implicitly_wait(5)

    try:
        WebDriverWait(driver, timeout).until(
            staleness_of(driver.find_element(by=By.TAG_NAME, value="html"))
        )
    except TimeoutException:
        calculated_print_options = {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "preferCSSPageSize": True,
        }
        calculated_print_options.update(print_options)
        result = __send_devtools(
            driver, "Page.printToPDF", calculated_print_options)
        driver.stop_client()
        driver.close()
        driver.quit()
        chrome_driver_service.stop()
        return base64.b64decode(result["data"])
