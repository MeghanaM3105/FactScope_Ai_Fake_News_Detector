from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import numpy as np
import pandas as pd
import re
import requests
import joblib
import os
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import hashlib
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('wordnet')

app = Flask(__name__, static_folder='static')
CORS(app)

# API Keys (store in .env file)
NEWS_API_KEY = os.getenv('NEWS_API_KEY', 'your_news_api_key')
GOOGLE_FACT_CHECK_API_KEY = os.getenv('GOOGLE_FACT_CHECK_API_KEY', 'your_google_api_key')
MEDIA_STACK_API_KEY = os.getenv('MEDIA_STACK_API_KEY', 'your_mediastack_key')

# Trusted news sources
TRUSTED_SOURCES = [
    'reuters.com', 'apnews.com', 'bbc.com', 'bbc.co.uk',
    'nytimes.com', 'wsj.com', 'washingtonpost.com',
    'theguardian.com', 'npr.org', 'politico.com',
    'economist.com', 'bloomberg.com', 'ft.com',
    'cnn.com', 'abcnews.go.com', 'cbsnews.com',
    'nbcnews.com', 'usatoday.com', 'time.com',
    'news.yahoo.com', 'huffpost.com', 'buzzfeednews.com'
]

# Suspicious sources (known for misinformation)
SUSPICIOUS_SOURCES = [
    'infowars.com', 'breitbart.com', 'dailymail.co.uk',
    'thesun.co.uk', 'dailystar.co.uk', 'dailymirror.co.uk',
    'naturalnews.com', 'beforeitsnews.com', 'activistpost.com'
]

class NewsVerifier:
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        self.load_or_train_model()
    
    def preprocess_text(self, text):
        """Preprocess text for model prediction"""
        # Convert to lowercase
        text = text.lower()
        # Remove special characters and digits
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        # Tokenize
        words = text.split()
        # Remove stopwords and lemmatize
        words = [self.lemmatizer.lemmatize(word) for word in words if word not in self.stop_words]
        return ' '.join(words)
    
    def load_or_train_model(self):
        """Load existing model or train a new one"""
        model_path = 'news_verifier_model.pkl'
        vectorizer_path = 'tfidf_vectorizer.pkl'
        
        if os.path.exists(model_path) and os.path.exists(vectorizer_path):
            # Load existing model
            self.model = joblib.load(model_path)
            self.vectorizer = joblib.load(vectorizer_path)
            print("Model loaded successfully")
        else:
            # Train new model with synthetic data
            self.train_model()
    
    def train_model(self):
        """Train the logistic regression model with synthetic data"""
        print("Training new model...")
        
        # Synthetic training data (in production, use real dataset)
        fake_news = [
            "You won't believe what they found! SHOCKING discovery proves government hiding truth",
            "Miracle cure for cancer discovered - Big Pharma doesn't want you to know",
            "BREAKING: Alien spaceship found in Area 51, authorities confirm cover-up",
            "This simple trick will make you rich overnight - banks hate this",
            "Vaccines cause autism - new study proves it but media won't report",
            "Celebrity caught in scandal - see the photos before they're deleted",
            "The truth about 5G towers causing COVID-19 revealed",
            "Scientists discover that drinking bleach cures all diseases",
            "Obama signs secret executive order to ban guns",
            "FEMA camps being prepared for mass internment"
        ]
        
        real_news = [
            "According to Reuters, the Federal Reserve raised interest rates by 0.25%",
            "The World Health Organization announced new guidelines for pandemic response",
            "Researchers at Stanford published a study on climate change impacts",
            "The United Nations Security Council voted on new sanctions today",
            "NASA successfully launched a new satellite to study exoplanets",
            "The Supreme Court ruled on the constitutionality of the new law",
            "Scientists discovered a new species in the Amazon rainforest",
            "The European Union announced new trade agreements with Japan",
            "GDP growth figures released by the Commerce Department show 2.1% increase",
            "The Centers for Disease Control updated mask guidelines"
        ]
        
        # Create labels (0: fake, 1: real)
        texts = fake_news + real_news
        labels = [0] * len(fake_news) + [1] * len(real_news)
        
        # Preprocess texts
        processed_texts = [self.preprocess_text(text) for text in texts]
        
        # Create pipeline
        self.vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 3))
        self.model = LogisticRegression(random_state=42, max_iter=1000)
        
        # Train
        X = self.vectorizer.fit_transform(processed_texts)
        self.model.fit(X, labels)
        
        # Save model
        joblib.dump(self.model, 'news_verifier_model.pkl')
        joblib.dump(self.vectorizer, 'tfidf_vectorizer.pkl')
        print("Model trained and saved successfully")
    
    def predict(self, text):
        """Predict if news is fake or real"""
        processed = self.preprocess_text(text)
        X = self.vectorizer.transform([processed])
        prediction = self.model.predict(X)[0]
        probability = self.model.predict_proba(X)[0]
        
        confidence = max(probability) * 100
        
        return {
            'is_fake': bool(prediction == 0),
            'confidence': round(confidence, 2),
            'fake_probability': round(probability[0] * 100, 2),
            'real_probability': round(probability[1] * 100, 2)
        }

class NewsAPIIntegration:
    def __init__(self):
        self.news_api_key = NEWS_API_KEY
        self.fact_check_api_key = GOOGLE_FACT_CHECK_API_KEY
        self.media_stack_key = MEDIA_STACK_API_KEY
    
    def search_news_api(self, query):
        """Search for news articles using NewsAPI"""
        if not self.news_api_key or self.news_api_key == 'your_news_api_key':
            return []
        
        url = 'https://newsapi.org/v2/everything'
        params = {
            'q': query,
            'apiKey': self.news_api_key,
            'pageSize': 10,
            'sortBy': 'relevancy',
            'language': 'en'
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('articles', [])
        except Exception as e:
            print(f"NewsAPI error: {e}")
        return []
    
    def search_fact_check_api(self, query):
        """Search Google Fact Check API"""
        if not self.fact_check_api_key or self.fact_check_api_key == 'your_google_api_key':
            return []
        
        url = 'https://factchecktools.googleapis.com/v1alpha1/claims:search'
        params = {
            'query': query,
            'key': self.fact_check_api_key,
            'languageCode': 'en'
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('claims', [])
        except Exception as e:
            print(f"Fact Check API error: {e}")
        return []
    
    def search_mediastack(self, query):
        """Search Mediastack API"""
        if not self.media_stack_key or self.media_stack_key == 'your_mediastack_key':
            return []
        
        url = 'http://api.mediastack.com/v1/news'
        params = {
            'access_key': self.media_stack_key,
            'keywords': query,
            'languages': 'en',
            'limit': 10
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
        except Exception as e:
            print(f"Mediastack error: {e}")
        return []
    
    def verify_with_multiple_sources(self, text):
        """Verify news text against multiple sources"""
        # Extract key phrases for search
        words = text.split()[:10]  # First 10 words
        search_query = ' '.join(words)
        
        results = {
            'trusted_sources': [],
            'fact_checks': [],
            'contradictory_sources': []
        }
        
        # Search NewsAPI
        articles = self.search_news_api(search_query)
        for article in articles:
            source = article.get('source', {}).get('name', '').lower()
            url = article.get('url', '')
            
            # Check if source is trusted
            if any(trusted in url.lower() for trusted in TRUSTED_SOURCES):
                results['trusted_sources'].append({
                    'title': article.get('title'),
                    'source': source,
                    'url': url,
                    'published': article.get('publishedAt')
                })
            elif any(susp in url.lower() for susp in SUSPICIOUS_SOURCES):
                results['contradictory_sources'].append({
                    'title': article.get('title'),
                    'source': source,
                    'url': url,
                    'published': article.get('publishedAt')
                })
        
        # Search Fact Check API
        fact_checks = self.search_fact_check_api(search_query)
        for claim in fact_checks:
            results['fact_checks'].append({
                'text': claim.get('text'),
                'claimant': claim.get('claimant'),
                'rating': claim.get('claimReview', [{}])[0].get('textualRating'),
                'publisher': claim.get('claimReview', [{}])[0].get('publisher', {}).get('name')
            })
        
        return results

class SentimentAnalyzer:
    def __init__(self):
        self.sensational_patterns = [
            r'shock\w*', r'unbeliev\w*', r'mind[-\s]?blow\w*', r'you won\'?t believe',
            r'authorities', r'rigged', r'conspiracy', r'secret', r'exposed',
            r'scandal', r'cover\s?up', r'breaking', r'urgent', r'alert',
            r'incredible', r'amazing', r'miracle', r'cure', r'destroy',
            r'terrifying', r'horrifying', r'devastating', r'outrage'
        ]
        
        self.factual_patterns = [
            r'according to', r'reported by', r'study shows', r'research indicates',
            r'data shows', r'statistics', r'official', r'confirmed', r'announced',
            r'statement', r'said', r'told', r'reports', r'sources say',
            r'january|february|march|april|may|june|july|august|september|october|november|december',
            r'monday|tuesday|wednesday|thursday|friday|saturday|sunday',
            r'20\d{2}'
        ]
    
    def analyze(self, text):
        """Analyze sentiment and sensationalism"""
        lower_text = text.lower()
        
        # Check for sensational patterns
        sensational_score = 0
        sensational_words = []
        
        for pattern in self.sensational_patterns:
            matches = re.findall(pattern, lower_text)
            if matches:
                sensational_score += len(matches) * 2
                sensational_words.extend(matches)
        
        # Check for factual patterns
        factual_score = 0
        factual_words = []
        
        for pattern in self.factual_patterns:
            matches = re.findall(pattern, lower_text)
            if matches:
                factual_score += len(matches) * 1.5
                factual_words.extend(matches)
        
        # Check ALL CAPS
        all_caps = re.findall(r'\b[A-Z]{4,}\b', text)
        if all_caps:
            sensational_score += len(all_caps) * 2
            sensational_words.extend([w.lower() for w in all_caps])
        
        # Check punctuation
        exclamation_count = text.count('!')
        question_count = text.count('?')
        
        if exclamation_count > 1:
            sensational_score += exclamation_count
            sensational_words.append('multiple !!!')
        
        if question_count > 2:
            sensational_score += question_count // 2
            sensational_words.append('multiple ???')
        
        # Calculate sentiment
        total = sensational_score + factual_score
        if total == 0:
            sentiment_score = 0
            sentiment_label = 'Neutral'
        else:
            sentiment_score = (factual_score - sensational_score) / (total)
            if sentiment_score > 0.3:
                sentiment_label = 'Positive (Factual)'
            elif sentiment_score < -0.3:
                sentiment_label = 'Negative (Sensational)'
            else:
                sentiment_label = 'Neutral (Balanced)'
        
        return {
            'sentiment': sentiment_label,
            'sentiment_score': round(sentiment_score, 2),
            'sensational_score': sensational_score,
            'factual_score': factual_score,
            'sensational_words': list(set(sensational_words))[:5],
            'factual_words': list(set(factual_words))[:5]
        }

# Initialize components
verifier = NewsVerifier()
news_api = NewsAPIIntegration()
sentiment_analyzer = SentimentAnalyzer()

@app.route('/')
def serve_frontend():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/api/verify', methods=['POST'])
def verify_news():
    """Main endpoint to verify news"""
    try:
        data = request.json
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Get ML model prediction
        ml_prediction = verifier.predict(text)
        
        # Get sentiment analysis
        sentiment = sentiment_analyzer.analyze(text)
        
        # Get multi-source verification
        sources = news_api.verify_with_multiple_sources(text)
        
        # Calculate final verdict based on multiple factors
        final_verdict = calculate_final_verdict(ml_prediction, sentiment, sources)
        
        response = {
            'success': True,
            'input_text': text[:200] + '...' if len(text) > 200 else text,
            'ml_prediction': ml_prediction,
            'sentiment_analysis': sentiment,
            'source_verification': sources,
            'final_verdict': final_verdict,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def calculate_final_verdict(ml_prediction, sentiment, sources):
    """Calculate final verdict combining all analyses"""
    
    # Start with ML prediction
    is_fake = ml_prediction['is_fake']
    confidence = ml_prediction['confidence']
    
    # Adjust based on sentiment
    if sentiment['sentiment_score'] < -0.5:
        confidence = min(98, confidence + 5)
        is_fake = True
    elif sentiment['sentiment_score'] > 0.5 and not is_fake:
        confidence = min(98, confidence + 3)
    
    # Adjust based on source verification
    trusted_count = len(sources['trusted_sources'])
    contradictory_count = len(sources['contradictory_sources'])
    fact_check_count = len(sources['fact_checks'])
    
    # If multiple trusted sources found, lean towards real
    if trusted_count >= 3:
        confidence = min(98, confidence + 10)
        is_fake = False
    # If multiple suspicious sources found, lean towards fake
    elif contradictory_count >= 2:
        confidence = min(98, confidence + 8)
        is_fake = True
    
    # Check fact checks
    for fact_check in sources['fact_checks']:
        rating = fact_check.get('rating', '').lower()
        if 'false' in rating or 'fake' in rating:
            confidence = min(98, confidence + 15)
            is_fake = True
        elif 'true' in rating:
            confidence = min(98, confidence + 10)
            is_fake = False
    
    return {
        'is_fake': is_fake,
        'confidence': round(confidence, 2),
        'explanation': generate_explanation(ml_prediction, sentiment, sources, is_fake)
    }

def generate_explanation(ml_prediction, sentiment, sources, is_fake):
    """Generate human-readable explanation"""
    explanation_parts = []
    
    if is_fake:
        if sentiment['sensational_score'] > 10:
            explanation_parts.append("The text contains highly sensational language")
        if sources['contradictory_sources']:
            explanation_parts.append("Found contradictory information from suspicious sources")
        if ml_prediction['fake_probability'] > 80:
            explanation_parts.append("ML model indicates strong fake news patterns")
    else:
        if sentiment['factual_score'] > 5:
            explanation_parts.append("The text uses factual, journalistic language")
        if sources['trusted_sources']:
            explanation_parts.append(f"Found {len(sources['trusted_sources'])} articles from trusted sources")
        if sources['fact_checks']:
            explanation_parts.append("Verified by independent fact-checkers")
    
    if not explanation_parts:
        explanation_parts.append("Analysis based on linguistic patterns and available sources")
    
    return ' '.join(explanation_parts)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'model_loaded': verifier.model is not None
    })

@app.route('/api/sources', methods=['GET'])
def get_sources():
    """Get list of trusted sources"""
    return jsonify({
        'trusted_sources': TRUSTED_SOURCES,
        'suspicious_sources': SUSPICIOUS_SOURCES
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)