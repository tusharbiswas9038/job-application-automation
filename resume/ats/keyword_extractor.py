# resume/ats/keyword_extractor.py
import re
import logging
from typing import List, Set, Dict, Tuple
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import PorterStemmer, WordNetLemmatizer

from resume.ats.models import Keyword, KeywordCategory

logger = logging.getLogger(__name__)

# Download required NLTK data (run once)
def _ensure_nltk_data():
    """Ensure all required NLTK data is downloaded"""
    required_data = [
        ('tokenizers/punkt', 'punkt'),
        ('tokenizers/punkt_tab', 'punkt_tab'),
        ('corpora/stopwords', 'stopwords'),
        ('corpora/wordnet', 'wordnet'),
    ]
    
    for path, package in required_data:
        try:
            nltk.data.find(path)
        except LookupError:
            logger.info(f"Downloading NLTK data: {package}")
            nltk.download(package, quiet=True)

# Call on module import
_ensure_nltk_data()

class KeywordExtractor:
    """
    Extract keywords from job descriptions using NLP techniques
    """
    
    # Common technical skill patterns
    TECH_PATTERNS = {
        'kafka': r'\b(?:kafka|apache\s+kafka|confluent)\b',
        'kubernetes': r'\bk8s\b|\bkubernetes\b',
        'docker': r'\bdocker\b|\bcontainerization\b',
        'python': r'\bpython\b|\bpython3\b',
        'java': r'\bjava\b(?!\s*script)',
        'aws': r'\baws\b|\bamazon\s+web\s+services\b',
        'azure': r'\bazure\b|\bmicrosoft\s+azure\b',
        'terraform': r'\bterraform\b|\biac\b|\binfrastructure\s+as\s+code\b',
        'ansible': r'\bansible\b',
        'jenkins': r'\bjenkins\b|\bci/cd\b',
        'git': r'\bgit\b|\bgithub\b|\bgitlab\b',
    }
    
    # Skill synonyms and variations
    SYNONYMS = {
        'kafka': ['apache kafka', 'confluent kafka', 'kafka streams'],
        'kubernetes': ['k8s', 'container orchestration'],
        'ci/cd': ['continuous integration', 'continuous deployment', 'jenkins', 'gitlab ci'],
        'monitoring': ['observability', 'telemetry', 'alerting', 'grafana', 'prometheus'],
        'scripting': ['automation', 'bash', 'shell', 'python scripting'],
        'cloud': ['aws', 'azure', 'gcp', 'cloud computing'],
    }
    
    # Certifications
    CERTIFICATIONS = [
        'aws certified', 'azure certified', 'cka', 'ckad',
        'confluent certified', 'kafka certification',
        'terraform certified', 'ansible certified'
    ]
    
    def __init__(self):
        self.stemmer = PorterStemmer()
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
        # Add technical terms that shouldn't be filtered
        self.stop_words -= {'not', 'no', 'more', 'most', 'should', 'must'}
    
    def extract_keywords(
        self,
        job_description: str,
        top_n: int = 50
    ) -> List[Keyword]:
        """
        Extract ranked keywords from job description
        
        Args:
            job_description: Full JD text
            top_n: Maximum keywords to return
        
        Returns:
            List of Keyword objects ranked by importance
        """
        logger.info("Extracting keywords from job description")
        
        keywords = []
        
        # 1. Extract technical skills (highest priority)
        tech_keywords = self._extract_technical_skills(job_description)
        keywords.extend(tech_keywords)
        
        # 2. Extract certifications
        cert_keywords = self._extract_certifications(job_description)
        keywords.extend(cert_keywords)
        
        # 3. Extract key phrases (n-grams)
        phrase_keywords = self._extract_key_phrases(job_description, n=3)
        keywords.extend(phrase_keywords)
        
        # 4. Extract domain terms
        domain_keywords = self._extract_domain_terms(job_description)
        keywords.extend(domain_keywords)
        
        # 5. Extract soft skills
        soft_keywords = self._extract_soft_skills(job_description)
        keywords.extend(soft_keywords)
        
        # Deduplicate and rank
        keywords = self._deduplicate_and_rank(keywords, top_n)
        
        logger.info(f"Extracted {len(keywords)} unique keywords")
        return keywords
    
    def _extract_technical_skills(self, text: str) -> List[Keyword]:
        """Extract technical skills using patterns"""
        keywords = []
        text_lower = text.lower()
        
        for skill, pattern in self.TECH_PATTERNS.items():
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                # Get context (20 chars before and after)
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                context = text[start:end]
                
                # Determine importance based on context
                importance = self._calculate_importance(text, match.group(0))
                
                keyword = Keyword(
                    text=skill,
                    category=KeywordCategory.TECHNICAL,
                    importance=importance,
                    synonyms=self.SYNONYMS.get(skill, []),
                    context=context
                )
                keywords.append(keyword)
        
        return keywords
    
    def _extract_certifications(self, text: str) -> List[Keyword]:
        """Extract certification requirements"""
        keywords = []
        text_lower = text.lower()
        
        for cert in self.CERTIFICATIONS:
            if cert in text_lower:
                keyword = Keyword(
                    text=cert.title(),
                    category=KeywordCategory.CERTIFICATION,
                    importance=0.9,  # Certifications are usually important
                    synonyms=[],
                    context=None
                )
                keywords.append(keyword)
        
        return keywords
    
    def _extract_key_phrases(self, text: str, n: int = 3) -> List[Keyword]:
        """
        Extract key n-gram phrases
        
        Args:
            text: Input text
            n: Maximum n-gram length
        
        Returns:
            List of Keyword objects
        """
        keywords = []
        
        # Tokenize into sentences
        sentences = sent_tokenize(text.lower())
        
        # Extract n-grams from each sentence
        all_ngrams = []
        for sentence in sentences:
            words = word_tokenize(sentence)
            # Filter stopwords but keep technical terms
            words = [w for w in words if w.isalnum() and len(w) > 2]
            
            # Generate n-grams
            for i in range(2, n + 1):
                for j in range(len(words) - i + 1):
                    ngram = ' '.join(words[j:j + i])
                    all_ngrams.append(ngram)
        
        # Count frequency
        ngram_counts = Counter(all_ngrams)
        
        # Convert top n-grams to keywords
        for phrase, count in ngram_counts.most_common(20):
            if count >= 2:  # Must appear at least twice
                # Categorize based on content
                category = self._categorize_phrase(phrase)
                
                keyword = Keyword(
                    text=phrase,
                    category=category,
                    importance=min(count / 5.0, 1.0),  # Normalize frequency
                    synonyms=[],
                    context=None
                )
                keywords.append(keyword)
        
        return keywords
    
    def _extract_domain_terms(self, text: str) -> List[Keyword]:
        """Extract domain-specific terminology"""
        # Domain patterns for Kafka/DevOps
        domain_patterns = {
            'cluster management': r'\bcluster\s+(?:management|administration|scaling)\b',
            'high availability': r'\bhigh\s+availability\b|\bha\b',
            'disaster recovery': r'\bdisaster\s+recovery\b|\bdr\b|\bbackup\b',
            'performance tuning': r'\bperformance\s+(?:tuning|optimization)\b',
            'security': r'\bsecurity\b|\bssl/tls\b|\bencryption\b|\bsasl\b',
            'monitoring': r'\bmonitoring\b|\bobservability\b|\bmetrics\b',
            'replication': r'\breplication\b|\bdata\s+replication\b',
            'partitioning': r'\bpartition(?:ing|s)?\b',
            'throughput': r'\bthroughput\b|\blatency\b',
        }
        
        keywords = []
        text_lower = text.lower()
        
        for term, pattern in domain_patterns.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                keyword = Keyword(
                    text=term,
                    category=KeywordCategory.DOMAIN,
                    importance=0.8,
                    synonyms=[],
                    context=None
                )
                keywords.append(keyword)
        
        return keywords
    
    def _extract_soft_skills(self, text: str) -> List[Keyword]:
        """Extract soft skills and behavioral traits"""
        soft_skills = [
            'collaboration', 'communication', 'leadership', 'problem solving',
            'analytical', 'troubleshooting', 'teamwork', 'mentoring',
            'documentation', 'agile', 'scrum'
        ]
        
        keywords = []
        text_lower = text.lower()
        
        for skill in soft_skills:
            if skill in text_lower:
                keyword = Keyword(
                    text=skill.title(),
                    category=KeywordCategory.SOFT_SKILL,
                    importance=0.5,  # Lower priority than technical
                    synonyms=[],
                    context=None
                )
                keywords.append(keyword)
        
        return keywords
    
    def _calculate_importance(self, full_text: str, keyword: str) -> float:
        """
        Calculate keyword importance based on context
        
        Factors:
        - Appears in requirements section: +0.3
        - Appears in title: +0.2
        - Preceded by "required", "must": +0.2
        - Frequency: +0.1 per occurrence (max +0.3)
        """
        importance = 0.5  # Base importance
        text_lower = full_text.lower()
        keyword_lower = keyword.lower()
        
        # Check if in requirements section
        if re.search(r'(?:requirements?|qualifications?).*?' + re.escape(keyword_lower), 
                    text_lower, re.DOTALL):
            importance += 0.3
        
        # Check if in title or first paragraph
        first_para = text_lower[:min(500, len(text_lower))]
        if keyword_lower in first_para:
            importance += 0.2
        
        # Check for emphasis words nearby
        emphasis_pattern = r'\b(?:required|must|essential|critical|key)\b.{0,50}' + re.escape(keyword_lower)
        if re.search(emphasis_pattern, text_lower):
            importance += 0.2
        
        # Frequency bonus
        frequency = text_lower.count(keyword_lower)
        importance += min(frequency * 0.1, 0.3)
        
        return min(importance, 1.0)
    
    def _categorize_phrase(self, phrase: str) -> KeywordCategory:
        """Categorize a phrase into keyword category"""
        phrase_lower = phrase.lower()
        
        # Technical indicators
        tech_indicators = ['system', 'cluster', 'server', 'data', 'api', 'infrastructure']
        if any(ind in phrase_lower for ind in tech_indicators):
            return KeywordCategory.TECHNICAL
        
        # Experience indicators
        exp_indicators = ['experience', 'years', 'background', 'expertise']
        if any(ind in phrase_lower for ind in exp_indicators):
            return KeywordCategory.EXPERIENCE
        
        # Default to domain
        return KeywordCategory.DOMAIN
    
    def _deduplicate_and_rank(
        self,
        keywords: List[Keyword],
        top_n: int
    ) -> List[Keyword]:
        """
        Remove duplicates and rank keywords by importance
        """
        # Group by normalized text
        unique_keywords = {}
        
        for kw in keywords:
            key = kw.text.lower().strip()
            
            if key in unique_keywords:
                # Keep the one with higher importance
                if kw.importance > unique_keywords[key].importance:
                    unique_keywords[key] = kw
            else:
                unique_keywords[key] = kw
        
        # Sort by importance and category priority
        category_priority = {
            KeywordCategory.REQUIRED: 5,
            KeywordCategory.TECHNICAL: 4,
            KeywordCategory.CERTIFICATION: 4,
            KeywordCategory.DOMAIN: 3,
            KeywordCategory.TOOL: 3,
            KeywordCategory.EXPERIENCE: 2,
            KeywordCategory.SOFT_SKILL: 1,
        }
        
        sorted_keywords = sorted(
            unique_keywords.values(),
            key=lambda k: (category_priority.get(k.category, 0), k.importance),
            reverse=True
        )
        
        return sorted_keywords[:top_n]

