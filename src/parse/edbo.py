from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from os import PathLike

from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from tqdm import tqdm

from src import settings
from src.settings import DRIVER_PATH

__all__ = ["EdboData", "EdboParser", "ParserException"]


class ParserException(Exception):
    pass


@dataclass
class EdboData:
    first_select_text: str
    second_select_text: str
    document_series: str
    # document_number: str
    number_of_digits: int
    first_name: str
    last_name: str
    middle_name: str
    birth_date: date


class EdboParser:
    URL = "https://info.edbo.gov.ua/edu-documents/"
    DUMB_URL = "https://info.edbo.gov.ua"

    def __init__(
        self,
        data: EdboData,
        document_number_range: tuple[int, int],
        session_id: str,
        captcha: str,
    ):
        self.data = data
        self.doc_num_range = document_number_range
        self.sess_id = session_id
        self.captcha = captcha

        self.driver = None

    def _init_driver(self):
        option = webdriver.ChromeOptions()
        chrome_prefs = {}
        option.experimental_options["prefs"] = chrome_prefs
        chrome_prefs["profile.default_content_settings"] = {"images": 2}
        chrome_prefs["profile.managed_default_content_settings"] = {"images": 2}

        self.driver = webdriver.Chrome(DRIVER_PATH, chrome_options=option)

    def set_session_cookies(self):
        driver = self.driver
        driver.get(self.DUMB_URL)
        driver.add_cookie({"name": "PHPSESSID", "value": self.sess_id})

    def fill_select(self, select_id: str, option_text: str):
        driver: webdriver.Chrome = self.driver

        wait = WebDriverWait(driver, 2, poll_frequency=0.2)

        dropdown = driver.find_element(by="id", value=f"{select_id}-container")
        dropdown.click()

        options_container = wait.until(
            expected_conditions.presence_of_element_located(
                (By.XPATH, f"//*[contains(@id, '{select_id}-results')]")
            )
        )
        option = options_container.find_element(
            By.XPATH, f"//li[contains(text(), '{option_text}')]"
        )

        option.click()

        # dropdown.click()  # Sometimes is needed to click

    def fill_input(self, input_id: str, text: str, *, clear=False):
        input_el = self.driver.find_element(by="id", value=input_id)

        if clear:
            input_el.clear()

        input_el.send_keys(text)

    def init_page(self):
        self.set_session_cookies()
        driver = self.driver
        driver.get(self.URL)

        self.fill_select("select2-educationType", self.data.first_select_text)
        self.fill_select("select2-documentType", self.data.second_select_text)

        self.fill_input("documentSeries", self.data.document_series)

        self.fill_input("lastName", self.data.last_name)
        self.fill_input("firstName", self.data.first_name)
        self.fill_input("middleName", self.data.middle_name)

        self.fill_input("birthDay", self.data.birth_date.strftime("%d%m%Y"))

        self.fill_input("captcha", self.captcha)

    def run(self):
        self._init_driver()
        try:
            self.init_page()
            self.guess_multiple()
        finally:
            self.driver.quit()

    def save_screenshot(self, filename: PathLike) -> bool:
        try:
            return self.driver.save_screenshot(filename)
        except Exception:
            return False

    def guess_multiple(self, max_errors: int = 10):
        consecutive_errors: int = 0
        doc_numbers = range(*self.doc_num_range)
        if settings.SHOW_PROGRESS:
            doc_numbers = tqdm(doc_numbers)

        # with self.driver:
        for i in doc_numbers:
            try:
                if self.guess(i):
                    logging.info(f"Congratulations!!! Document number is {i}")
                    self.save_screenshot(f"{i}.png")
                    break
            except Exception as e:
                consecutive_errors += 1
                logging.error(f"For document number {i} unexpected exception occured")
                if consecutive_errors > max_errors:
                    raise ParserException(
                        f"There were 10 consecutive errors. Parsing will be stopped on the document number {i}"
                    ) from e
            else:
                consecutive_errors = 0
        else:
            logging.critical("Done processing. No matching were found")

    def guess(self, document_number: int) -> bool:
        driver = self.driver
        doc_number = f"{document_number:0>{self.data.number_of_digits}}"

        self.fill_input("documentNumber", doc_number, clear=True)

        submit = driver.find_element(by=By.CSS_SELECTOR, value="#EduRequest>button")

        submit.click()

        try:
            no_diploma_popup = WebDriverWait(driver, 5).until(
                expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, "#document-info>.error")
                )
            )
            logging.debug(f"No document found with number {doc_number}")
            close_popup = driver.find_element(
                By.CSS_SELECTOR, value=".ui-dialog-buttonset>button"
            )
            close_popup.click()
            return False
        except TimeoutException:
            return True
