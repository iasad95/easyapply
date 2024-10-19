import random
import time
import traceback
from itertools import product

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from human_behavior import (
    human_between_jobs_delay,
    human_disinterested_glance,
    human_glance,
    human_job_interest_level,
    human_long_break_seconds,
    human_max_pages_per_search,
    human_occasional_long_pause,
    human_page_load_delay,
    human_pause,
    human_reading_delay,
    human_session_break_min_seconds,
    human_should_take_long_break,
)
from linkedin_easy_apply.config import ELEMENT_WAIT_TIMEOUT


class LinkedinSessionMixin:
    def warm_up_session(self):
        print("Warming up session (browsing feed)...")
        try:
            self.browser.get("https://www.linkedin.com/feed/")
            human_page_load_delay()
            human_reading_delay(length_chars=1500)
            for _ in range(random.randint(2, 5)):
                self._maybe_idle_move()
                try:
                    vw = self.browser.execute_script("return window.innerWidth;") or 1200
                    vh = self.browser.execute_script("return window.innerHeight;") or 800
                    self.browser.execute_cdp_cmd(
                        "Input.dispatchMouseEvent",
                        {
                            "type": "mouseWheel",
                            "x": random.randint(int(vw * 0.3), int(vw * 0.7)),
                            "y": random.randint(int(vh * 0.3), int(vh * 0.7)),
                            "deltaX": 0,
                            "deltaY": random.randint(200, 600),
                        },
                    )
                except Exception:
                    self.browser.execute_script(f"window.scrollBy(0, {random.randint(200, 600)});")
                human_reading_delay(length_chars=random.randint(500, 2000))
            if random.random() < 0.4:
                try:
                    nav_items = self.browser.find_elements(By.CSS_SELECTOR, 'a[href*="/notifications"]')
                    if nav_items:
                        self._human_click(nav_items[0])
                        human_page_load_delay()
                        human_reading_delay(length_chars=800)
                except Exception:
                    pass
            if random.random() < 0.25:
                try:
                    msg_items = self.browser.find_elements(By.CSS_SELECTOR, 'a[href*="/messaging"]')
                    if msg_items:
                        self._human_click(msg_items[0])
                        human_page_load_delay()
                        human_reading_delay(length_chars=500)
                except Exception:
                    pass
            time.sleep(random.uniform(10, 35))
            print("Warm-up complete.")
        except Exception as e:
            print(f"Warm-up browsing encountered an issue (non-fatal): {e}")

    def _navigate_to_jobs_via_navbar(self):
        try:
            jobs_links = self.browser.find_elements(By.CSS_SELECTOR, 'nav a[href*="/jobs"], #global-nav a[href*="/jobs"], a[href*="/jobs/?"]')
            if not jobs_links:
                jobs_links = self.browser.find_elements(By.XPATH, '//a[contains(@href, "/jobs")]')
            clicked = False
            for link in jobs_links:
                href = link.get_attribute("href") or ""
                if "/jobs/" in href and "/jobs/view/" not in href and ("/jobs/search/" not in href):
                    self._human_click(link)
                    clicked = True
                    break
            if not clicked:
                self.browser.get("https://www.linkedin.com/jobs/")
        except Exception:
            self.browser.get("https://www.linkedin.com/jobs/")
        human_page_load_delay()
        self._maybe_idle_move()
        human_glance()

    def _browse_jobs_only(self):
        try:
            job_results = WebDriverWait(self.browser, ELEMENT_WAIT_TIMEOUT).until(
                expected_conditions.presence_of_element_located((By.CLASS_NAME, "jobs-search-results-list"))
            )
            list_containers = self.browser.find_elements(By.CSS_SELECTOR, ".scaffold-layout__list-container")
            list_container = list_containers[0] if list_containers else self.browser
            job_list = self._find_elements_with_fallback(
                [(By.CLASS_NAME, "jobs-search-results__list-item"), (By.CSS_SELECTOR, "li[data-occludable-job-id]")],
                from_element=list_container,
            )
            if not job_list:
                return
            num_to_browse = random.randint(2, min(5, len(job_list)))
            indices = random.sample(range(len(job_list)), num_to_browse)
            indices.sort()
            for idx in indices:
                self.scroll_slow(job_results, delta=random.randint(100, 250))
                list_containers = self.browser.find_elements(By.CSS_SELECTOR, ".scaffold-layout__list-container")
                list_container = list_containers[0] if list_containers else self.browser
                refreshed = self._find_elements_with_fallback(
                    [(By.CLASS_NAME, "jobs-search-results__list-item"), (By.CSS_SELECTOR, "li[data-occludable-job-id]")],
                    from_element=list_container,
                )
                if idx >= len(refreshed):
                    continue
                job_tile = refreshed[idx]
                try:
                    job_el = None
                    for (by, selector) in [(By.CLASS_NAME, "job-card-list__title"), (By.CSS_SELECTOR, "a.job-card-container__link")]:
                        try:
                            job_el = job_tile.find_element(by, selector)
                            break
                        except NoSuchElementException:
                            continue
                    if job_el:
                        self._human_click(job_el)
                    else:
                        continue
                except Exception:
                    continue
                self._maybe_idle_move()
                try:
                    desc_area = self.browser.find_element(By.CLASS_NAME, "jobs-search__job-details--container")
                    human_pause(short=False)
                    self.scroll_slow(desc_area, end=random.randint(400, 1200))
                    human_reading_delay(length_chars=random.randint(200, 1000))
                except Exception:
                    human_disinterested_glance()
                self.jobs_viewed_this_session += 1
                human_between_jobs_delay()
        except Exception:
            pass

    def login(self):
        try:
            self.browser.get("https://www.linkedin.com/login")
            human_page_load_delay()
            wait = WebDriverWait(self.browser, 20)
            current_url = (self.browser.current_url or "").lower()
            if "/feed" in current_url or "/jobs" in current_url:
                print("Already logged in. Skipping login form.")
                return
            if "/checkpoint/" in current_url or "challenge" in current_url:
                raise Exception("LinkedIn verification required before login fields appear. Complete challenge in browser and rerun.")
            username_el = self._find_element_with_fallback(
                [
                    (By.ID, "username"),
                    (By.NAME, "session_key"),
                    (By.CSS_SELECTOR, "input[autocomplete='username']"),
                    (By.CSS_SELECTOR, "input[name*='email']"),
                ]
            )
            self._human_type(username_el, self.email)
            human_pause(short=False)
            password_el = self._find_element_with_fallback(
                [
                    (By.ID, "password"),
                    (By.NAME, "session_password"),
                    (By.CSS_SELECTOR, "input[autocomplete='current-password']"),
                    (By.CSS_SELECTOR, "input[type='password']"),
                ]
            )
            self._human_type(password_el, self.password, allow_typo=False)
            human_pause(short=False)
            submit_btn = wait.until(
                expected_conditions.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[type='submit'], .btn__primary--large, button[data-litms-control-urn*='login-submit']")
                )
            )
            self._human_click(submit_btn)
            human_page_load_delay()
        except TimeoutException as e:
            raise Exception("Could not load login page or find login fields. Check your internet and that LinkedIn is reachable.") from e
        except Exception as e:
            raise Exception(f"Login failed: {e}") from e

    def handle_verification(self):
        current_url = self.browser.current_url
        if "/checkpoint/" in current_url or "challenge" in current_url:
            input("Complete the verification in the browser, then press Enter here to continue.")
            time.sleep(random.uniform(2.0, 5.0))

    def start_applying(self):
        searches = list(product(self.positions, self.locations))
        random.shuffle(searches)
        pages_done = 0
        next_page_ready_at = time.time()
        for (position, location) in searches:
            if self.applications_this_session >= self.max_applications_session:
                print(f"Session limit reached ({self.max_applications_session} applications). Done for this session.")
                break
            location_url = "&location=" + location
            job_page_number = -1
            max_pages = human_max_pages_per_search()
            print(f"Starting the search for {position} in {location} (up to {max_pages} pages).")
            self._navigate_to_jobs_via_navbar()
            try:
                while True:
                    if job_page_number + 1 >= max_pages:
                        print(f"  Page limit ({max_pages}) reached for this search.")
                        break
                    if self.applications_this_session >= self.max_applications_session:
                        print(f"Session limit reached ({self.max_applications_session} applications).")
                        break
                    pages_done += 1
                    job_page_number += 1
                    print("Going to job page " + str(job_page_number))
                    self.next_job_page(position, location_url, job_page_number)
                    self._maybe_idle_move()
                    human_glance()
                    human_page_load_delay()
                    if random.random() < 0.15 and self.applications_this_session > 0:
                        print("  Just browsing this page (not applying)...")
                        self._browse_jobs_only()
                    else:
                        print("Starting the application process for this page...")
                        self.apply_jobs(location)
                        print("Applying to jobs on this page has been completed!")
                    min_wait = human_session_break_min_seconds()
                    next_page_ready_at = time.time() + min_wait
                    time_left = next_page_ready_at - time.time()
                    if time_left > 0:
                        print("Waiting " + str(round(time_left)) + " seconds before next page.")
                        time.sleep(time_left)
                    if human_should_take_long_break(pages_done):
                        long_wait = human_long_break_seconds()
                        print("Pausing for " + str(round(long_wait / 60, 1)) + " minutes.")
                        time.sleep(long_wait)
                        next_page_ready_at = time.time()
            except Exception:
                traceback.print_exc()
            time_left = next_page_ready_at - time.time()
            if time_left > 0:
                time.sleep(time_left)
            if human_should_take_long_break(pages_done):
                time.sleep(human_long_break_seconds())
        viewed = max(1, self.jobs_viewed_this_session)
        rate = 100 * self.applications_this_session / viewed
        print(
            f"\nSession complete: {self.applications_this_session} applications submitted, "
            f"{self.jobs_viewed_this_session} jobs viewed (apply rate: {self.applications_this_session}/{viewed} = {rate:.0f}%)."
        )

    def apply_jobs(self, location):
        no_jobs_text = ""
        try:
            no_jobs_element = self.browser.find_element(By.CLASS_NAME, "jobs-search-no-results-banner")
            no_jobs_text = no_jobs_element.text
        except Exception:
            pass
        if "No matching jobs found" in no_jobs_text:
            raise Exception("No more jobs on this page")
        if "unfortunately, things aren" in self.browser.page_source.lower():
            raise Exception("No more jobs on this page")
        try:
            job_results = WebDriverWait(self.browser, ELEMENT_WAIT_TIMEOUT).until(
                expected_conditions.presence_of_element_located((By.CLASS_NAME, "jobs-search-results-list"))
            )
            self.scroll_slow(job_results)
            self.scroll_slow(job_results, step=300, reverse=True)
            list_container = self._find_element_with_fallback(
                [(By.CSS_SELECTOR, ".scaffold-layout__list-container"), (By.CLASS_NAME, "scaffold-layout__list-container")]
            )
            job_list = self._find_elements_with_fallback(
                [
                    (By.CSS_SELECTOR, "li.jobs-search-results__list-item"),
                    (By.CLASS_NAME, "jobs-search-results__list-item"),
                    (By.CSS_SELECTOR, "li[data-occludable-job-id]"),
                ],
                from_element=list_container,
            )
            if len(job_list) == 0:
                raise Exception("No job class elements found in page")
        except (NoSuchElementException, TimeoutException):
            raise Exception("No more jobs on this page")
        if len(job_list) == 0:
            raise Exception("No more jobs on this page")
        for index in range(len(job_list)):
            if self.applications_this_session >= self.max_applications_session:
                print(f"Session limit reached ({self.max_applications_session} applications). Moving on.")
                return
            if index > 0:
                self.scroll_slow(job_results, delta=random.randint(150, 220))
            list_containers = self.browser.find_elements(By.CSS_SELECTOR, ".scaffold-layout__list-container")
            list_container = list_containers[0] if list_containers else self.browser
            job_list_refreshed = self._find_elements_with_fallback(
                [(By.CLASS_NAME, "jobs-search-results__list-item"), (By.CSS_SELECTOR, "li[data-occludable-job-id]")],
                from_element=list_container,
            )
            if index >= len(job_list_refreshed):
                continue
            job_tile = job_list_refreshed[index]
            (job_title, company, job_location, link, poster, apply_method) = self.extract_job_information_from_tile(job_tile)
            print(f"Job Details: {job_title}; {company}; {job_location}; {link}; {poster}; {apply_method}")
            if link:
                self.seen_jobs.append(link)
            if self.is_blacklisted(job_title, company, poster, link):
                print(f"Blacklisted {job_title} at {company}, skipping...")
                self.scroll_slow(job_results, delta=200)
                self.record_skipped_job(job_title, company, job_location, link, "", "Title Filtering")
                continue
            interest = human_job_interest_level()
            if interest == "skip":
                print(f"  Scanning past: {job_title}")
                self.jobs_viewed_this_session += 1
                continue
            try:
                job_el = None
                for (by, selector) in [
                    (By.CLASS_NAME, "job-card-list__title"),
                    (By.CSS_SELECTOR, "a.job-card-container__link"),
                    (By.CSS_SELECTOR, '[data-job-id] a[href*="/jobs/view/"]'),
                ]:
                    try:
                        job_el = job_tile.find_element(by, selector)
                        break
                    except NoSuchElementException:
                        continue
                if job_el:
                    self._human_click(job_el)
                else:
                    raise NoSuchElementException("Could not find job title element to click")
            except Exception:
                traceback.print_exc()
                print("Could not click on the job!")
                continue
            self.jobs_viewed_this_session += 1
            if interest == "glance":
                print(f"  Quick look (not applying): {job_title}")
                human_disinterested_glance()
                self._maybe_idle_move()
                continue
            human_occasional_long_pause()
            human_between_jobs_delay()
            self._maybe_idle_move()
            try:
                if not self.apply_to_job(interest):
                    print("Already applied to this job!")
                    continue
            except Exception:
                self.record_failed_application(company, job_location, job_title, link, location)
                print("Failed to fetch details whether previously applied or not!")
                continue
            self.applications_this_session += 1
            self.record_successful_application(company, job_location, job_title, link, location)
            print(f"  Session progress: {self.applications_this_session}/{self.max_applications_session} applications")

    def record_successful_application(self, company, job_location, job_title, link, location):
        try:
            self.write_to_file(company, job_title, link, job_location, location)
        except Exception:
            print("Could not write the job to the file! No special characters in the job title/company is allowed!")
            traceback.print_exc()

    def record_failed_application(self, company, job_location, job_title, link, location):
        print("Failed to apply to job! Please submit a bug report with this link: " + link)
        print("Writing to the failed csv file...")
        try:
            self.write_to_file(company, job_title, link, job_location, location, file_name="failed")
        except Exception:
            pass

    def extract_job_information_from_tile(self, job_tile):
        (job_title, company, poster, job_location, apply_method, link) = ("", "", "", "", "", "")
        title_selectors = [
            (By.CLASS_NAME, "job-card-list__title"),
            (By.CSS_SELECTOR, '[data-job-id] a[href*="/jobs/view/"]'),
            (By.CSS_SELECTOR, "a.job-card-container__link"),
        ]
        for (by, selector) in title_selectors:
            try:
                el = job_tile.find_element(by, selector)
                job_title = el.text.strip()
                href = el.get_attribute("href")
                if href:
                    link = href.split("?")[0]
                if job_title and link:
                    break
            except NoSuchElementException:
                continue
        company_selectors = [
            (By.CLASS_NAME, "job-card-container__primary-description"),
            (By.CLASS_NAME, "job-card-container__company-name"),
            (By.CSS_SELECTOR, ".job-card-container__company-name"),
        ]
        for (by, selector) in company_selectors:
            try:
                company = job_tile.find_element(by, selector).text.strip()
                if company:
                    break
            except NoSuchElementException:
                continue
        try:
            hiring_line = job_tile.find_element(By.XPATH, './/span[contains(., " is hiring for this")]')
            hiring_line_text = hiring_line.text
            name_terminating_index = hiring_line_text.find(" is hiring for this")
            if name_terminating_index != -1:
                poster = hiring_line_text[:name_terminating_index]
        except NoSuchElementException:
            pass
        try:
            loc_el = job_tile.find_element(By.CLASS_NAME, "job-card-container__metadata-item")
            job_location = loc_el.text.strip()
        except NoSuchElementException:
            pass
        try:
            apply_el = job_tile.find_element(By.CLASS_NAME, "job-card-container__apply-method")
            apply_method = apply_el.text.strip()
        except NoSuchElementException:
            pass
        return (job_title, company, job_location, link, poster, apply_method)

    def is_blacklisted(self, job_title, company, poster, link):
        title_lower = job_title.lower()
        for word in self.title_blacklist:
            if word and word.lower() in title_lower:
                return True
        if company.lower() in [word.lower() for word in self.company_blacklist]:
            return True
        if poster.lower() in [word.lower() for word in self.poster_blacklist]:
            return True
        if link in self.seen_jobs:
            return True
        return False
