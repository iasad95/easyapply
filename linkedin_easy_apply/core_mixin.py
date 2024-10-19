import csv
import random
import sys
import time

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select, WebDriverWait

from human_behavior import (
    human_click_delay,
    human_click_offset,
    human_form_section_delay,
    human_glance,
    human_occasional_long_pause,
    human_pause,
    human_scroll_delay,
    human_scroll_step,
    human_typing_delay,
    should_simulate_typo,
)


class LinkedinCoreMixin:
    def _find_element_with_fallback(self, by_values, from_element=None):
        search_root = from_element or self.browser
        last_error = None
        for (by, value) in by_values:
            try:
                return WebDriverWait(search_root, 5).until(
                    expected_conditions.presence_of_element_located((by, value))
                )
            except (NoSuchElementException, TimeoutException) as e:
                last_error = e
                continue
        raise last_error or NoSuchElementException("Element not found with any selector")

    def _find_elements_with_fallback(self, by_values, from_element=None):
        search_root = from_element or self.browser
        for (by, value) in by_values:
            try:
                elements = search_root.find_elements(by, value)
                if elements:
                    return elements
            except Exception:
                continue
        return []

    def _human_click(self, element):
        human_glance()
        human_click_delay()
        (x_off, y_off) = human_click_offset()
        try:
            chain = ActionChains(self.browser)
            chain.move_to_element_with_offset(element, x_off // 2, y_off // 2)
            chain.pause(random.uniform(0.05, 0.2))
            chain.move_by_offset(x_off - x_off // 2, y_off - y_off // 2)
            chain.pause(random.uniform(0.06, 0.28))
            chain.click()
            chain.perform()
        except Exception:
            try:
                chain = ActionChains(self.browser)
                chain.move_to_element(element).move_by_offset(x_off, y_off)
                chain.pause(random.uniform(0.08, 0.3))
                chain.click().perform()
            except Exception:
                try:
                    ActionChains(self.browser).move_to_element(element).pause(random.uniform(0.1, 0.25)).click().perform()
                except Exception:
                    element.click()

    def _human_type(self, element, text, clear_first=True, allow_typo=True):
        if clear_first:
            self._human_clear_field(element)
            human_pause(short=True)
        text = str(text)
        human_glance()
        if len(text) <= 80:
            for char in text:
                if allow_typo and should_simulate_typo() and char.isalnum():
                    wrong = random.choice([c for c in "qwertyuiopasdfghjklzxcvbnm" if c != char.lower()] or [char])
                    element.send_keys(wrong)
                    time.sleep(human_typing_delay())
                    element.send_keys(Keys.BACKSPACE)
                    time.sleep(human_typing_delay())
                element.send_keys(char)
                time.sleep(human_typing_delay())
                if random.random() < 0.04:
                    time.sleep(random.uniform(0.2, 0.6))
        else:
            i = 0
            while i < len(text):
                chunk_size = random.randint(2, 6)
                chunk = text[i : i + chunk_size]
                element.send_keys(chunk)
                i += len(chunk)
                time.sleep(random.uniform(0.04, 0.18))
                if random.random() < 0.06:
                    time.sleep(random.uniform(0.25, 0.9))
                human_occasional_long_pause()

    def _human_clear_field(self, element):
        mod_key = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL
        chain = ActionChains(self.browser)
        chain.click(element)
        chain.pause(random.uniform(0.08, 0.25))
        chain.key_down(mod_key)
        chain.send_keys("a")
        chain.key_up(mod_key)
        chain.pause(random.uniform(0.05, 0.15))
        chain.send_keys(Keys.BACKSPACE)
        chain.pause(random.uniform(0.05, 0.15))
        chain.perform()

    def _idle_mouse_move(self):
        try:
            vw = self.browser.execute_script("return window.innerWidth;") or 1200
            vh = self.browser.execute_script("return window.innerHeight;") or 800
            target_x = random.randint(100, max(101, vw - 100))
            target_y = random.randint(100, max(101, vh - 100))
            steps = random.randint(3, 8)
            (curr_x, curr_y) = (vw // 2, vh // 2)
            for i in range(steps):
                frac = (i + 1) / steps
                jitter_x = random.randint(-12, 12)
                jitter_y = random.randint(-8, 8)
                x = int(curr_x + (target_x - curr_x) * frac + jitter_x)
                y = int(curr_y + (target_y - curr_y) * frac + jitter_y)
                x = max(0, min(x, vw))
                y = max(0, min(y, vh))
                self.browser.execute_cdp_cmd("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
                time.sleep(random.uniform(0.01, 0.06))
        except Exception:
            pass

    def _maybe_idle_move(self):
        if random.random() < 0.3:
            self._idle_mouse_move()

    def enter_text(self, element, text):
        self._human_type(element, text, clear_first=True)

    def select_dropdown(self, element, text):
        human_pause(short=True)
        try:
            self._human_click(element)
            human_pause(short=True)
            options = element.find_elements(By.TAG_NAME, "option")
            for opt in options:
                if (opt.text or "").strip() == (text or "").strip():
                    self._human_click(opt)
                    human_pause(short=True)
                    return
        except (NoSuchElementException, Exception):
            pass
        select = Select(element)
        select.select_by_visible_text(text)
        human_pause(short=True)

    def radio_select_simplified(self, element):
        label = element.find_element(By.TAG_NAME, "label")
        human_pause(short=True)
        self._human_click(label)

    def write_to_file(self, company, job_title, link, location, search_location, file_name="output"):
        to_write = [company, job_title, link, location]
        file_name = file_name + "_" + search_location + ".csv"
        file_path = self.output_file_directory / file_name
        with open(file_path, "a") as f:
            writer = csv.writer(f)
            writer.writerow(to_write)

    def record_gpt_answer(self, answer_type, question_text, gpt_response):
        to_write = [answer_type, question_text, gpt_response]
        file_name = "gpt_answers.csv"
        file_path = self.output_file_directory / file_name
        try:
            with open(file_path, "a") as f:
                writer = csv.writer(f)
                writer.writerow(to_write)
        except Exception:
            print("Could not write the unprepared gpt question to the file! No special characters in the question is allowed: ")
            print(question_text)

    def record_skipped_job(self, job_title: str, company: str, location: str, link: str, description: str, skipped_stage: str):
        file_path = self.output_file_directory / "skipped_jobs.csv"
        to_write = [job_title, company, location, skipped_stage, link, description]
        with open(file_path, "a") as f:
            writer = csv.writer(f)
            writer.writerow(to_write)

    def scroll_slow(self, scrollable_element, start=0, end=3600, step=100, reverse=False, delta=None):
        if delta is not None:
            current_scroll_position = self.browser.execute_script("return arguments[0].scrollTop;", scrollable_element)
            if reverse:
                start = current_scroll_position - delta
                end = current_scroll_position
            else:
                start = current_scroll_position
                end = current_scroll_position + delta
        if reverse:
            (start, end) = (end, start)
            step = -abs(step)
        going_forward = step > 0
        try:
            rect = self.browser.execute_script(
                "var r = arguments[0].getBoundingClientRect();return {x: r.x, y: r.y, w: r.width, h: r.height};",
                scrollable_element,
            )
            el_x = int(rect["x"] + rect["w"] * random.uniform(0.3, 0.7))
            el_y = int(rect["y"] + rect["h"] * random.uniform(0.3, 0.7))
        except Exception:
            el_x = random.randint(400, 800)
            el_y = random.randint(300, 600)
        total_distance = abs(end - start)
        scrolled = 0
        while scrolled < total_distance:
            step_size = human_scroll_step()
            step_size = min(step_size, total_distance - scrolled)
            dy = step_size if going_forward else -step_size
            try:
                jx = el_x + random.randint(-8, 8)
                jy = el_y + random.randint(-5, 5)
                self.browser.execute_cdp_cmd("Input.dispatchMouseEvent", {"type": "mouseWheel", "x": jx, "y": jy, "deltaX": 0, "deltaY": dy})
            except Exception:
                try:
                    current = self.browser.execute_script("return arguments[0].scrollTop;", scrollable_element)
                    self.browser.execute_script("arguments[0].scrollTo(0, arguments[1])", scrollable_element, current + dy)
                except Exception:
                    pass
            scrolled += step_size
            time.sleep(human_scroll_delay())
            if random.random() < 0.14:
                time.sleep(random.uniform(0.35, 1.15))
            if random.random() < 0.08:
                overshoot = random.randint(6, 22) * (-1 if going_forward else 1)
                try:
                    self.browser.execute_cdp_cmd(
                        "Input.dispatchMouseEvent",
                        {"type": "mouseWheel", "x": el_x + random.randint(-5, 5), "y": el_y + random.randint(-3, 3), "deltaX": 0, "deltaY": overshoot},
                    )
                except Exception:
                    pass
                time.sleep(random.uniform(0.1, 0.3))

    def avoid_lock(self):
        if self.disable_lock:
            return
        if random.random() < random.uniform(0.25, 0.55):
            self._idle_mouse_move()

    def get_base_search_url(self, parameters):
        remote_url = ""
        if parameters["remote"]:
            remote_url = "f_CF=f_WRA"
        level = 1
        experience_level = parameters.get("experienceLevel", [])
        experience_url = "f_E="
        for key in experience_level.keys():
            if experience_level[key]:
                experience_url += "%2C" + str(level)
            level += 1
        distance_url = "?distance=" + str(parameters["distance"])
        job_type_codes = {
            "full-time": "F",
            "contract": "C",
            "part-time": "P",
            "temporary": "T",
            "internship": "I",
            "other": "O",
            "volunteer": "V",
        }
        job_types_url = "f_JT="
        job_types = parameters.get("jobTypes", {})
        selected_types = [job_type_codes[k] for k in job_types if job_types.get(k)]
        if selected_types:
            job_types_url += "%2C".join(selected_types)
        date_url = ""
        dates = {"all time": "", "month": "&f_TPR=r2592000", "week": "&f_TPR=r604800", "24 hours": "&f_TPR=r86400"}
        date_table = parameters.get("date", [])
        for key in date_table.keys():
            if date_table[key]:
                date_url = dates[key]
                break
        easy_apply_url = "&f_LF=f_AL"
        extra_search_terms = [distance_url, remote_url, job_types_url, experience_url]
        extra_search_terms_str = "&".join((term for term in extra_search_terms if len(term) > 0)) + easy_apply_url + date_url
        return extra_search_terms_str

    def next_job_page(self, position, location, job_page):
        self.browser.get(f"https://www.linkedin.com/jobs/search/{self.base_search_url}&keywords={position}{location}&start={job_page * 25}")
        self.avoid_lock()
        self._maybe_idle_move()
