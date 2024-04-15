import re
from collections import Counter
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer, WordNetLemmatizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def preprocess_text(text):
    stop_words = set(stopwords.words('english'))
    porter = PorterStemmer()
    tokens = word_tokenize(text.lower())
    filtered_tokens = [porter.stem(token) for token in tokens if token.isalpha() and token not in stop_words]
    lemmatizer = WordNetLemmatizer()
    final_tokens = [lemmatizer.lemmatize(word) for word in filtered_tokens]
    return " ".join(final_tokens)

def calculate_cosine_similarity(text1, text2):
    preprocessed_text1 = preprocess_text(text1)
    preprocessed_text2 = preprocess_text(text2)
    corpus = [preprocessed_text1, preprocessed_text2]
    vectorizer = CountVectorizer().fit_transform(corpus)
    vectors = vectorizer.toarray()
    return cosine_similarity([vectors[0]], [vectors[1]])[0][0]

def get_missing_words_suggestions(resume, job_desc):
    job_desc_words = re.findall(r'\b\w+\b', job_desc.lower())
    resume_words = re.findall(r'\b\w+\b', resume.lower())
    job_desc_word_counts = Counter(job_desc_words)
    resume_word_counts = Counter(resume_words)
    missing_words = set(job_desc_word_counts) - set(resume_word_counts)
    return list(missing_words)
