import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import openai
import requests
from dotenv import find_dotenv, load_dotenv
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import UnstructuredURLLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter
from langchain.utilities import GoogleSerperAPIWrapper
from langchain.vectorstores import FAISS

openai.api_key = os.getenv("OPENAI_API_KEY")
SERP_API_KEY = os.getenv("SERPER_API_KEY")
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY")

load_dotenv(find_dotenv())

embeddings = OpenAIEmbeddings()


# Serp request to get list of relevant articles
def search_serp(query):
    search = GoogleSerperAPIWrapper(k=5, type="search")
    response_json = search.results(query)

    return response_json


#  llm to choose the best articles, and return urls
def pick_best_articles_urls(response_json, query, llm_model="gpt-3.5-turbo"):
    llm_model = llm_model
    # turn json to string
    response_str = json.dumps(response_json)

    # create llm to choose best articles
    llm = ChatOpenAI(temperature=0.7, model=llm_model)
    template = """
      You are a renowned writer, communicationist, AI engineer, programmer, Software Engineer, Developer and a technical trainer
      , you are amazing at finding the most interesting and relevant, trending and updated articles and news in certain topics.

      QUERY RESPONSE:{response_str}

      Above is the list of search results for the query {query}.

      You are required to choose only the best articles from the list and return ONLY an array of the urls.
      Do not include any other thing apart from the array of the urls -
      Also make sure the articles are recent and not outdated.
      If the file, or URL is invalid, use the url www.google.com instead.
    """
    prompt_template = PromptTemplate(
        input_variables=["response_str", "query"], template=template
    )
    article_chooser_chain = LLMChain(llm=llm, prompt=prompt_template, verbose=True)
    urls = article_chooser_chain.run(response_str=response_str, query=query)

    url_list = json.loads(urls)
    return url_list


# Get content for each article from urls and make summaries
def extract_content_from_urls(urls):
    # use unstructuredURLLoader
    loader = UnstructuredURLLoader(urls=urls)
    data = loader.load()

    text_splitter = CharacterTextSplitter(
        separator="\n", chunk_size=1000, chunk_overlap=200, length_function=len
    )
    docs = text_splitter.split_documents(data)
    db = FAISS.from_documents(docs, embeddings)

    return db


# summarize the articles...
def generate_report(db, query, k=6):
    docs = db.similarity_search(query, k=k)

    # Join the content of the page_content attribute from eac document...
    docs_page_content = " ".join([d.page_content for d in docs])

    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
    template = """
       {docs}
        You are a renowned writer, communicationist, AI engineer, programmer, Software Engineer, Developer and a technical trainer,
        you have to write a well detailed report (like a technical report or otherwise) with respect to this {query}.
        
        ARTICLE REPORT:
    """
    prompt_template = PromptTemplate(
        input_variables=["docs", "query"], template=template
    )

    report_chain = LLMChain(llm=llm, prompt=prompt_template, verbose=True)

    response = report_chain.run(docs=docs_page_content, query=query)

    return response.replace("\n", "")


# 5. Turn summarization into newsletter (or article...)
def generate_newsletter(summaries, query):
    summaries_str = str(summaries)
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
    template = """
    {summaries_str}
        As a world class journalist, researcher, article, newsletter and blog writer,
        you'll use the text above as the context about {query}
        to write an excellent newsletter to be sent to subscribers about {query}.

        This newsletter will be sent as an email.  The format is going to be in the format of 
        "Hacker Newsletter".

        Please ensure to write it informally - no "Dear" or any other formalities.  
        Start the newsletter with a clear and concise Headline. Craft compelling and clear headline that capture the essence of the content.
        This headline should be the first thing in our newsletter just like a good newsletter. 
        Avoid jargon-heavy title that might be intimidating to some readers. 
        Make it easy for the audience to understand the value of the newsletter.
        `Hi All!
          Here is your weekly dose of the AI TLDR Newsletter, a curated list of what I find interesting
          and worth reading. (Please add the estimated time to read the newsletter here so that the user will get to know the time it takes to read it).`

        Make sure to also write a backstory about the topic - make it personal, engaging and lighthearted before
        going into the detail of the newsletter.

        while writing the newsletter, ensure to do the following but do not discuss the following as heading or subheading:
    
        The content should address the {query} topic very well
        
        Ensure the use of Visual Appeal.
        Use visuals such as images, infographics, and charts to break up long blocks of text and make the content more visually appealing.
        Ensure engaging opening. Start with a compelling introduction that sparks curiosity. 
        Pose a question, share a relevant anecdote, or highlight a key point to draw readers in. 
        The opening should make them want to continue reading.
        Ensure adequate storytelling.Tell stories that resonate with your audience. 
        Use real-world examples, case studies, or anecdotes to illustrate technical concepts. 
     
        Ensure there isw a Call-to-Action (CTA). End each newsletter with a clear call-to-action. 
        This could be encouraging readers to share feedback, participate in discussions, or explore related content.

        As a signoff, write a clever quote related to learning, general wisdom, or {query}.  Be as creative with this one as possible - and then,
        Sign with "Engr Mountain
          - AI/Software Engineer"

        NEWSLETTER-->:
    """
    prompt_template = PromptTemplate(
        input_variables=["summaries_str", "query"], template=template
    )
    news_letter_chain = LLMChain(llm=llm, prompt=prompt_template, verbose=True)
    news_letter = news_letter_chain.predict(summaries_str=summaries_str, query=query)

    return news_letter


def send_email(from_email, to_emails, subject, body, api=EMAIL_API_KEY):
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        smtp_server = smtplib.SMTP("smtp.gmail.com", 587)
        smtp_server.starttls()
        smtp_server.login(from_email, api)
        smtp_server.sendmail(from_email, to_emails, msg.as_string())
        smtp_server.quit()
        print("Email sent.")
    except Exception as e:
        print("Email not sent", e)


import os

import streamlit as st
from helpers import *

from_email = "engrmountain@gmail.com"
to_emails = ["nzuteokafor@gmail.com"]
subject = "AI TLDR Weekly Newsletter"
