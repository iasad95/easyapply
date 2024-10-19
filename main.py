import os
import random
import yaml
import argparse
from linkedin_easy_apply import LinkedinEasyApply
from validate_email import validate_email
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
_STEALTH_SCRIPTS = "\nObject.defineProperty(navigator, 'webdriver', { get: () => undefined });\nif (navigator.plugins.length === 0) {\n    Object.defineProperty(navigator, 'plugins', {\n        get: () => {\n            return {\n                0: { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },\n                1: { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },\n                2: { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },\n                length: 3,\n                item: function(i) { return this[i] || null; },\n                namedItem: function(n) { for (var i=0; i<this.length; i++) { if (this[i] && this[i].name===n) return this[i]; } return null; },\n                refresh: function() {},\n            };\n        }\n    });\n}\nObject.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });\ntry {\n    const origQuery = window.navigator.permissions.query.bind(window.navigator.permissions);\n    window.navigator.permissions.query = (params) =>\n        params.name === 'notifications'\n            ? Promise.resolve({ state: Notification.permission })\n            : origQuery(params);\n} catch(e) {}\nif (!window.chrome) window.chrome = {};\nif (!window.chrome.runtime) window.chrome.runtime = { id: undefined };\n(function(){\n    const _origToString = Function.prototype.toString;\n    const _nativeCode = 'function () { [native code] }';\n    const _patched = new Set();\n    for (const prop of ['webdriver', 'plugins', 'languages']) {\n        try {\n            const desc = Object.getOwnPropertyDescriptor(navigator, prop);\n            if (desc && desc.get) _patched.add(desc.get);\n        } catch(e) {}\n    }\n    Function.prototype.toString = function() {\n        if (_patched.has(this)) return _nativeCode;\n        return _origToString.call(this);\n    };\n    _patched.add(Function.prototype.toString);\n})();\n"

def init_browser():
    import undetected_chromedriver as uc
    options = uc.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    w = random.randint(1380, 1500)
    h = random.randint(840, 960)
    options.add_argument(f'--window-size={w},{h}')
    options.add_argument('--lang=en-US')
    profile_dir = os.getenv('CHROME_PROFILE_DIR') or os.path.join(str(Path.home()), '.easyapply_chrome_profile')
    driver_path = os.getenv('CHROMEDRIVER_PATH')
    try:
        driver = uc.Chrome(options=options, user_data_dir=profile_dir, driver_executable_path=driver_path or None)
        try:
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': _STEALTH_SCRIPTS})
        except Exception as e:
            print(f'Warning: Could not inject stealth scripts via CDP: {e}')
        print(f'Chrome started with persistent profile at: {profile_dir}')
        return driver
    except Exception as e:
        print(f'\nChrome failed to start. Error: {e}')
        print('Common fixes:')
        print('  1. Install Google Chrome: https://www.google.com/chrome/')
        print('  2. pip install undetected-chromedriver')
        print('  3. Set CHROMEDRIVER_PATH in .env if you have a chromedriver binary.')
        raise

def find_file(name_containing: str, with_extension: str, at_path: Path) -> Path:
    for file in at_path.iterdir():
        if name_containing.lower() in file.name.lower() and file.suffix.lower() == with_extension.lower():
            return file

def _find_job_filters_file(app_data_folder: Path) -> Path:
    candidates = [app_data_folder / 'filters.md', app_data_folder / 'job_filters.md', app_data_folder / 'job-filters.md']
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]

def _pick_file(app_data_folder: Path, names) -> Path:
    candidates = [app_data_folder / name for name in names]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]

def validate_data_folder(app_data_folder):
    app_data_folder = Path(app_data_folder)
    config_file = app_data_folder / 'config.yaml'
    plain_text_resume_file = _pick_file(app_data_folder, ['resume.md', 'plain_text_resume.md'])
    plain_text_cover_letter_file = _pick_file(app_data_folder, ['cover_letter.md', 'plain_text_cover_letter.md'])
    personal_data_file = _pick_file(app_data_folder, ['profile.md', 'personal_data.md'])
    job_filters_file = _find_job_filters_file(app_data_folder)
    resume_file = find_file('resume', '.pdf', app_data_folder)
    cover_letter_file = find_file('cover', '.pdf', app_data_folder)
    missing = []
    if not config_file.exists():
        missing.append('config.yaml')
    if not resume_file:
        missing.append("resume.pdf (filename must include 'resume')")
    if not plain_text_resume_file.exists():
        missing.append('resume.md or plain_text_resume.md')
    if not personal_data_file.exists():
        missing.append('profile.md or personal_data.md')
    if not job_filters_file.exists():
        missing.append('filters.md or job_filters.md or job-filters.md')
    if not cover_letter_file:
        print('Warning: cover_letter.pdf missing. Continuing.')
    if not plain_text_cover_letter_file.exists():
        print('Warning: cover_letter.md/plain_text_cover_letter.md missing. Continuing.')
    if missing:
        missing_list = '\n\t- ' + '\n\t- '.join(missing)
        raise Exception('Missing required files:' + missing_list + '\n\nSee Templates.')
    output_folder = app_data_folder / 'output'
    if not output_folder.exists():
        output_folder.mkdir()
    return (config_file, resume_file, cover_letter_file, plain_text_resume_file, plain_text_cover_letter_file, personal_data_file, job_filters_file, output_folder)

def file_paths_to_dict(resume_file: Path, cover_letter_file: Path, plain_text_resume_file: Path, plain_text_cover_letter_file: Path, personal_data_file: Path, job_filters_file: Path) -> dict:
    parameters = {'resume': resume_file, 'plainTextResume': plain_text_resume_file, 'plainTextPersonalData': personal_data_file, 'jobFilters': job_filters_file}
    if cover_letter_file:
        parameters['coverLetter'] = cover_letter_file
    if plain_text_cover_letter_file.exists():
        parameters['plainTextCoverLetter'] = plain_text_cover_letter_file
    return parameters

def validate_yaml(config_yaml_path: Path):
    with open(config_yaml_path, 'r') as stream:
        try:
            parameters = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise exc
    mandatory_params = ['email', 'password', 'disableAntiLock', 'remote', 'experienceLevel', 'jobTypes', 'date', 'positions', 'locations', 'distance', 'personalInfo']
    parameters['email'] = os.getenv('LINKEDIN_EMAIL') or parameters.get('email', '')
    parameters['password'] = os.getenv('LINKEDIN_PASSWORD') or parameters.get('password', '')
    for mandatory_param in mandatory_params:
        if mandatory_param not in parameters and mandatory_param not in ('email', 'password'):
            raise Exception(mandatory_param + ' is not inside the yml file!')
    if not parameters['email'] or not parameters['password']:
        raise Exception('LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in .env, or email/password in config.yaml')
    assert validate_email(parameters['email'])
    assert len(str(parameters['password'])) > 0
    assert isinstance(parameters['disableAntiLock'], bool)
    assert isinstance(parameters['remote'], bool)
    assert len(parameters['experienceLevel']) > 0
    experience_level = parameters.get('experienceLevel', [])
    at_least_one_experience = False
    for key in experience_level.keys():
        if experience_level[key]:
            at_least_one_experience = True
    assert at_least_one_experience
    assert len(parameters['jobTypes']) > 0
    job_types = parameters.get('jobTypes', [])
    at_least_one_job_type = False
    for key in job_types.keys():
        if job_types[key]:
            at_least_one_job_type = True
    assert at_least_one_job_type
    assert len(parameters['date']) > 0
    date = parameters.get('date', [])
    at_least_one_date = False
    for key in date.keys():
        if date[key]:
            at_least_one_date = True
    assert at_least_one_date
    approved_distances = {0, 5, 10, 25, 50, 100}
    assert parameters['distance'] in approved_distances
    assert len(parameters['positions']) > 0
    assert len(parameters['locations']) > 0
    assert len(parameters['personalInfo'])
    personal_info = parameters.get('personalInfo', [])
    for info in personal_info:
        assert personal_info[info] != ''
    return parameters

def main(data_folder_path: Path):
    print(f'Using data folder path: {data_folder_path}')
    (config_file, resume_file, cover_letter_file, plain_text_resume_file, plain_text_cover_letter_file, personal_data_file, job_filters_file, output_folder) = validate_data_folder(data_folder_path)
    parameters = validate_yaml(config_file)
    parameters['uploads'] = file_paths_to_dict(resume_file, cover_letter_file, plain_text_resume_file, plain_text_cover_letter_file, personal_data_file, job_filters_file)
    parameters['outputFileDirectory'] = output_folder
    try:
        print('Starting Chrome...')
        browser = init_browser()
        bot = LinkedinEasyApply(parameters, browser)
        print('Opening LinkedIn login page...')
        bot.login()
        bot.handle_verification()
        bot.warm_up_session()
        bot.start_applying()
    except Exception as e:
        print(f'\nError: {e}')
        import traceback
        traceback.print_exc()
        raise
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process data folder path')
    parser.add_argument('data_folder', help='Path to the data folder')
    args = parser.parse_args()
    data_folder = Path(args.data_folder)
    if not data_folder.exists():
        print(f'The data folder {data_folder} does not exist!')
        exit(1)
    if not data_folder.is_dir():
        print(f'The data folder {data_folder} is not a folder!')
        exit(1)
    main(data_folder)
