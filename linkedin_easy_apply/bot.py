from pathlib import Path

from gpt import GPTAnswerer, SimpleAnswerer, has_openai_key
from human_behavior import human_max_applications_per_session
from linkedin_easy_apply.application_forms_mixin import LinkedinApplicationFormsMixin
from linkedin_easy_apply.config import EnvironmentKeys
from linkedin_easy_apply.core_mixin import LinkedinCoreMixin
from linkedin_easy_apply.session_mixin import LinkedinSessionMixin


class LinkedinEasyApply(LinkedinCoreMixin, LinkedinSessionMixin, LinkedinApplicationFormsMixin):
    def __init__(self, parameters, driver):
        self.browser = driver
        self.email = parameters["email"]
        self.password = parameters["password"]
        self.disable_lock = parameters["disableAntiLock"]
        self.company_blacklist = parameters.get("companyBlacklist", []) or []
        self.title_blacklist = parameters.get("titleBlacklist", []) or []
        self.poster_blacklist = parameters.get("posterBlacklist", []) or []
        self.positions = parameters.get("positions", [])
        self.locations = parameters.get("locations", [])
        self.base_search_url = self.get_base_search_url(parameters)
        self.seen_jobs = []
        self.output_file_directory = Path(parameters["outputFileDirectory"])
        self.resume_dir: Path = parameters["uploads"]["resume"]
        self.cover_letter_dir: Path = parameters["uploads"].get("coverLetter")
        self.personal_info = parameters.get("personalInfo", [])
        self.checkboxes = parameters.get("checkboxes", {}) or {}
        self.applications_this_session = 0
        self.max_applications_session = human_max_applications_per_session()
        self.jobs_viewed_this_session = 0
        print(f"Session application limit: {self.max_applications_session}")
        self.env_config = EnvironmentKeys()
        self.env_config.print_config()

        plain_text_resume_path = parameters["uploads"]["plainTextResume"]
        plain_text_personal_data_path = parameters["uploads"]["plainTextPersonalData"]
        plain_text_cover_letter_path = parameters["uploads"].get("plainTextCoverLetter")
        job_filters_path = parameters["uploads"]["jobFilters"]

        with open(plain_text_resume_path, "r") as resume_file:
            plain_text_resume = resume_file.read()
        with open(plain_text_personal_data_path, "r") as personal_file:
            plain_text_personal_data = personal_file.read()
        plain_text_cover_letter = ""
        if plain_text_cover_letter_path and Path(plain_text_cover_letter_path).exists():
            with open(plain_text_cover_letter_path, "r") as cover_file:
                plain_text_cover_letter = cover_file.read()
        with open(job_filters_path, "r") as filters_file:
            job_filters = filters_file.read()

        if has_openai_key():
            self.gpt_answerer = GPTAnswerer(plain_text_resume, plain_text_personal_data, plain_text_cover_letter, job_filters)
            print("Using GPT for application answers.")
        else:
            self.gpt_answerer = SimpleAnswerer(
                plain_text_resume,
                plain_text_personal_data,
                plain_text_cover_letter,
                job_filters,
                self.personal_info,
            )
            print("No OpenAI key - using simple answers from personal_info. Set OPEN_AI_API_KEY for GPT-powered answers.")
