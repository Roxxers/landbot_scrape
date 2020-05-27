import json
import os
import time

from typing import List, Dict, Any

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.webelement import FirefoxWebElement as Element

selectors = {
    "button": "a.hu-input-menu_button",
    "text_box": ".hu-textarea",
    "bot_message": ".hu-message-text",
    "all_messages": ".hu-message-bubble"
}


def check_if_duplicates(list_of_elems: List[Any]) -> bool:
    ''' Check if given list contains any duplicates '''
    if len(list_of_elems) == len(set(list_of_elems)):
        return False
    else:
        return True


class AnyEc:
    """ Use with WebDriverWait to combine expected_conditions
        in an OR.
    """
    def __init__(self, *args):
        self.ecs = args

    def __call__(self, driver):
        for function in self.ecs:
            try:
                if function(driver):
                    return True
            except:
                pass
        return False


# After every choice, and on second choice selection
# Check all previous blocks
# if blocks have repeated, stop choosing different choices and default to first for next choice

Blocks = Dict[int, List[str]]
Output = Dict[str, Blocks]


class Scraper:
    def __init__(self, page_url: str):
        self.id = page_url.split("/")[-2]
        self.url = page_url

        self.timeout = 15 # Secs
        self.output = {"blocks": {}, "choices": {}}
        self.no_of_input_sections = 0
        self.loop_number = 0
        self.required_loops = 1

    def get(self):
        """being web scraping landbot.io page"""
        self.browser = webdriver.Firefox()
        self.loop_number += 1
        self.prev_messages = set(
        ) # This is used to store all previous bot messages, without duplicates
        self.browser.get(url)
        self.loop_through_page()
        all_messages = self.browser.find_elements_by_css_selector(
            selectors["all_messages"]
        )
        messages = self.process_messages(all_messages)
        self.output["blocks"] = self.define_blocks(messages)
        self.write_to_disk()
        self.browser.close()

        # If the amount of times we have looped eq the amount we need to loop, then end
        # If not, recursively run the function again
        if self.loop_number != self.required_loops:
            self.get()

    def write_to_disk(self):
        try:
            os.mkdir(f"./{self.id}")
        except FileExistsError:
            pass # Folder already exists

        with open(f"./{self.id}/{self.loop_number}.json", "w") as fp:
            fp.write(json.dumps(self.output, ensure_ascii=False))

    def decide_recursive_loop_amount(self, choices: List[str]):
        no_choices = len(choices)
        if no_choices > self.required_loops:
            self.required_loops = no_choices

    def loop_through_page(self) -> None:
        """ loops through waiting for an input and then doing it.
        Will exit when times out.
        """
        while True:
            page = self.browser.find_element_by_tag_name("body").text
            try:
                choices = self.wait_for_input() # Resolve any output needed
                # Add choices to output to show
                self.output["choices"][self.no_of_input_sections] = choices
                self.no_of_input_sections += 1
                # Check if choices is more than current loop amount value
                self.decide_recursive_loop_amount(choices)
                time.sleep(2)
            except TimeoutException:
                if page == self.browser.find_element_by_tag_name("body").text:
                    # Page has not changed and should be timed out
                    break

    def wait_for_input(self) -> List[str]:
        """
        This function waits for a input or choice to become available. Once it is,
        click or input text, and return what input it was to parent function"""
        wait = WebDriverWait(self.browser, self.timeout)
        wait.until(
            AnyEc(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, selectors["button"])
                ),
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, selectors["text_box"])
                )
            )
        )
        try:
            text_box = self.browser.find_element_by_css_selector(
                selectors["text_box"]
            )
            text_box.send_keys("{INPUT_TEXT}")
            text_box.send_keys(Keys.ENTER)
            return ["TEXT_BOX"]
        except NoSuchElementException:
            buttons = self.browser.find_elements_by_css_selector(
                selectors["button"]
            )
            first_button = self.decide_button_to_click(buttons)
            choices = [
                x.find_element_by_tag_name("span").text for x in buttons
            ]
            time.sleep(
                0.2
            ) # IF not sometimes there is some errors when the choices are deleted
            first_button.click()
            return choices

    def decide_button_to_click(self, buttons: List[Element]) -> Element:
        """
        Decides what button to click when presented with one.
        Checks if loop has occurred.
        """
        button_amount = len(buttons)

        bot_messages = self.browser.find_elements_by_css_selector(
            ".hu-background-color_bot-message-background"
        )

        prev_mesg = self.process_messages(bot_messages)

        if check_if_duplicates(prev_mesg):
            # If there is duplicates
            # Stop previous duplicates from triggering this
            # Removes most classes from previous bot messages
            # But keeps "hu-message-bubble" to for the end of the script
            self.browser.execute_script(
                'list = document.getElementsByClassName("hu-message-bubble hu-position-relative hu-background-color_bot-message-background");for (var i = 0; i < list.length; i++){list[i].className="hu-message-bubble"}'
            )
            # Return first button to stop text loop
            return buttons[0]

        if button_amount == 1 or button_amount < self.loop_number:
            return buttons[0]
        else:
            return buttons[self.loop_number - 1]

    def define_blocks(self, messages: List[str]) -> Blocks:
        user_mesg = self.browser.find_elements_by_css_selector(
            ".hu-message-text.hu-color_user-message-text"
        )
        user_dialog = [x.text for x in user_mesg]
        blocks = {}
        start_of_block = 0
        block_number = 0
        for ind, line in enumerate(messages):
            if line in user_dialog:
                blocks[block_number] = messages[start_of_block:ind]
                user_dialog.pop(user_dialog.index(line))
                start_of_block = ind + 1
                block_number += 1
                if not user_dialog:
                    blocks[block_number] = messages[start_of_block:]
        return blocks

    def process_messages(self, messages: List[Element]) -> List[str]:
        all_processed_dialog = []
        for message in messages:
            all_processed_dialog.append(self.parse_message_bubble(message))
        return all_processed_dialog

    def parse_message_bubble(self, message: Element) -> str:
        """"""
        try:
            text = message.find_element_by_css_selector(".hu-message-text")
            return text.text
        except NoSuchElementException:
            try:
                image_element = message.find_element_by_tag_name("img")
                image_src = image_element.get_attribute('src')
                caption = message.find_elements_by_tag_name("p")
                if caption:
                    return "{}: {}".format(caption[0].text, image_src)
                return image_src
            except NoSuchElementException:
                try:
                    youtube = message.find_element_by_tag_name("iframe")
                    return youtube.get_attribute("src")
                except NoSuchElementException:
                    print("Could not find text, image, or youtube video.")
                    return ""


urls = [
    'https://landbot.io/u/H-62930-ZP46ZQSEK44QRYMQ/index.html',
    'https://landbot.io/u/H-352102-P3SL3H01U8XL08OV/index.html',
    'https://landbot.io/u/H-352137-OPZAVJDI1A0HTMJ1/index.html',
    'https://landbot.io/u/H-351906-X5HRGP1JXFC4WEFG/index.html',
]

for url in urls:
    scraper = Scraper(url)
    scraper.get()
