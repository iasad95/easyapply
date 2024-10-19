import os
import re
import textwrap
from datetime import datetime
from typing import Optional, List, Any
from utils import Markdown
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.chains.router import MultiPromptChain
from langchain.chains.llm import LLMChain
from langchain.chains.router.llm_router import LLMRouterChain, RouterOutputParser
from langchain.chains.router.multi_prompt_prompt import MULTI_PROMPT_ROUTER_TEMPLATE
from langchain.schema import BaseMessage
try:
    from langchain_core.language_models.chat_models import SimpleChatModel
except ImportError:
    from langchain.chat_models.base import SimpleChatModel
from Levenshtein import distance
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import PromptTemplate
except ImportError:
    from langchain import PromptTemplate
    try:
        from langchain.chat_models import ChatOpenAI
    except ImportError:
        from langchain_community.chat_models import ChatOpenAI
try:
    from langchain.llms.base import LLM as BaseLLM
except ImportError:
    from langchain_core.language_models.llms import BaseLLM

def has_openai_key():
    return bool(os.getenv('OPEN_AI_API_KEY') or os.getenv('OPENAI_API_KEY'))

class SimpleAnswerer:

    def __init__(self, resume: str, personal_data: str, cover_letter: str, job_filters: str, personal_info: dict):
        self.resume = resume
        self.personal_data = personal_data
        self.cover_letter = cover_letter
        self._job_description = ''
        self.job_description_summary = ''
        self.personal_info = personal_info or {}

    @property
    def job_description(self):
        return self._job_description

    @job_description.setter
    def job_description(self, value):
        self._job_description = value
        self.job_description_summary = value[:2000] if value else ''

    def job_description_passes_filters(self):
        return True

    def answer_question_from_options(self, question: str, options: list) -> str:
        skip = ('select', 'choose', 'none', 'select an option', 'please select', '--', '')
        valid = [o for o in options if o and str(o).strip().lower() not in skip and (len(str(o)) > 1)]
        if not valid:
            return options[0] if options else ''
        q = question.lower()
        for v in valid:
            if str(v).lower() == 'yes':
                return 'Yes'
        for v in valid:
            if str(v).lower() == 'no':
                return 'No'
        for opt in valid:
            if 'years' in q or 'experience' in q:
                if any((c.isdigit() for c in str(opt))):
                    return opt
            if 'first name' in q and 'First Name' in self.personal_info:
                if self.personal_info['First Name'].lower() in str(opt).lower():
                    return opt
            if 'last name' in q and 'Last Name' in self.personal_info:
                if self.personal_info['Last Name'].lower() in str(opt).lower():
                    return opt
        return valid[0]

    def answer_question_numeric(self, question: str, default_experience: int=5) -> int:
        return default_experience

    def answer_question_textual_wide_range(self, question: str) -> str:
        q = question.lower()
        pi = self.personal_info
        if 'first name' in q or 'full name' in q:
            return pi.get('First Name', '') + (' ' + pi.get('Last Name', '') if 'full' in q else '')
        if 'last name' in q:
            return pi.get('Last Name', '')
        if 'phone' in q or 'mobile' in q:
            return pi.get('Mobile Phone Number', '') or pi.get('Phone', '')
        if 'email' in q:
            return pi.get('Email', '')
        if 'address' in q or 'street' in q:
            return pi.get('Street address', '') or pi.get('Address', '')
        if 'city' in q:
            return pi.get('City', '')
        if 'state' in q or 'province' in q:
            return pi.get('State', '')
        if 'zip' in q or 'postal' in q:
            return str(pi.get('Zip', ''))
        if 'linkedin' in q:
            return pi.get('Linkedin', '')
        if 'website' in q or 'github' in q:
            return pi.get('Website', '') or pi.get('Linkedin', '')
        if 'year' in q and 'experience' in q:
            return '5'
        if 'cover letter' in q or 'message' in q:
            return self.cover_letter[:500] if self.cover_letter else 'Please see my attached resume.'
        return 'See resume' if len(q) > 10 else 'Yes'

    def try_fix_answer(self, question: str, answer: str, error: str) -> str:
        if 'number' in error.lower() or 'whole' in error.lower():
            return ''.join((c for c in answer if c.isdigit())) or '5'
        if 'short' in error.lower() or 'valid' in error.lower():
            return str(answer)[:100]
        return str(answer)[:50]

class LLMLogger:

    def __init__(self, llm: Any):
        self.llm = llm

    @staticmethod
    def log_request(model: str, prompt: str, reply: str):
        calls_log = os.path.join(os.getcwd(), 'open_ai_calls.log')
        f = open(calls_log, 'a')
        time = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        f.write(f"<request model='{model}' time='{time}'>\n")
        f.write(prompt)
        f.write('\n')
        f.write('</request>\n')
        f.write('<response>\n')
        f.write(reply)
        f.write('\n')
        f.write('</response>\n')
        f.write('\n\n')
        f.close()

class LoggerLLMModel(BaseLLM):
    llm: Any

    @property
    def _llm_type(self) -> str:
        return 'custom'

    def _call(self, prompt: str, stop: Optional[List[str]]=None, run_manager: Optional[CallbackManagerForLLMRun]=None, **kwargs) -> str:
        if hasattr(self.llm, 'invoke'):
            result = self.llm.invoke(prompt, stop=stop)
            reply = result.content if hasattr(result, 'content') else str(result)
        else:
            reply = self.llm(prompt, stop=stop, **kwargs)
        model_name = getattr(self.llm, 'model_name', None) or getattr(self.llm, 'model', 'unknown')
        LLMLogger.log_request(str(model_name), prompt, reply)
        return reply

class LoggerChatModel(SimpleChatModel):
    llm: Any

    @property
    def _llm_type(self) -> str:
        return 'custom'

    def _call(self, messages: List[BaseMessage], stop: Optional[List[str]]=None, run_manager: Optional[CallbackManagerForLLMRun]=None) -> str:
        if hasattr(self.llm, 'invoke'):
            result = self.llm.invoke(messages, stop=stop)
            reply = result.content if hasattr(result, 'content') else str(result)
        else:
            reply_obj = self.llm.generate([messages], stop=stop, callbacks=run_manager)
            reply = reply_obj.generations[0][0].text
        model_name = getattr(self.llm, 'model_name', None) or getattr(self.llm, 'model', 'unknown')
        LLMLogger.log_request(str(model_name), str(messages), reply)
        return reply

class GPTAnswerer:

    def __init__(self, resume: str, personal_data: str, cover_letter: str, job_filtering_rules: str):
        self.resume = resume
        self.personal_data = personal_data
        self.cover_letter = cover_letter
        self._job_description = ''
        self.job_description_summary = ''
        self.job_filtering_rules = job_filtering_rules
        api_key = GPTAnswerer.openai_api_key()

        def _make_chat(**kwargs):
            try:
                return ChatOpenAI(model='gpt-3.5-turbo', openai_api_key=api_key, **kwargs)
            except TypeError:
                return ChatOpenAI(model_name='gpt-3.5-turbo', openai_api_key=api_key, **kwargs)
        self.llm_cheap = LoggerChatModel(llm=_make_chat(temperature=0.8))
        self.llm_expensive = LoggerLLMModel(llm=_make_chat(temperature=0.3))

    @property
    def job_description(self):
        return self._job_description

    @job_description.setter
    def job_description(self, value):
        self._job_description = value
        self.job_description_summary = self.summarize_job_description(value)

    @staticmethod
    def openai_api_key():
        key = os.getenv('OPEN_AI_API_KEY') or os.getenv('OPENAI_API_KEY')
        if not key:
            raise Exception('OpenAI API key not found. Set OPEN_AI_API_KEY or OPENAI_API_KEY in .env')
        return key

    @staticmethod
    def _preprocess_template_string(template: str) -> str:
        processed_template = textwrap.dedent(template)
        return processed_template

    def summarize_job_description(self, text: str) -> str:
        summarize_prompt_template = 'Summarize this job post in concise bullets. Keep role, skills, seniority, stack, location, and work model.\n{text}\n\nSummary:'
        summarize_prompt_template = self._preprocess_template_string(summarize_prompt_template)
        prompt = PromptTemplate(input_variables=['text'], template=summarize_prompt_template)
        chain = LLMChain(llm=self.llm_cheap, prompt=prompt)
        output = chain.run(text=text)
        while '\n ' in output:
            output = output.replace('\n ', '\n')
        return output

    def answer_question_textual_wide_range(self, question: str) -> str:
        resume_stuff_template = 'Use first person. Give short direct answers from resume/personal data. If unsure but likely, answer positively.\nPersonal data:\n{personal_data}\nResume:\n{resume}\nQuestion:\n{question}\nAnswer:'
        cover_letter_template = 'If asked for a cover letter, tailor it lightly to role/company. Keep tone and structure. Remove unresolved placeholders.\nJob:\n{job_description}\nCover letter:\n{cover_letter}\nQuestion:\n{question}\nAnswer:'
        summary_template = 'Answer based on resume and job summary. Keep concise, first person, and direct.\nJob:\n{job_description}\nResume:\n{resume}\nQuestion:\n{question}\nAnswer:'
        prompt_infos = [{'name': 'resume', 'description': 'Resume, skills, and personal data questions.', 'prompt_template': resume_stuff_template}, {'name': 'cover letter', 'description': 'Cover letter and motivation questions.', 'prompt_template': cover_letter_template}, {'name': 'summary', 'description': 'Job-fit and role-summary questions.', 'prompt_template': summary_template}]
        resume_stuff_template = self._preprocess_template_string(resume_stuff_template)
        resume_stuff_template = self._preprocess_template_string(resume_stuff_template)
        resume_stuff_template = self._preprocess_template_string(resume_stuff_template)
        resume_stuff_prompt_template = PromptTemplate(template=resume_stuff_template, input_variables=['personal_data', 'resume', 'question'])
        resume_stuff_prompt_template = resume_stuff_prompt_template.partial(personal_data=self.personal_data, resume=self.resume, question=question)
        resume_stuff_chain = LLMChain(llm=self.llm_cheap, prompt=resume_stuff_prompt_template)
        cover_letter_prompt_template = PromptTemplate(template=cover_letter_template, input_variables=['cover_letter', 'job_description', 'question'])
        cover_letter_prompt_template = cover_letter_prompt_template.partial(cover_letter=self.cover_letter, job_description=self.job_description_summary, question=question)
        cover_letter_chain = LLMChain(llm=self.llm_cheap, prompt=cover_letter_prompt_template)
        summary_prompt_template = PromptTemplate(template=summary_template, input_variables=['resume', 'job_description', 'question'])
        summary_prompt_template = summary_prompt_template.partial(resume=self.resume, job_description=self.job_description_summary, question=question)
        summary_chain = LLMChain(llm=self.llm_cheap, prompt=summary_prompt_template)
        destination_chains = {'resume': resume_stuff_chain, 'cover letter': cover_letter_chain, 'summary': summary_chain}
        destinations = [f"{p['name']}: {p['description']}" for p in prompt_infos]
        destinations_str = '\n'.join(destinations)
        router_template = MULTI_PROMPT_ROUTER_TEMPLATE.format(destinations=destinations_str)
        router_prompt = PromptTemplate(template=router_template, input_variables=['input'], output_parser=RouterOutputParser())
        router_chain = LLMRouterChain.from_llm(self.llm_expensive, router_prompt)
        chain = MultiPromptChain(router_chain=router_chain, destination_chains=destination_chains, default_chain=resume_stuff_chain, verbose=True)
        result = chain({'input': question})
        result_text = result['text'].strip()
        result_text = self._remove_placeholders(result_text)
        return result_text

    def answer_question_textual(self, question: str) -> str:
        template = 'Answer in first person. Keep under 140 chars when possible. Use resume/personal data and be direct.\nPersonal data:\n{personal_data}\nResume:\n{resume}\nQuestion:\n{question}\nAnswer:'
        template = self._preprocess_template_string(template)
        prompt = PromptTemplate(input_variables=['personal_data', 'resume', 'question'], template=template)
        chain = LLMChain(llm=self.llm_cheap, prompt=prompt)
        output = chain.run(personal_data=self.personal_data, resume=self.resume, question=question)
        return output

    def answer_question_numeric(self, question: str, default_experience: int=4) -> int:
        template = 'Return only an integer. If unknown, return {default_experience}.\nPersonal data:\n{personal_data}\nResume:\n{resume}\nQuestion:\n{question}\nAnswer:'
        template = self._preprocess_template_string(template)
        prompt = PromptTemplate(input_variables=['default_experience', 'personal_data', 'resume', 'question'], template=template)
        chain = LLMChain(llm=self.llm_cheap, prompt=prompt)
        output_str = chain.run(personal_data=self.personal_data, resume=self.resume, question=question, default_experience=default_experience)
        try:
            output = int(output_str)
        except ValueError:
            output = default_experience
            print(f'Error: The output of the LLM is not an integer number. The default experience ({default_experience}) will be returned instead. The output was: {output_str}')
        return output

    def answer_question_from_options(self, question: str, options: list[str]) -> str:
        template = 'Pick exactly one option using resume/personal data. Avoid placeholder options.\nPersonal data:\n{personal_data}\nResume:\n{resume}\nQuestion:\n{question}\nOptions:\n{options}\nAnswer:'
        template = self._preprocess_template_string(template)
        prompt = PromptTemplate(input_variables=['personal_data', 'resume', 'question', 'options'], template=template)
        chain = LLMChain(llm=self.llm_cheap, prompt=prompt)
        output = chain.run(personal_data=self.personal_data, resume=self.resume, question=question, options=options)
        if output not in options:
            output = self._closest_matching_option(output, options)
        return output

    @staticmethod
    def _closest_matching_option(to_match: str, options: list[str]) -> str:
        closest_option = min(options, key=lambda option: distance(to_match, option))
        return closest_option

    @staticmethod
    def _contains_placeholder(text: str) -> bool:
        pattern = '\\[\\[([^\\]]+)\\]\\]'
        match = re.search(pattern, text)
        return match is not None

    def _remove_placeholders(self, text: str) -> str:
        summarize_prompt_template = 'Rewrite text by removing all [[placeholders]]. Fill from context when possible; otherwise delete cleanly.\nText:\n{text_with_placeholders}\nRewritten:'
        summarize_prompt_template = self._preprocess_template_string(summarize_prompt_template)
        result = text
        max_iterations = 5
        concurrent_iterations = 0
        while self._contains_placeholder(result) and concurrent_iterations < max_iterations:
            prompt = PromptTemplate(input_variables=['text_with_placeholders'], template=summarize_prompt_template)
            chain = LLMChain(llm=self.llm_cheap, prompt=prompt)
            output = chain.run(text_with_placeholders=result)
            result = output
            concurrent_iterations += 1
        return result

    def job_title_passes_filters(self, job_title: str) -> bool:
        template = "Return 'yes' if this job title matches preferences, else 'no'.\nJob title: {job_title}\nPreferences:\n{job_title_filters}\nAnswer:"
        template = self._preprocess_template_string(template)
        job_title_filters = Markdown.extract_content_from_markdown(self.job_filtering_rules, 'Job Title Filters')
        prompt = PromptTemplate(input_variables=['job_title', 'job_title_filters'], template=template)
        chain = LLMChain(llm=self.llm_cheap, prompt=prompt)
        output = chain.run(job_title=job_title, job_title_filters=job_title_filters)
        if output.lower() not in ['yes', 'no']:
            output = self._closest_matching_option(output, ['yes', 'no'])
        return output.lower() == 'yes'

    def job_description_passes_filters(self) -> bool:
        template = "Return 'yes' if this job description matches preferences, else 'no'.\nJob description:\n{job_description}\nPreferences:\n{job_description_filters}\nAnswer:"
        template = self._preprocess_template_string(template)
        job_description_filters = Markdown.extract_content_from_markdown(self.job_filtering_rules, 'Job Description Filters')
        prompt = PromptTemplate(input_variables=['job_description', 'job_description_filters'], template=template)
        chain = LLMChain(llm=self.llm_cheap, prompt=prompt)
        output = chain.run(job_description=self.job_description_summary, job_description_filters=job_description_filters)
        if output.lower() not in ['yes', 'no']:
            output = self._closest_matching_option(output, ['yes', 'no'])
        return output.lower() == 'yes'

    def try_fix_answer(self, question: str, answer: str, error: str) -> str:
        template = 'Fix the input using the error. Keep output short and valid.\nQuestion: {question}\nInput: {input}\nError: {error}\nFixed input:'
        template = self._preprocess_template_string(template)
        prompt = PromptTemplate(input_variables=['question', 'input', 'error'], template=template)
        chain = LLMChain(llm=self.llm_cheap, prompt=prompt)
        output = chain.run(question=question, input=answer, error=error)
        return output
