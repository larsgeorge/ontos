"""SPARQL Query Validator for security and safety checks."""

import re
from typing import Optional
from src.common.logging import get_logger

logger = get_logger(__name__)


class SPARQLQueryValidator:
    """Validates SPARQL queries for security and safety."""
    
    # Only allow read-only query types
    ALLOWED_QUERY_TYPES = {'SELECT', 'ASK', 'DESCRIBE', 'CONSTRUCT'}
    
    # Disallow dangerous keywords that could modify data or system state
    FORBIDDEN_KEYWORDS = {
        'INSERT', 'DELETE', 'DROP', 'CLEAR', 'CREATE', 
        'LOAD', 'COPY', 'MOVE', 'ADD', 'UPDATE'
    }
    
    # Limits to prevent resource exhaustion
    MAX_QUERY_LENGTH = 10000  # Maximum query length in characters
    MAX_TRIPLE_PATTERNS = 100  # Maximum number of triple patterns
    MAX_UNIONS = 20  # Maximum number of UNION clauses
    MAX_OPTIONALS = 30  # Maximum number of OPTIONAL clauses
    
    @staticmethod
    def validate(sparql: str) -> Optional[str]:
        """Validate a SPARQL query.
        
        Args:
            sparql: The SPARQL query string to validate
            
        Returns:
            Error message if invalid, None if valid
        """
        if not sparql or not sparql.strip():
            return "Query cannot be empty"
        
        # Check length
        if len(sparql) > SPARQLQueryValidator.MAX_QUERY_LENGTH:
            return f"Query too long. Maximum {SPARQLQueryValidator.MAX_QUERY_LENGTH} characters allowed."
        
        # Normalize for checking
        sparql_upper = sparql.upper()
        
        # Check for forbidden keywords (update/insert/delete operations)
        for keyword in SPARQLQueryValidator.FORBIDDEN_KEYWORDS:
            # Use word boundary to avoid false positives
            if re.search(r'\b' + keyword + r'\b', sparql_upper):
                return f"Query contains forbidden keyword: {keyword}. Only read-only queries are allowed."
        
        # Check query type - must contain SELECT, ASK, DESCRIBE, or CONSTRUCT
        # (allowing for PREFIX declarations before the query type)
        query_type = None
        for allowed_type in SPARQLQueryValidator.ALLOWED_QUERY_TYPES:
            # Allow PREFIX declarations before query type
            if re.search(r'\b' + allowed_type + r'\b', sparql_upper):
                query_type = allowed_type
                break
        
        if not query_type:
            return f"Query must contain one of: {', '.join(SPARQLQueryValidator.ALLOWED_QUERY_TYPES)}"
        
        # Check complexity - count triple patterns (approximate)
        # Count '?' characters as a proxy for variables and complexity
        # Also count opening braces as a proxy for graph patterns
        brace_count = sparql_upper.count('{')
        question_count = sparql_upper.count('?')
        triple_pattern_estimate = brace_count + (question_count // 2)
        
        if triple_pattern_estimate > SPARQLQueryValidator.MAX_TRIPLE_PATTERNS:
            return f"Query too complex. Estimated {triple_pattern_estimate} patterns, maximum {SPARQLQueryValidator.MAX_TRIPLE_PATTERNS} allowed."
        
        # Check for excessive UNION clauses (can cause combinatorial explosion)
        union_count = len(re.findall(r'\bUNION\b', sparql_upper))
        if union_count > SPARQLQueryValidator.MAX_UNIONS:
            return f"Too many UNION clauses ({union_count}). Maximum {SPARQLQueryValidator.MAX_UNIONS} allowed."
        
        # Check for excessive OPTIONAL clauses
        optional_count = len(re.findall(r'\bOPTIONAL\b', sparql_upper))
        if optional_count > SPARQLQueryValidator.MAX_OPTIONALS:
            return f"Too many OPTIONAL clauses ({optional_count}). Maximum {SPARQLQueryValidator.MAX_OPTIONALS} allowed."
        
        # Check for potentially problematic patterns
        # Cartesian products (multiple BGPs without shared variables)
        # This is hard to detect perfectly, but we can warn about queries with many triple patterns
        # and few variables
        if question_count > 0:
            patterns_per_variable = triple_pattern_estimate / question_count
            if patterns_per_variable > 10:
                logger.warning(f"Query may contain Cartesian product: {patterns_per_variable:.1f} patterns per variable")
        
        # All checks passed
        return None
    
    @staticmethod
    def sanitize_for_logging(sparql: str, max_length: int = 200) -> str:
        """Sanitize SPARQL query for safe logging.
        
        Args:
            sparql: The SPARQL query
            max_length: Maximum length to log
            
        Returns:
            Truncated and sanitized query string
        """
        if not sparql:
            return "<empty>"
        
        # Remove excessive whitespace
        sanitized = ' '.join(sparql.split())
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."
        
        return sanitized

