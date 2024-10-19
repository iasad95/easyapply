import random
import time
import traceback
from datetime import date

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select, WebDriverWait

from human_behavior import (
    human_deep_reading_delay,
    human_form_section_delay,
    human_glance,
    human_occasional_long_pause,
    human_pause,
    human_reading_delay,
)
from linkedin_easy_apply.config import ELEMENT_WAIT_TIMEOUT


class LinkedinApplicationFormsMixin:
    def extract_job_information_from_opened_job(self):
        (job_title, company, job_location, description) = ("", "", "", "")
        try:
            job_element = WebDriverWait(self.browser, ELEMENT_WAIT_TIMEOUT).until(
                expected_conditions.presence_of_element_located((By.CLASS_NAME, "jobs-search__job-details--container"))
            )
            for sel in ["jobs-unified-top-card__job-title", "jobs-unified-top-card__content--two-pane"]:
                try:
                    job_title = job_element.find_element(By.CLASS_NAME, sel).text.strip()
                    if job_title and len(job_title) < 200:
                        break
                except NoSuchElementException:
                    continue
            for sel in ["jobs-unified-top-card__company-name", "jobs-unified-top-card__subtitle"]:
                try:
                    company = job_element.find_element(By.CLASS_NAME, sel).text.strip()
                    if company:
                        break
                except NoSuchElementException:
                    continue
            try:
                bullets = job_element.find_elements(By.CLASS_NAME, "jobs-unified-top-card__bullet")
                workplace = job_element.find_elements(By.CLASS_NAME, "jobs-unified-top-card__workplace-type")
                loc_parts = [b.text for b in bullets[:1] if b.text] + [w.text for w in workplace[:1] if w.text]
                job_location = " | ".join(loc_parts) if loc_parts else ""
            except (NoSuchElementException, IndexError):
                pass
            for sel in ["jobs-description-content__text", "jobs-description__content"]:
                try:
                    desc_el = job_element.find_element(By.CLASS_NAME, sel)
                    description = desc_el.text
                    break
                except NoSuchElementException:
                    continue
        except (TimeoutException, NoSuchElementException) as e:
            raise Exception(f"Could not extract job information from the opened job! {e}")
        return (job_title, company, job_location, description)

    def formatted_job_information(self, job_title: str, company: str, job_location: str, description: str):
        job_information = (
            f"\n        # Job Description\n        ## Job Information \n        - Position: {job_title}\n        - At: {company}\n"
            f"        - Location: {job_location}\n        \n        ## Description\n        {description}\n        "
        )
        return job_information

    def apply_to_job(self, interest_level="read"):
        easy_apply_button = None
        try:
            easy_apply_button = WebDriverWait(self.browser, 10).until(
                expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, "button.jobs-apply-button, button[aria-label*='Easy Apply']"))
            )
        except (NoSuchElementException, TimeoutException):
            return False
        if easy_apply_button.text == "Continue":
            return False
        try:
            job_description_area = self.browser.find_element(By.CLASS_NAME, "jobs-search__job-details--container")
            self._maybe_idle_move()
            if interest_level == "interested":
                human_pause(short=False)
                self.scroll_slow(job_description_area, end=random.randint(1400, 2000))
                human_deep_reading_delay()
                self._maybe_idle_move()
                self.scroll_slow(job_description_area, end=random.randint(800, 1600), step=400, reverse=True)
                human_reading_delay(length_chars=random.randint(1500, 3000))
                if random.random() < 0.4:
                    self.scroll_slow(job_description_area, end=random.randint(600, 1200))
                    human_pause(short=False)
            else:
                human_pause(short=False)
                self.scroll_slow(job_description_area, end=1600)
                self._maybe_idle_move()
                human_pause(short=True)
                self.scroll_slow(job_description_area, end=1600, step=400, reverse=True)
                human_reading_delay(length_chars=2000)
        except Exception:
            pass
        (job_title, job_company, job_location, job_description) = self.extract_job_information_from_opened_job()
        formatted_description = self.formatted_job_information(job_title, job_company, job_location, job_description)
        self.gpt_answerer.job_description = formatted_description
        if not self.env_config.disable_description_filter and (not self.gpt_answerer.job_description_passes_filters()):
            print(f"Blacklisted description {job_title} at {job_company}. Skipping...")
            self.record_skipped_job(job_title, job_company, job_location, "unknown link", job_description, "Description Filtering")
            raise Exception("Job description blacklisted")
        if self.env_config.skip_apply:
            print("ENV: Skipping apply. The SKIP_APPLY environment variable is set to True.")
            return False
        print("Applying to the job....")
        human_glance()
        human_pause(short=False)
        human_occasional_long_pause()
        self._human_click(easy_apply_button)
        submitted_application = False
        while not submitted_application:
            try:
                self.fill_up()
                submitted_application = self.apply_to_job_form_next_step()
            except Exception:
                traceback.print_exc()
                human_pause(short=True)
                self._human_click(self.browser.find_element(By.CLASS_NAME, "artdeco-modal__dismiss"))
                human_pause(short=False)
                self._human_click(self.browser.find_elements(By.CLASS_NAME, "artdeco-modal__confirm-dialog-btn")[1])
                human_pause(short=False)
                raise Exception("Failed to apply to job!")
        self.apply_to_job_form_close_confirmation_modal()
        return True

    def apply_to_job_form_close_confirmation_modal(self):
        closed_notification = False
        human_pause(short=False)
        try:
            dismiss_btn = self.browser.find_element(By.CLASS_NAME, "artdeco-modal__dismiss")
            self._human_click(dismiss_btn)
            closed_notification = True
        except Exception:
            pass
        try:
            toast_btn = self.browser.find_element(By.CLASS_NAME, "artdeco-toast-item__dismiss")
            self._human_click(toast_btn)
            closed_notification = True
        except Exception:
            pass
        human_pause(short=False)
        if closed_notification is False:
            raise Exception("Could not close the applied confirmation window!")

    def apply_to_job_form_next_step(self):
        submit_application_text = "submit application"
        next_button = self.browser.find_element(By.CLASS_NAME, "artdeco-button--primary")
        button_text = next_button.text.lower()
        if submit_application_text in button_text:
            self.unfollow()
        human_form_section_delay()
        self._human_click(next_button)
        human_pause(short=False)
        error_elements = self.browser.find_elements(By.CLASS_NAME, "artdeco-inline-feedback--error")
        if len(error_elements) > 0:
            raise Exception(f"Failed answering required questions or uploading required files. {str([e.text for e in error_elements])}")
        if submit_application_text in button_text.lower():
            return True
        return False

    def home_address(self, element):
        try:
            groups = element.find_elements(By.CLASS_NAME, "jobs-easy-apply-form-section__grouping")
            if len(groups) > 0:
                for group in groups:
                    lb = group.find_element(By.TAG_NAME, "label").text.lower()
                    input_field = group.find_element(By.TAG_NAME, "input")
                    if "street" in lb:
                        self.enter_text(input_field, self.personal_info["Street address"])
                        human_pause(short=True)
                    elif "city" in lb:
                        self.enter_text(input_field, self.personal_info["City"])
                        human_pause(short=False)
                        input_field.send_keys(Keys.DOWN)
                        human_pause(short=True)
                        input_field.send_keys(Keys.RETURN)
                        human_pause(short=True)
                    elif "zip" in lb or "postal" in lb:
                        self.enter_text(input_field, self.personal_info["Zip"])
                        human_pause(short=True)
                    elif "state" in lb or "province" in lb:
                        self.enter_text(input_field, self.personal_info["State"])
                        human_pause(short=True)
        except Exception:
            pass

    def additional_questions(self):
        frm_el = self.browser.find_elements(By.CLASS_NAME, "jobs-easy-apply-form-section__grouping")
        if len(frm_el) == 0:
            return
        for el in frm_el:
            if self.additional_questions_agree_terms_of_service(el):
                continue
            self.additional_questions_radio_gpt(el)
            self.additional_questions_textbox_gpt(el)
            self.additional_questions_date(el)
            self.additional_questions_drop_down_gpt(el)

    def additional_questions_agree_terms_of_service(self, el) -> bool:
        try:
            question = el.find_element(By.CLASS_NAME, "jobs-easy-apply-form-element")
            clickable_checkbox = question.find_element(By.TAG_NAME, "label")
            question_text = question.text.lower()
            if "terms of service" in question_text or "privacy policy" in question_text or "terms of use" in question_text:
                human_pause(short=True)
                self._human_click(clickable_checkbox)
                return True
        except Exception:
            pass
        return False

    def additional_questions_drop_down_gpt(self, el):
        try:
            question = el.find_element(By.CLASS_NAME, "jobs-easy-apply-form-element")
            question_text = question.find_element(By.TAG_NAME, "label").text.lower()
            dropdown_field = question.find_element(By.TAG_NAME, "select")
            select = Select(dropdown_field)
            options = [options.text for options in select.options]
            if "email" in question_text:
                return
            choice = self.gpt_answerer.answer_question_from_options(question_text, options)
            self.select_dropdown(dropdown_field, choice)
            self.record_gpt_answer("dropdown", question_text, choice)
        except Exception:
            pass

    def additional_questions_date(self, el):
        try:
            date_picker = None
            for cls in ["artdeco-datepicker__input ", "artdeco-datepicker__input", "artdeco-datepicker-input"]:
                try:
                    date_picker = el.find_element(By.CLASS_NAME, cls)
                    break
                except NoSuchElementException:
                    continue
            if not date_picker:
                date_picker = el.find_element(By.CSS_SELECTOR, 'input[type="date"], input[placeholder*="date"], input[placeholder*="Date"]')
            date_str = date.today().strftime("%m/%d/%y")
            self._human_type(date_picker, date_str)
            human_pause(short=False)
            date_picker.send_keys(Keys.RETURN)
            human_pause(short=True)
        except NoSuchElementException:
            pass

    def additional_questions_textbox_gpt(self, el):
        try:
            question = el.find_element(By.CLASS_NAME, "jobs-easy-apply-form-element")
            question_text = question.find_element(By.TAG_NAME, "label").text.lower()
            try:
                txt_field = question.find_element(By.TAG_NAME, "input")
            except Exception:
                try:
                    txt_field = question.find_element(By.TAG_NAME, "textarea")
                except Exception:
                    raise Exception("Could not find textarea or input tag for question")
            text_field_type = (txt_field.get_attribute("type") or "").lower()
            tag_name = (txt_field.tag_name or "").lower()
            if not ("numeric" in text_field_type or "text" in text_field_type or tag_name == "textarea"):
                return
            is_numeric_field = False
            class_attribute = txt_field.get_attribute("id")
            if class_attribute and "numeric" in class_attribute:
                is_numeric_field = True
            if is_numeric_field:
                to_enter = self.gpt_answerer.answer_question_numeric(question_text)
            else:
                to_enter = self.gpt_answerer.answer_question_textual_wide_range(question_text)
            self.record_gpt_answer("numeric" if is_numeric_field else "text", question_text, to_enter)
            self.enter_text(txt_field, to_enter)
            self.textbox_gpt_handle_form_errors(el, question_text, to_enter, txt_field)
        except Exception:
            pass

    def textbox_gpt_handle_form_errors(self, el, question_text: str, answer_text: str, txt_field):
        try:
            error = el.find_element(By.CLASS_NAME, "artdeco-inline-feedback--error")
            error_text = error.text.lower()
        except NoSuchElementException:
            return
        new_answer = self.gpt_answerer.try_fix_answer(question_text, answer_text, error_text)
        self.enter_text(txt_field, new_answer)

    def additional_questions_radio_gpt(self, el):
        try:
            question = el.find_element(By.CLASS_NAME, "jobs-easy-apply-form-element")
            radios = question.find_elements(By.CLASS_NAME, "fb-text-selectable__option")
            if len(radios) == 0:
                radios = question.find_elements(By.CSS_SELECTOR, "label.fb-text-selectable__option")
            if len(radios) == 0:
                radio_inputs = question.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
                radios = []
                for radio_input in radio_inputs:
                    try:
                        label = radio_input.find_element(By.XPATH, "./following-sibling::label | ./parent::label | ..//label")
                        radios.append(label)
                    except NoSuchElementException:
                        pass
            if len(radios) == 0:
                raise Exception("No radio found in element")
            radio_text = el.text.lower()
            radio_options = [text.text.lower() for text in radios]
            answer = self.gpt_answerer.answer_question_from_options(radio_text, radio_options)
            self.record_gpt_answer("radio", radio_text, answer)
            to_select = None
            for radio in radios:
                if answer in radio.text.lower():
                    to_select = radio
                    break
            if to_select is None:
                to_select = radios[-1]
            self.radio_select_simplified(to_select)
        except Exception:
            pass

    def unfollow(self):
        try:
            human_pause(short=True)
            follow_checkbox = self.browser.find_element(By.XPATH, "//label[contains(.,'to stay up to date with their page.')]")
            self._human_click(follow_checkbox)
        except Exception as e:
            print(f"Failed to unfollow company! {e}")

    def is_upload_field(self, element: WebElement) -> bool:
        try:
            element.find_element(By.XPATH, ".//input[@type='file']")
            return True
        except Exception:
            return False

    def try_send_resume(self):
        try:
            file_upload_elements = self.browser.find_elements(By.XPATH, "//input[@type='file']")
            if len(file_upload_elements) == 0:
                raise Exception("No file upload elements found")
            resume_path = str(self.resume_dir.resolve())
            letter_path = str(self.cover_letter_dir.resolve()) if self.cover_letter_dir else ""
            for element in file_upload_elements:
                parent = element.find_element(By.XPATH, "..")
                label_lower = parent.text.lower()
                try:
                    label_or_btn = parent.find_element(By.TAG_NAME, "label")
                    human_pause(short=False)
                    self._human_click(label_or_btn)
                    human_pause(short=True)
                except NoSuchElementException:
                    pass
                human_pause(short=False)
                if "resume" in label_lower:
                    element.send_keys(resume_path)
                elif "cover" in label_lower and letter_path:
                    element.send_keys(letter_path)
                human_pause(short=False)
        except Exception as e:
            print(f"Failed to upload resume or cover letter! {e}")

    def contact_info(self):
        frm_el = self.browser.find_elements(By.CLASS_NAME, "jobs-easy-apply-form-section__grouping")
        if len(frm_el) == 0:
            return
        for el in frm_el:
            text = el.text.lower()
            if "email address" in text:
                continue
            elif "phone number" in text:
                try:
                    country_code_picker = el.find_element(By.XPATH, '//select[contains(@id,"phoneNumber")][contains(@id,"country")]')
                    self.select_dropdown(country_code_picker, self.personal_info["Phone Country Code"])
                except Exception as e:
                    print("Country code " + self.personal_info["Phone Country Code"] + " not found! Make sure it is exact.")
                    print(e)
                try:
                    phone_number_field = el.find_element(By.XPATH, '//input[contains(@id,"phoneNumber")][contains(@id,"nationalNumber")]')
                    self.enter_text(phone_number_field, self.personal_info["Mobile Phone Number"])
                except Exception as e:
                    print("Could not input phone number:")
                    print(e)

    def fill_up(self):
        try:
            easy_apply_content = self._find_element_with_fallback(
                [
                    (By.CLASS_NAME, "jobs-easy-apply-content"),
                    (By.CSS_SELECTOR, "[data-test-modal]"),
                    (By.CSS_SELECTOR, ".jobs-apply-form"),
                    (By.CLASS_NAME, "jobs-apply-form"),
                ]
            )
            pb4 = easy_apply_content.find_elements(By.CLASS_NAME, "pb4")
            if len(pb4) == 0:
                pb4 = easy_apply_content.find_elements(By.CSS_SELECTOR, '[class*="form-section"], [class*="form__form-section"]')
            if len(pb4) == 0:
                pb4 = easy_apply_content.find_elements(By.CSS_SELECTOR, "section, .jobs-easy-apply-form-section__grouping")
            if len(pb4) == 0:
                grouping = easy_apply_content.find_elements(By.CLASS_NAME, "jobs-easy-apply-form-section__grouping")
                if grouping:
                    pb4 = [easy_apply_content]
            for pb in pb4:
                try:
                    human_form_section_delay()
                    self._maybe_idle_move()
                    try:
                        label = pb.find_element(By.TAG_NAME, "h3").text.lower()
                    except NoSuchElementException:
                        label = (pb.get_attribute("aria-label") or pb.text or "")[:100].lower()
                    if "home address" in label:
                        self.home_address(pb)
                        continue
                    if "contact info" in label:
                        self.contact_info()
                        continue
                    if self.is_upload_field(pb):
                        try:
                            self.try_send_resume()
                            continue
                        except Exception:
                            pass
                    try:
                        self.additional_questions()
                    except Exception:
                        pass
                except NoSuchElementException:
                    try:
                        self.additional_questions()
                    except Exception:
                        pass
        except Exception:
            try:
                groupings = self.browser.find_elements(By.CLASS_NAME, "jobs-easy-apply-form-section__grouping")
                if groupings:
                    self.home_address(self.browser)
                    self.contact_info()
                    self.try_send_resume()
                    self.additional_questions()
            except Exception:
                pass
