import streamlit as st
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import os
import PyPDF2
import re
from collections import Counter
import docx2txt
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import contractions
import spacy
from spacy.matcher import PhraseMatcher
from skillNer.general_params import SKILL_DB
from skillNer.skill_extractor_class import SkillExtractor

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import string

# Set up OpenAI
os.environ["OPEN_API_KEY"] = "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"
llm = OpenAI(openai_api_key="your_api_key", temperature=0.5, max_tokens=2400)

# Define a function to read PDF files
def read_pdf(file_path):
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        text = ''
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text()
    return text

# Define a function to read document files
def read_document(file_path):
    try:
        return docx2txt.process(file_path)
    except Exception as e:
        st.error(f"Error reading document at '{file_path}': {e}")
        return ""

# Define a function to preprocess text
def preprocess_text(text):
    text = text.lower()
    text = text.replace("\n", " ")
    text = contractions.fix(text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    tokens = [word for word in tokens if word not in stop_words]
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(word) for word in tokens]
    preprocessed_text = ' '.join(tokens)
    return preprocessed_text

# Define a function to extract skills from text
def get_skills(text):
    skills = []
    nlp = spacy.load("en_core_web_lg")
    skill_extractor = SkillExtractor(nlp, SKILL_DB, PhraseMatcher)
    annotations = skill_extractor.annotate(text)

    if 'full_matches' in annotations['results']:
        for item in annotations['results']['full_matches']:
            doc_node_value = item['doc_node_value']
            skills.append(doc_node_value)

    if 'ngram_scored' in annotations['results']:
        for item in annotations['results']['ngram_scored']:
            doc_node_value = item['doc_node_value']
            skills.append(doc_node_value)

    return skills

# Define a function to calculate similarity between two documents
def calculate_similarity(doc1, doc2):
    text = [doc1, doc2]
    cv = CountVectorizer()
    count_matrix = cv.fit_transform(text)
    similarities = cosine_similarity(count_matrix)[0][1]
    return float(format(similarities * 100, '.2f'))

# Define a function to check application status based on similarity percentage
def check_application_status(similarity_percentage, threshold=80):
    if similarity_percentage > threshold:
        return "Application is accepted"
    else:
        return "Application is rejected"

# Define a function to find missing words between two sets of text
def get_missing_words(resume, jd_desc):
    resume = set(resume)
    jd_desc = set(jd_desc)
    missing_words = jd_desc - resume
    return list(missing_words)

# Define a function to generate HTML portfolio for all variants
def generate_all_portfolios(resume_text):
    portfolio_paths = []
    for i in range(1, 9):
        portfolio_path = f"portfolio_{i}.html"
        templates = {
            "1": "make a professional looking html page with colors and styles from the following resume text: {resume_info}",
            "2": "make a professional looking html page with colors styles and proper allignment from the following resume text: {resume_info}",
            "3": "make a professional looking html page with professional colors and styles from the following resume text: {resume_info}",
            "4": "make a professional looking html page with creative colors and professional styles from the following resume text: {resume_info}",
            "5": "make a professional looking html page with creative colors of font and background and eye catching styles from the following resume text: {resume_info}",
            "6": "make a professional looking html portfolio page, use eye catching colors scheme through out the page from the following resume text: {resume_info}",
            "7": "make a professional looking html portfolio page, use blue colors scheme and structure through out the page. Use the following resume text: {resume_info}",
            "8": "make a professional looking html portfolio page, use eye catching colors scheme and structure through out the page. Use the following resume text: {resume_info}"
        }
        prompt_template = PromptTemplate(input_variables=["resume_info"], template=templates[str(i)])
        prompt_template.format(resume_info=resume_text)
        chain = LLMChain(llm=llm, prompt=prompt_template)
        response = chain.invoke(resume_text)
        with open(portfolio_path, 'w') as file:
            file.write(response["text"])
        portfolio_paths.append(portfolio_path)
    return portfolio_paths

# Streamlit app
def main():
    st.title("Project Development Team - 4 :rocket:")

    st.title("AI Powered Resume Analysis and Portfolio Generation")

    # File uploaders for resume and job description
    resume_upload = st.file_uploader("Upload Resume (PDF or Word)", type=["pdf", "docx"])
    job_desc_upload = st.file_uploader("Upload Job Description (PDF or Word)", type=["pdf", "docx"])

    # Submit button
    if st.button("Submit"):
        # Check if both documents are provided
        if resume_upload and job_desc_upload:
            # Show loader
            with st.spinner('Analyzing documents...'):
                # Load documents and preprocess
                resume_text = preprocess_text(read_document(resume_upload))
                job_desc_text = preprocess_text(read_document(job_desc_upload))

                if not resume_text or not job_desc_text:
                    st.error("Error: One or both documents couldn't be read.")
                else:
                    # Calculate similarity
                    resume_skills = get_skills(resume_text)
                    job_desc_skills = get_skills(job_desc_text)

                    similarity_percentage = calculate_similarity(' '.join(resume_skills), ' '.join(job_desc_skills))

                    # Check application status
                    status = check_application_status(similarity_percentage)

                    # Get missing words suggestions
                    missing_words = get_missing_words(resume_skills, job_desc_skills)

                    # Hide loader
                    st.success('Analysis complete!')

                    # Display results
                    st.write(f"Similarity: {similarity_percentage}%")
                    st.success(status)

                    # Display missing words suggestions
                    if missing_words:
                        st.warning("\nWords from the Job Description not found in the Resume:")
                        for missing_word in missing_words:
                            st.write(f"- {missing_word}")
                    else:
                        st.info("All required words are present in the Resume.")

        else:
            st.warning("Please upload both resume and job description.")

    st.title("Resume to HTML Portfolio Generator")

    # File upload
    uploaded_file = st.file_uploader("Upload your resume (PDF)", type=["pdf"])

    if uploaded_file is not None:
        resume_text = read_pdf(uploaded_file)

        st.text_area("Resume Text", value=resume_text, height=300, max_chars=None)

        # Button to generate all HTML portfolios
        if st.button("Generate All HTML Portfolios"):
            portfolio_paths = generate_all_portfolios(resume_text)
            st.success("All HTML Portfolios generated successfully!")

            # Provide download links for all generated HTML files
            for i, path in enumerate(portfolio_paths, start=1):
                st.markdown(f"[Download HTML Portfolio {i}](path)", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
