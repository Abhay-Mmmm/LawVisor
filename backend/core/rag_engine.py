"""
LawVisor RAG Engine Module
==========================
Retrieval-Augmented Generation for legal clause analysis.
Combines vector search with LLM reasoning for compliance checking.

Key Features:
- Semantic search across regulatory corpus
- Multi-source retrieval (GDPR, SEC, etc.)
- Contextual compliance analysis
- Explainable reasoning chains
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from openai import AsyncOpenAI
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

from core.clause_extractor import ClauseType, ExtractedClause
from core.config import get_settings
from core.regulations import (
    RegulationArticle,
    RegulationsFetcher,
    get_regulations_fetcher,
)

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class RetrievedContext:
    """Context retrieved from vector search."""
    regulation_id: str
    article_number: str
    title: str
    text: str
    relevance_score: float
    source_url: str
    regulation_type: str


@dataclass
class ComplianceAnalysis:
    """Analysis result for a single clause against regulations."""
    clause_id: str
    clause_type: str
    clause_text: str
    is_compliant: bool
    risk_level: str
    risk_score: float
    violated_regulations: list[str]
    matched_regulations: list[RetrievedContext]
    explanation: str
    reasoning_chain: list[str]
    recommendations: list[str]
    confidence: float
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "clause_id": self.clause_id,
            "clause_type": self.clause_type,
            "clause_text": self.clause_text,
            "is_compliant": self.is_compliant,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "violated_regulations": self.violated_regulations,
            "matched_regulations": [
                {
                    "regulation_id": r.regulation_id,
                    "article_number": r.article_number,
                    "title": r.title,
                    "relevance_score": r.relevance_score,
                    "source_url": r.source_url
                }
                for r in self.matched_regulations
            ],
            "explanation": self.explanation,
            "reasoning_chain": self.reasoning_chain,
            "recommendations": self.recommendations,
            "confidence": self.confidence
        }


# System prompt for compliance analysis
COMPLIANCE_ANALYSIS_PROMPT = """You are a legal compliance expert AI. Your task is to analyze a contract clause against relevant regulations and determine compliance.

IMPORTANT RULES:
1. NEVER make up or hallucinate regulations - only reference regulations provided in the context
2. Provide clear, step-by-step reasoning for your conclusions
3. Be specific about which parts of regulations are relevant
4. Assign risk levels based on actual regulatory requirements
5. All recommendations must be actionable and specific

RISK LEVELS:
- CRITICAL (80-100): Clear violation of mandatory requirements, significant penalties possible
- HIGH (60-79): Likely violation or significant gaps in compliance
- MEDIUM (40-59): Partial compliance, some requirements not fully addressed
- LOW (20-39): Minor gaps or ambiguities that should be clarified
- MINIMAL (0-19): Appears compliant with relevant regulations

For your analysis, provide:
1. Whether the clause is compliant (true/false)
2. The risk level (critical/high/medium/low/minimal)
3. A risk score (0-100)
4. List of potentially violated regulations (if any)
5. Your reasoning chain (step-by-step logic)
6. A clear explanation for non-technical stakeholders
7. Specific recommendations for improving compliance
8. Your confidence score (0-1) based on quality of evidence

Output as JSON:
{{
    "is_compliant": true/false,
    "risk_level": "medium",
    "risk_score": 45,
    "violated_regulations": ["GDPR Article 5(1)(c)"],
    "reasoning_chain": [
        "Step 1: ...",
        "Step 2: ..."
    ],
    "explanation": "Plain language explanation...",
    "recommendations": [
        "Specific recommendation 1",
        "Specific recommendation 2"
    ],
    "confidence": 0.85
}}"""


class RAGEngine:
    """
    Retrieval-Augmented Generation engine for legal compliance analysis.
    
    Architecture:
    1. Embed clause text
    2. Retrieve relevant regulations from vector DB
    3. Fetch full regulatory context
    4. Analyze compliance using LLM with retrieved context
    5. Generate explainable risk assessment
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._init_clients()
        self._regulations_fetcher = get_regulations_fetcher()
        self._pinecone_index = None
    
    def _init_clients(self):
        """Initialize LLM and embedding clients."""
        # OpenAI client for LLM with increased timeout
        self.llm_client = AsyncOpenAI(
            api_key=self.settings.openai_api_key,
            timeout=300.0  # 5 minutes per request
        )
        self.llm_model = self.settings.llm_model or "gpt-4o-mini"
        
        # Local embedding model (sentence-transformers)
        # Using all-MiniLM-L6-v2 which produces 384-dim embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def _get_pinecone_index(self):
        """Get or create Pinecone index."""
        if self._pinecone_index is None:
            pc = Pinecone(api_key=self.settings.pinecone_api_key)
            
            # Check if index exists
            index_name = self.settings.pinecone_index_name
            existing_indexes = pc.list_indexes()
            
            if index_name not in [idx.name for idx in existing_indexes]:
                # Create index if it doesn't exist
                # Using 384 dimensions for sentence-transformers all-MiniLM-L6-v2
                pc.create_index(
                    name=index_name,
                    dimension=384,
                    metric="cosine",
                    spec={
                        "serverless": {
                            "cloud": "aws",
                            "region": self.settings.pinecone_environment
                        }
                    }
                )
            
            self._pinecone_index = pc.Index(index_name)
        
        return self._pinecone_index
    
    async def analyze_clause(
        self, 
        clause: ExtractedClause
    ) -> ComplianceAnalysis:
        """
        Analyze a single clause for regulatory compliance.
        
        Args:
            clause: Extracted clause to analyze
            
        Returns:
            ComplianceAnalysis with full risk assessment
        """
        logger.info(f"Analyzing clause {clause.clause_id} of type {clause.clause_type}")
        
        # Step 1: Get relevant regulations based on clause type
        regulations = await self._regulations_fetcher.get_relevant_regulations(
            clause.clause_type.value
        )
        
        # Step 2: Retrieve additional context via semantic search
        additional_context = await self._semantic_search(
            clause.normalized_text,
            top_k=5
        )
        
        # Combine retrieved contexts
        all_contexts = self._prepare_regulatory_context(regulations, additional_context)
        
        # Step 3: Analyze compliance with LLM
        analysis = await self._analyze_with_llm(clause, all_contexts)
        
        return analysis
    
    async def analyze_clauses(
        self, 
        clauses: list[ExtractedClause]
    ) -> list[ComplianceAnalysis]:
        """
        Analyze multiple clauses for regulatory compliance.
        
        Args:
            clauses: List of extracted clauses
            
        Returns:
            List of ComplianceAnalysis objects
        """
        # Process in parallel batches
        batch_size = 5
        all_analyses = []
        
        for i in range(0, len(clauses), batch_size):
            batch = clauses[i:i + batch_size]
            batch_analyses = await asyncio.gather(
                *[self.analyze_clause(c) for c in batch],
                return_exceptions=True
            )
            
            for j, analysis in enumerate(batch_analyses):
                if isinstance(analysis, Exception):
                    logger.error(f"Error analyzing clause: {analysis}")
                    # Create a minimal error analysis
                    all_analyses.append(ComplianceAnalysis(
                        clause_id=batch[j].clause_id,
                        clause_type=batch[j].clause_type.value,
                        clause_text=batch[j].raw_text[:500],
                        is_compliant=False,
                        risk_level="high",
                        risk_score=75,
                        violated_regulations=[],
                        matched_regulations=[],
                        explanation=f"Analysis failed: {str(analysis)}",
                        reasoning_chain=["Error during analysis"],
                        recommendations=["Manual review required"],
                        confidence=0.0
                    ))
                else:
                    all_analyses.append(analysis)
        
        return all_analyses
    
    async def _embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for text using sentence-transformers.
        Uses all-MiniLM-L6-v2 which produces 384-dimensional embeddings.
        """
        # Truncate if too long (model max is ~256 tokens, but we handle longer text)
        truncated_text = text[:8000]
        
        # Run in executor to not block async loop
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: self.embedding_model.encode(truncated_text).tolist()
        )
        return embedding
    
    async def _semantic_search(
        self, 
        query: str, 
        top_k: int = 5
    ) -> list[RetrievedContext]:
        """
        Search for relevant regulations using semantic similarity.
        
        Args:
            query: Text to search for
            top_k: Number of results to return
            
        Returns:
            List of relevant regulatory contexts
        """
        try:
            # Generate embedding for query
            query_embedding = await self._embed_text(query)
            
            # Search in Pinecone
            index = await self._get_pinecone_index()
            results = index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            contexts = []
            for match in results.matches:
                metadata = match.metadata or {}
                contexts.append(RetrievedContext(
                    regulation_id=metadata.get("regulation_id", ""),
                    article_number=metadata.get("article_number", ""),
                    title=metadata.get("title", ""),
                    text=metadata.get("text", ""),
                    relevance_score=float(match.score),
                    source_url=metadata.get("source_url", ""),
                    regulation_type=metadata.get("regulation_type", "")
                ))
            
            return contexts
            
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []
    
    def _prepare_regulatory_context(
        self,
        regulations: list[RegulationArticle],
        additional_context: list[RetrievedContext]
    ) -> list[RetrievedContext]:
        """Prepare combined regulatory context for LLM."""
        contexts = []
        
        # Add direct regulations
        for reg in regulations:
            contexts.append(RetrievedContext(
                regulation_id=reg.regulation_id,
                article_number=reg.article_number,
                title=reg.title,
                text=reg.full_text,
                relevance_score=1.0,  # Direct match
                source_url=reg.source_url,
                regulation_type=reg.regulation_type.value
            ))
        
        # Add semantic search results (avoiding duplicates)
        existing_ids = {c.regulation_id for c in contexts}
        for ctx in additional_context:
            if ctx.regulation_id not in existing_ids:
                contexts.append(ctx)
        
        return contexts
    
    async def _analyze_with_llm(
        self,
        clause: ExtractedClause,
        contexts: list[RetrievedContext]
    ) -> ComplianceAnalysis:
        """
        Analyze clause compliance using LLM with retrieved context.
        """
        # Prepare context text
        context_text = self._format_context_for_llm(contexts)
        
        user_prompt = f"""Analyze the following contract clause for regulatory compliance.

## CLAUSE TO ANALYZE
Type: {clause.clause_type.value}
Text: {clause.normalized_text}

## RELEVANT REGULATIONS
{context_text}

Provide your compliance analysis as JSON."""

        try:
            logger.info(f"Using OpenAI LLM ({self.llm_model}) to analyze clause {clause.clause_id}...")
            # Use OpenAI for LLM analysis
            response = await self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": COMPLIANCE_ANALYSIS_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=2000
            )
            result_text = response.choices[0].message.content
            
            # Parse JSON response
            result = json.loads(result_text)
            
            return ComplianceAnalysis(
                clause_id=clause.clause_id,
                clause_type=clause.clause_type.value,
                clause_text=clause.raw_text[:1000],  # Truncate for storage
                is_compliant=result.get("is_compliant", False),
                risk_level=result.get("risk_level", "medium"),
                risk_score=float(result.get("risk_score", 50)),
                violated_regulations=result.get("violated_regulations", []),
                matched_regulations=contexts[:5],  # Top 5 relevant
                explanation=result.get("explanation", ""),
                reasoning_chain=result.get("reasoning_chain", []),
                recommendations=result.get("recommendations", []),
                confidence=float(result.get("confidence", 0.5))
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return self._create_error_analysis(clause, str(e))
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            return self._create_error_analysis(clause, str(e))
    
    def _format_context_for_llm(
        self, 
        contexts: list[RetrievedContext]
    ) -> str:
        """Format regulatory context for LLM prompt."""
        if not contexts:
            return "No relevant regulations found in the database."
        
        formatted = []
        for ctx in contexts:
            formatted.append(
                f"### {ctx.regulation_id}: {ctx.title}\n"
                f"Source: {ctx.source_url}\n"
                f"Relevance: {ctx.relevance_score:.2f}\n"
                f"Text: {ctx.text[:1000]}..."
            )
        
        return "\n\n".join(formatted)
    
    def _create_error_analysis(
        self, 
        clause: ExtractedClause, 
        error: str
    ) -> ComplianceAnalysis:
        """Create an error analysis when processing fails."""
        return ComplianceAnalysis(
            clause_id=clause.clause_id,
            clause_type=clause.clause_type.value,
            clause_text=clause.raw_text[:500],
            is_compliant=False,
            risk_level="high",
            risk_score=75,
            violated_regulations=[],
            matched_regulations=[],
            explanation=f"Analysis error: {error}. Manual review recommended.",
            reasoning_chain=["Analysis failed due to error"],
            recommendations=["Manual legal review required"],
            confidence=0.0
        )
    
    async def index_regulations(self):
        """
        Index all regulations in the vector database.
        Should be run during initial setup.
        """
        logger.info("Indexing regulations in vector database...")
        
        # Fetch all regulations
        gdpr_set = await self._regulations_fetcher.fetch_all_gdpr_articles()
        sec_set = await self._regulations_fetcher.fetch_all_sec_regulations()
        
        all_regulations = gdpr_set.articles + sec_set.articles
        
        # Prepare vectors for upsert
        vectors = []
        for reg in all_regulations:
            # Generate embedding
            embedding = await self._embed_text(reg.full_text)
            
            vector_id = hashlib.md5(reg.regulation_id.encode()).hexdigest()
            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "regulation_id": reg.regulation_id,
                    "regulation_type": reg.regulation_type.value,
                    "article_number": reg.article_number,
                    "title": reg.title,
                    "text": reg.full_text[:1000],  # Truncate for metadata
                    "source_url": reg.source_url
                }
            })
        
        # Upsert to Pinecone
        index = await self._get_pinecone_index()
        
        # Batch upsert
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            index.upsert(vectors=batch)
        
        logger.info(f"Indexed {len(vectors)} regulations")
