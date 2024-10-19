import time
import random

def _varied(base, spread_low=0.85, spread_high=1.18):
    return base * random.uniform(spread_low, spread_high)

def human_pause(short=True):
    if short:
        t = _varied(random.uniform(0.4, 1.2))
    else:
        t = _varied(random.uniform(1.5, 3.8))
    time.sleep(t)

def human_typing_delay():
    base = random.uniform(0.06, 0.2)
    r = random.random()
    if r < 0.05:
        base += random.uniform(0.2, 0.6)
    elif r < 0.11:
        base *= random.uniform(0.4, 0.7)
    return _varied(base)

def human_reading_delay(length_chars=0):
    base = random.uniform(1.6, 4.5)
    if length_chars > 0:
        base += min(length_chars / random.uniform(200, 380), 15)
    time.sleep(_varied(base))

def human_scroll_delay():
    return _varied(random.uniform(0.1, 0.48))

def human_scroll_step():
    return random.randint(55, 175)

def human_between_jobs_delay():
    time.sleep(_varied(random.uniform(2.0, 6.0)))

def human_form_section_delay():
    time.sleep(_varied(random.uniform(0.6, 2.2)))

def human_click_delay():
    time.sleep(_varied(random.uniform(0.15, 0.7)))

def human_page_load_delay():
    time.sleep(_varied(random.uniform(1.6, 4.8)))

def human_glance():
    if random.random() < 0.09:
        time.sleep(_varied(random.uniform(0.35, 1.2)))

def human_occasional_long_pause():
    if random.random() < 0.025:
        time.sleep(_varied(random.uniform(1.8, 4.5)))

def human_click_offset():
    return (random.randint(-10, 10), random.randint(-10, 10))

def should_simulate_typo():
    return random.random() < 0.02

def human_session_break_min_seconds():
    return 60 * random.uniform(8, 22)

def human_long_break_seconds():
    return random.uniform(4 * 60, 14 * 60)

def human_should_take_long_break(page_count):
    p = min(0.12 + page_count * 0.015, 0.35)
    return random.random() < p

def human_warmup_feed_scroll_pause():
    time.sleep(_varied(random.uniform(3.0, 12.0)))

def human_warmup_transition():
    time.sleep(_varied(random.uniform(2.0, 6.0)))

def human_job_interest_level():
    r = random.random()
    if r < 0.15:
        return 'skip'
    elif r < 0.45:
        return 'glance'
    elif r < 0.8:
        return 'read'
    else:
        return 'interested'

def human_disinterested_glance():
    time.sleep(_varied(random.uniform(1.5, 4.0)))

def human_deep_reading_delay():
    time.sleep(_varied(random.uniform(8.0, 25.0)))

def human_max_applications_per_session():
    return random.randint(4, 10)

def human_max_pages_per_search():
    r = random.random()
    if r < 0.3:
        return 1
    elif r < 0.6:
        return 2
    elif r < 0.85:
        return 3
    else:
        return random.randint(4, 6)
