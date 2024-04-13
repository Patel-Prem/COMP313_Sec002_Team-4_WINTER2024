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


# nltk.download('punkt')
# nltk.download('stopwords')
# nltk.download('wordnet')


import streamlit as st

def read_document(file_path):
    try:
        return docx2txt.process(file_path)
    except Exception as e:
        st.error(f"Error reading document at '{file_path}': {e}")
        return ""

def preprocess_text(text):
    # Convert to lowercase and remove stop words
    ''' Code by Arun
    text = text.lower()
    text = ' '.join([word for word in text.split() if word not in ENGLISH_STOP_WORDS])
    return text
    '''

    # Code by - Prem start
    text = text.lower()

    text = text.replace("\n", " ")
    
    # Expand contractions
    text = contractions.fix(text)
    
    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))
    
    # Tokenize text
    tokens = word_tokenize(text)
    
    # Remove stopwords
    stop_words = set(stopwords.words('english'))
    tokens = [word for word in tokens if word not in stop_words]
    
    # Lemmatize tokens
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(word) for word in tokens]
    
    # Join tokens back into a string
    preprocessed_text = ' '.join(tokens)
    
    return preprocessed_text
    # Code by - Prem end
   
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

def calculate_similarity(doc1, doc2):
    text = [doc1, doc2]
    cv = CountVectorizer()
    count_matrix = cv.fit_transform(text)
    similarities = cosine_similarity(count_matrix)[0][1]
    return float(format(similarities * 100, '.2f'))

def check_application_status(similarity_percentage, threshold=80):
    if similarity_percentage > threshold:
        return "Application is accepted"
    else:
        return "Application is rejected"

def get_missing_words_suggestions(resume, job_desc):
    # Tokenize the words in the job description and resume
    job_desc_words = re.findall(r'\b\w+\b', job_desc.lower())
    resume_words = re.findall(r'\b\w+\b', resume.lower())

    # Count the occurrences of each word in the job description and resume
    job_desc_word_counts = Counter(job_desc_words)
    resume_word_counts = Counter(resume_words)

    # Identify words in the job description that are not present in the resume
    missing_words = set(job_desc_word_counts) - set(resume_word_counts)

    return list(missing_words)


def get_missing_words(resume, jd_desc):
    resume = set(resume)
    jd_desc = set(jd_desc)
        
    missing_words = jd_desc - resume
    
    return list(missing_words)

# Streamlit app header
st.title("AI Powered by Resume Scorer")

# File uploaders for resume and job description
resume_upload = st.file_uploader("Upload Resume (PDF or Word)", type=["pdf", "docx"])
job_desc_upload = st.file_uploader("Upload Job Description (PDF or Word)", type=["pdf", "docx"])

# Submit button
if st.button("Submit"):
    # Check if both documents are provided
    if resume_upload and job_desc_upload:
        # Load documents and preprocess
        resume = preprocess_text(read_document(resume_upload))
        job_desc = preprocess_text(read_document(job_desc_upload))

        if not resume or not job_desc:
            st.error("Error: One or both documents couldn't be read.")
        else:
            # Calculate similarity

            resume = get_skills(resume)
            job_desc = get_skills(job_desc)

            similarity_percentage = calculate_similarity(' '.join(resume), ' '.join(job_desc))
            st.write(f"Similarity: {similarity_percentage}%")

            # Check application status
            status = check_application_status(similarity_percentage)
            st.success(status)

            # Get missing words suggestions
            missing_words = get_missing_words(resume, job_desc)

            # Display missing words suggestions
            if missing_words:
                st.warning("\nWords from the Job Description not found in the Resume:")
                for missing_word in missing_words:
                    st.write(f"- {missing_word}")
            else:
                st.info("All required words are present in the Resume.")
    else:
        st.warning("Please upload both resume and job description.")
