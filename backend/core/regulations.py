"""
LawVisor Regulations Module
===========================
Fetches, caches, and normalizes regulatory data from live sources.
Supports GDPR articles and SEC compliance rules.

Features:
- Real-time regulatory data fetching
- Intelligent caching with TTL
- Regulatory text normalization
- Structured regulatory representation
"""

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import aiohttp
from diskcache import Cache

from core.config import REGULATORY_SOURCES, get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RegulationType(str, Enum):
    """Types of regulations supported."""
    GDPR = "gdpr"
    SEC = "sec"
    CCPA = "ccpa"  # Future support
    HIPAA = "hipaa"  # Future support


@dataclass
class RegulationArticle:
    """A single regulatory article or rule."""
    regulation_id: str
    regulation_type: RegulationType
    article_number: str
    title: str
    full_text: str
    summary: str
    key_requirements: list[str]
    penalties: list[str]
    last_updated: datetime
    source_url: str
    related_articles: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "regulation_id": self.regulation_id,
            "regulation_type": self.regulation_type.value,
            "article_number": self.article_number,
            "title": self.title,
            "full_text": self.full_text,
            "summary": self.summary,
            "key_requirements": self.key_requirements,
            "penalties": self.penalties,
            "last_updated": self.last_updated.isoformat(),
            "source_url": self.source_url,
            "related_articles": self.related_articles
        }


@dataclass
class RegulationSet:
    """A collection of related regulations."""
    regulation_type: RegulationType
    name: str
    articles: list[RegulationArticle]
    fetched_at: datetime
    version: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "regulation_type": self.regulation_type.value,
            "name": self.name,
            "articles": [a.to_dict() for a in self.articles],
            "fetched_at": self.fetched_at.isoformat(),
            "version": self.version
        }


# Pre-defined GDPR articles with key compliance information
# This is structured regulatory data - not hardcoded conclusions
GDPR_ARTICLES_DATA = {
    "5": {
        "title": "Principles relating to processing of personal data",
        "subsections": {
            "1a": "Lawfulness, fairness and transparency",
            "1b": "Purpose limitation",
            "1c": "Data minimisation",
            "1d": "Accuracy",
            "1e": "Storage limitation",
            "1f": "Integrity and confidentiality",
            "2": "Accountability"
        },
        "key_requirements": [
            "Personal data must be processed lawfully, fairly, and transparently",
            "Data must be collected for specified, explicit, and legitimate purposes",
            "Data must be adequate, relevant, and limited to what is necessary",
            "Data must be accurate and kept up to date",
            "Data must be kept for no longer than necessary",
            "Data must be processed securely"
        ],
        "penalties": ["Up to €20 million or 4% of annual global turnover"]
    },
    "6": {
        "title": "Lawfulness of processing",
        "subsections": {
            "1a": "Consent",
            "1b": "Contract performance",
            "1c": "Legal obligation",
            "1d": "Vital interests",
            "1e": "Public task",
            "1f": "Legitimate interests"
        },
        "key_requirements": [
            "Processing requires a lawful basis",
            "Consent must be freely given, specific, informed, and unambiguous",
            "Processing must be necessary for stated purpose"
        ],
        "penalties": ["Up to €20 million or 4% of annual global turnover"]
    },
    "7": {
        "title": "Conditions for consent",
        "key_requirements": [
            "Controller must demonstrate consent was given",
            "Consent request must be distinguishable and in clear language",
            "Consent can be withdrawn at any time",
            "Withdrawal must be as easy as giving consent"
        ],
        "penalties": ["Up to €20 million or 4% of annual global turnover"]
    },
    "12": {
        "title": "Transparent information, communication and modalities",
        "key_requirements": [
            "Information must be provided in concise, transparent, intelligible form",
            "Information must be in clear and plain language",
            "Response to data subject requests within one month"
        ],
        "penalties": ["Up to €20 million or 4% of annual global turnover"]
    },
    "13": {
        "title": "Information to be provided where data collected from data subject",
        "key_requirements": [
            "Identity and contact details of controller",
            "Purposes and legal basis for processing",
            "Recipients of personal data",
            "Details of international transfers",
            "Data retention period"
        ],
        "penalties": ["Up to €20 million or 4% of annual global turnover"]
    },
    "17": {
        "title": "Right to erasure ('right to be forgotten')",
        "key_requirements": [
            "Right to obtain erasure without undue delay",
            "Applies when data no longer necessary for purpose",
            "Applies when consent withdrawn",
            "Applies when data unlawfully processed"
        ],
        "penalties": ["Up to €20 million or 4% of annual global turnover"]
    },
    "25": {
        "title": "Data protection by design and by default",
        "key_requirements": [
            "Implement appropriate technical measures",
            "Implement appropriate organisational measures",
            "Ensure only necessary data is processed by default"
        ],
        "penalties": ["Up to €10 million or 2% of annual global turnover"]
    },
    "28": {
        "title": "Processor",
        "key_requirements": [
            "Use only processors with sufficient guarantees",
            "Processing governed by contract or legal act",
            "Processor must not engage sub-processor without authorization"
        ],
        "penalties": ["Up to €10 million or 2% of annual global turnover"]
    },
    "32": {
        "title": "Security of processing",
        "key_requirements": [
            "Implement appropriate technical measures",
            "Implement appropriate organisational measures",
            "Include pseudonymisation and encryption",
            "Ensure ongoing confidentiality, integrity, availability"
        ],
        "penalties": ["Up to €10 million or 2% of annual global turnover"]
    },
    "33": {
        "title": "Notification of a personal data breach",
        "key_requirements": [
            "Notify supervisory authority within 72 hours",
            "Describe nature of breach",
            "Describe likely consequences",
            "Describe measures taken"
        ],
        "penalties": ["Up to €10 million or 2% of annual global turnover"]
    },
    "44": {
        "title": "General principle for transfers",
        "key_requirements": [
            "Transfers to third countries only with adequate safeguards",
            "Level of protection must not be undermined"
        ],
        "penalties": ["Up to €20 million or 4% of annual global turnover"]
    },
    "46": {
        "title": "Transfers subject to appropriate safeguards",
        "key_requirements": [
            "Standard contractual clauses",
            "Binding corporate rules",
            "Approved codes of conduct",
            "Approved certification mechanisms"
        ],
        "penalties": ["Up to €20 million or 4% of annual global turnover"]
    }
}

# Pre-defined SEC regulations
SEC_REGULATIONS_DATA = {
    "10b-5": {
        "title": "Employment of Manipulative and Deceptive Devices",
        "key_requirements": [
            "Prohibition on fraud in connection with securities",
            "Prohibition on making untrue statements of material fact",
            "Prohibition on omitting material facts"
        ],
        "source": "Securities Exchange Act of 1934"
    },
    "FD": {
        "title": "Regulation Fair Disclosure",
        "key_requirements": [
            "Simultaneous public disclosure of material nonpublic information",
            "Applies to communications with market professionals and shareholders",
            "24-hour cure period for unintentional selective disclosure"
        ],
        "source": "17 CFR 243"
    },
    "S-K": {
        "title": "Standard Instructions for Filing Forms",
        "key_requirements": [
            "Disclosure of business description",
            "Risk factor disclosure",
            "Management's discussion and analysis",
            "Executive compensation disclosure"
        ],
        "source": "17 CFR 229"
    },
    "13D": {
        "title": "Beneficial Ownership Reporting",
        "key_requirements": [
            "Report within 10 days of acquiring 5% or more",
            "Disclose identity, source of funds, purpose",
            "Promptly amend for material changes"
        ],
        "source": "Securities Exchange Act Section 13(d)"
    }
}


class RegulationsFetcher:
    """
    Fetches and manages regulatory data from official sources.
    
    Features:
    - Live fetching from regulatory websites
    - Intelligent caching with configurable TTL
    - Fallback to pre-defined data when live fetch fails
    - Normalized output for downstream processing
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._cache = Cache(str(Path("./cache/regulations")))
        self._cache_ttl = timedelta(hours=24)  # Cache for 24 hours
        self._session: aiohttp.ClientSession | None = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "User-Agent": "LawVisor/1.0 Legal Compliance Analyzer"
                }
            )
        return self._session
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def fetch_gdpr_article(
        self, 
        article_number: str
    ) -> RegulationArticle | None:
        """
        Fetch a specific GDPR article.
        
        Args:
            article_number: Article number (e.g., "5", "17", "25")
            
        Returns:
            RegulationArticle if found, None otherwise
        """
        cache_key = f"gdpr_article_{article_number}"
        
        # Check cache first
        cached = self._get_cached(cache_key)
        if cached:
            logger.debug(f"Cache hit for GDPR Article {article_number}")
            return cached
        
        # Try to fetch live data
        try:
            article = await self._fetch_gdpr_live(article_number)
            if article:
                self._set_cached(cache_key, article)
                return article
        except Exception as e:
            logger.warning(f"Live GDPR fetch failed: {e}")
        
        # Fallback to pre-defined data
        article = self._get_gdpr_predefined(article_number)
        if article:
            self._set_cached(cache_key, article)
        
        return article
    
    async def _fetch_gdpr_live(
        self, 
        article_number: str
    ) -> RegulationArticle | None:
        """Fetch GDPR article from gdpr-info.eu."""
        url = f"https://gdpr-info.eu/art-{article_number}-gdpr/"
        
        session = await self._get_session()
        
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                
                # Parse the article content
                article = self._parse_gdpr_html(html, article_number, url)
                return article
                
        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch GDPR article {article_number}: {e}")
            return None
    
    def _parse_gdpr_html(
        self, 
        html: str, 
        article_number: str,
        source_url: str
    ) -> RegulationArticle | None:
        """Parse GDPR article from HTML content."""
        # Extract title
        title_match = re.search(
            r'<h1[^>]*>Art\.\s*\d+\s*GDPR\s*[–-]\s*([^<]+)</h1>', 
            html
        )
        title = title_match.group(1).strip() if title_match else f"Article {article_number}"
        
        # Extract article text
        text_match = re.search(
            r'<div class="entry-content"[^>]*>(.*?)</div>', 
            html, 
            re.DOTALL
        )
        
        if not text_match:
            return None
        
        raw_text = text_match.group(1)
        # Clean HTML tags
        full_text = re.sub(r'<[^>]+>', '', raw_text)
        full_text = re.sub(r'\s+', ' ', full_text).strip()
        
        # Get additional data from predefined if available
        predefined = GDPR_ARTICLES_DATA.get(article_number, {})
        
        return RegulationArticle(
            regulation_id=f"GDPR-Art-{article_number}",
            regulation_type=RegulationType.GDPR,
            article_number=article_number,
            title=title,
            full_text=full_text,
            summary=self._generate_summary(full_text),
            key_requirements=predefined.get("key_requirements", []),
            penalties=predefined.get("penalties", []),
            last_updated=datetime.utcnow(),
            source_url=source_url,
            related_articles=[]
        )
    
    def _get_gdpr_predefined(
        self, 
        article_number: str
    ) -> RegulationArticle | None:
        """Get GDPR article from pre-defined data."""
        data = GDPR_ARTICLES_DATA.get(article_number)
        
        if not data:
            return None
        
        # Construct full text from subsections if available
        full_text_parts = [data["title"]]
        if "subsections" in data:
            for key, value in data["subsections"].items():
                full_text_parts.append(f"({key}) {value}")
        
        return RegulationArticle(
            regulation_id=f"GDPR-Art-{article_number}",
            regulation_type=RegulationType.GDPR,
            article_number=article_number,
            title=data["title"],
            full_text=" ".join(full_text_parts),
            summary=data["title"],
            key_requirements=data.get("key_requirements", []),
            penalties=data.get("penalties", []),
            last_updated=datetime.utcnow(),
            source_url=f"https://gdpr-info.eu/art-{article_number}-gdpr/",
            related_articles=[]
        )
    
    async def fetch_sec_regulation(
        self, 
        regulation_id: str
    ) -> RegulationArticle | None:
        """
        Fetch a specific SEC regulation.
        
        Args:
            regulation_id: Regulation identifier (e.g., "10b-5", "FD", "S-K")
            
        Returns:
            RegulationArticle if found, None otherwise
        """
        cache_key = f"sec_regulation_{regulation_id}"
        
        # Check cache first
        cached = self._get_cached(cache_key)
        if cached:
            logger.debug(f"Cache hit for SEC Regulation {regulation_id}")
            return cached
        
        # Use pre-defined SEC data (SEC website requires special access)
        article = self._get_sec_predefined(regulation_id)
        if article:
            self._set_cached(cache_key, article)
        
        return article
    
    def _get_sec_predefined(
        self, 
        regulation_id: str
    ) -> RegulationArticle | None:
        """Get SEC regulation from pre-defined data."""
        data = SEC_REGULATIONS_DATA.get(regulation_id)
        
        if not data:
            return None
        
        full_text = f"{data['title']}. "
        full_text += ". ".join(data["key_requirements"])
        
        return RegulationArticle(
            regulation_id=f"SEC-{regulation_id}",
            regulation_type=RegulationType.SEC,
            article_number=regulation_id,
            title=data["title"],
            full_text=full_text,
            summary=data["title"],
            key_requirements=data["key_requirements"],
            penalties=[],  # SEC penalties are case-specific
            last_updated=datetime.utcnow(),
            source_url=f"https://www.sec.gov/rules/{regulation_id.lower()}",
            related_articles=[]
        )
    
    async def fetch_all_gdpr_articles(self) -> RegulationSet:
        """Fetch all key GDPR articles."""
        articles = []
        
        for article_num in GDPR_ARTICLES_DATA.keys():
            article = await self.fetch_gdpr_article(article_num)
            if article:
                articles.append(article)
        
        return RegulationSet(
            regulation_type=RegulationType.GDPR,
            name="General Data Protection Regulation",
            articles=articles,
            fetched_at=datetime.utcnow(),
            version="2016/679"
        )
    
    async def fetch_all_sec_regulations(self) -> RegulationSet:
        """Fetch all key SEC regulations."""
        articles = []
        
        for reg_id in SEC_REGULATIONS_DATA.keys():
            article = await self.fetch_sec_regulation(reg_id)
            if article:
                articles.append(article)
        
        return RegulationSet(
            regulation_type=RegulationType.SEC,
            name="SEC Regulations",
            articles=articles,
            fetched_at=datetime.utcnow(),
            version="Current"
        )
    
    async def get_relevant_regulations(
        self, 
        clause_type: str
    ) -> list[RegulationArticle]:
        """
        Get regulations relevant to a specific clause type.
        
        Maps clause types to relevant regulatory articles.
        """
        # Mapping of clause types to relevant regulations
        relevance_map = {
            "data_protection": [
                ("gdpr", ["5", "6", "7", "12", "13", "25", "32"]),
            ],
            "liability": [
                ("sec", ["10b-5"]),
            ],
            "confidentiality": [
                ("gdpr", ["5", "32"]),
            ],
            "intellectual_property": [
                ("gdpr", ["5"]),
            ],
            "jurisdiction": [
                ("gdpr", ["44", "46"]),
            ],
            "termination": [
                ("gdpr", ["17"]),
            ],
            "indemnification": [
                ("sec", ["10b-5"]),
            ],
        }
        
        regulations = []
        mappings = relevance_map.get(clause_type, [])
        
        for reg_type, article_ids in mappings:
            for article_id in article_ids:
                if reg_type == "gdpr":
                    article = await self.fetch_gdpr_article(article_id)
                elif reg_type == "sec":
                    article = await self.fetch_sec_regulation(article_id)
                else:
                    continue
                
                if article:
                    regulations.append(article)
        
        return regulations
    
    def _get_cached(self, key: str) -> RegulationArticle | None:
        """Get item from cache if not expired."""
        try:
            cached_data = self._cache.get(key)
            if cached_data:
                # Check TTL
                cached_at = cached_data.get("cached_at")
                if cached_at:
                    cached_time = datetime.fromisoformat(cached_at)
                    if datetime.utcnow() - cached_time < self._cache_ttl:
                        return self._dict_to_article(cached_data["article"])
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None
    
    def _set_cached(self, key: str, article: RegulationArticle):
        """Set item in cache."""
        try:
            self._cache.set(key, {
                "cached_at": datetime.utcnow().isoformat(),
                "article": article.to_dict()
            })
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    def _dict_to_article(self, data: dict) -> RegulationArticle:
        """Convert dictionary back to RegulationArticle."""
        return RegulationArticle(
            regulation_id=data["regulation_id"],
            regulation_type=RegulationType(data["regulation_type"]),
            article_number=data["article_number"],
            title=data["title"],
            full_text=data["full_text"],
            summary=data["summary"],
            key_requirements=data["key_requirements"],
            penalties=data["penalties"],
            last_updated=datetime.fromisoformat(data["last_updated"]),
            source_url=data["source_url"],
            related_articles=data.get("related_articles", [])
        )
    
    def _generate_summary(self, text: str, max_length: int = 200) -> str:
        """Generate a summary from full text."""
        # Simple extraction of first sentences
        sentences = text.split('.')
        summary = ""
        for sentence in sentences:
            if len(summary) + len(sentence) < max_length:
                summary += sentence.strip() + ". "
            else:
                break
        return summary.strip()


# Singleton instance
_regulations_fetcher: RegulationsFetcher | None = None


def get_regulations_fetcher() -> RegulationsFetcher:
    """Get singleton RegulationsFetcher instance."""
    global _regulations_fetcher
    if _regulations_fetcher is None:
        _regulations_fetcher = RegulationsFetcher()
    return _regulations_fetcher
