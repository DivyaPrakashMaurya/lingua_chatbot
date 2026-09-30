import re
from threading import Lock
from langdetect import detect, DetectorFactory, LangDetectException
from app.core.config import settings

DetectorFactory.seed = 0
LANGUAGES = {'auto':'Auto-detect', 'en':'English', 'hi':'Hindi', 'es':'Spanish', 'fr':'French', 'de':'German', 'ar':'Arabic', 'zh-cn':'Chinese', 'ja':'Japanese', 'pt':'Portuguese', 'bn':'Bengali', 'ta':'Tamil'}
LABELS = ['greeting', 'translation', 'summarization', 'writing assistance', 'coding help', 'explanation', 'planning', 'general conversation']
GUIDANCE = {
    'translation': 'Translate accurately, preserving tone. Ask for the target language if absent.',
    'summarization': 'Summarize the supplied or previous content faithfully. Do not invent source content.',
    'coding help': 'Give practical code and explain assumptions. Ask for missing code when needed.',
    'planning': 'Offer an actionable, organized plan that follows the stated constraints.',
    'writing assistance': 'Help draft or refine the requested text and preserve the intended voice.',
}

class NLPService:
    def __init__(self):
        self.classifier = None
        self.lock = Lock()

    def language(self, text):
        if re.search('[\u0900-\u097f]', text):
            return 'hi'
        try:
            return detect(text) if len(text.split()) >= 3 else 'und'
        except LangDetectException:
            return 'und'

    def classify(self, text, history):
        if settings.intent_mode == 'transformer':
            with self.lock:
                if self.classifier is None:
                    from transformers import pipeline
                    self.classifier = pipeline('zero-shot-classification', model=settings.intent_model, device=-1)
                # Include prior turns to resolve short follow-ups such as "make it shorter".
                context = '\n'.join(f"{m['role']}: {m['content'][:400]}" for m in history[-2:])
                result = self.classifier(f'{context}\nCurrent user request: {text}', LABELS, hypothesis_template='The user requests {}.')
                index = 0
                score = float(result['scores'][index])
                label = result['labels'][index] if score >= .30 else 'general conversation'
                return {'label': label, 'confidence': round(score, 3), 'engine':'transformer'}
        patterns = {
            'translation': r'translat|अनुवाद|traduc|traduire|übersetz',
            'summarization': r'summari|summary|shorter|résum|सारांश|resum',
            'coding help': r'python|code|debug|javascript|fastapi|कोड',
            'writing assistance': r'write|draft|email|लिख|escribe|écri',
            'planning': r'plan|itinerary|योजना|organize',
            'greeting': r'^(hi|hello|hey|नमस्ते|hola|bonjour|hallo|مرحبا)[!.\s]*$',
            'explanation': r'explain|what is|how does|समझा|explica',
        }
        label = next((label for label, pattern in patterns.items() if re.search(pattern, text, re.I)), 'general conversation')
        return {'label':label, 'confidence':None, 'engine':'demo rules'}

nlp = NLPService()
