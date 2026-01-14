"""
Robot Framework library for semantic similarity calculations.
Uses sentence-transformers for embedding-based similarity matching.
"""
# Lazy import to avoid errors during libspec generation
# No imports at module level - everything is loaded lazily using importlib
import importlib
import sys

# Robot Framework library metadata
ROBOT_LIBRARY_VERSION = '1.0.0'

_model = None
_util = None

# Suppress import errors during libspec generation
if sys.version_info < (3, 0):
    # Python 2 compatibility (unlikely but safe)
    pass

def _get_model():
    """Lazy load the model only when needed."""
    global _model, _util
    if _model is None:
        try:
            # Use importlib to dynamically import, avoiding static analysis issues
            st_module = importlib.import_module('sentence_transformers')
            SentenceTransformer = getattr(st_module, 'SentenceTransformer')
            _util = getattr(st_module, 'util')
            _model = SentenceTransformer("all-MiniLM-L6-v2")
        except (ImportError, AttributeError) as e:
            raise ImportError(
                "sentence_transformers is not installed. "
                "Please install it using: pip install sentence-transformers"
            ) from e
    return _model, _util

def get_embedding(text):
    """
    Get the embedding vector for a given text.
    
    Args:
        text (str): The text to embed
    
    Returns:
        list: The embedding vector as a list (converted from tensor)
    """
    model, util = _get_model()
    embedding = model.encode(text, convert_to_tensor=True)
    # Convert tensor to list for Robot Framework compatibility
    embedding_list = embedding.cpu().tolist()
    return embedding_list

def get_embedding_preview(embedding_list, num_values=5):
    """
    Get a preview of the first N values from an embedding vector.
    
    Args:
        embedding_list (list): The embedding vector as a list
        num_values (int): Number of values to preview (default: 5)
    
    Returns:
        list: First N values of the embedding vector
    """
    if not embedding_list:
        return []
    return embedding_list[:num_values]

def semantic_similarity(prompt, text, threshold=0.55):
    """
    Calculate semantic similarity between a prompt and text using cosine similarity.
    
    Args:
        prompt (str): The search prompt/query
        text (str): The text to compare against the prompt
        threshold (float): Similarity threshold (default: 0.55)
    
    Returns:
        tuple: (score, is_match, prompt_embedding, text_embedding) where:
               - score is the cosine similarity score
               - is_match is a boolean indicating if score >= threshold
               - prompt_embedding is the embedding vector for the prompt (as list)
               - text_embedding is the embedding vector for the text (as list)
    """
    model, util = _get_model()
    emb1 = model.encode(prompt, convert_to_tensor=True)
    emb2 = model.encode(text, convert_to_tensor=True)
    score = util.cos_sim(emb1, emb2).item()
    is_match = score >= threshold
    # Convert tensors to lists for Robot Framework
    emb1_list = emb1.cpu().tolist()
    emb2_list = emb2.cpu().tolist()
    return score, is_match, emb1_list, emb2_list

def evaluate_boolean_expression(expression, text):
    """
    Evaluates Boolean expressions (AND/OR) against text. Supports nested parentheses and complex expressions.
    
    Args:
        expression (str): Boolean expression with AND/OR operators and optional parentheses
        text (str): Text to search in (should be lowercase)
    
    Returns:
        bool: True if expression matches, False otherwise
    
    Examples:
        - "java developer AND python" - both must match
        - "java OR python" - at least one must match
        - "(java OR python) AND aws" - either java or python must match, AND aws must match
        - "java AND (python OR react) AND aws" - java and aws must match, and either python or react must match
    """
    import re
    
    def check_term(term, txt):
        """Check if a term exists in text."""
        # Remove parentheses and quotes
        term_clean = re.sub(r'[()"\']', '', term).strip().lower()
        if not term_clean:
            return False
        
        # Split into words and check if all meaningful words exist
        words = [w.strip() for w in term_clean.split() if len(w.strip()) > 2]
        if not words:
            # If no meaningful words, check if the whole term exists
            return term_clean in txt
        
        # Check if all meaningful words exist in text
        return all(word in txt for word in words)
    
    def evaluate_expression(expr, txt):
        """Recursively evaluate Boolean expression."""
        expr = expr.strip()
        
        # Handle parentheses first (innermost first)
        while '(' in expr:
            # Find innermost parentheses
            start = expr.rfind('(')
            end = expr.find(')', start)
            if end == -1:
                break
            
            # Evaluate inner expression
            inner = expr[start+1:end]
            inner_result = evaluate_expression(inner, txt)
            
            # Replace parentheses with result
            expr = expr[:start] + ('TRUE' if inner_result else 'FALSE') + expr[end+1:]
        
        # Evaluate AND operations (higher precedence)
        and_parts = [p.strip() for p in expr.split(' AND ')]
        if len(and_parts) > 1:
            # All AND parts must be true
            return all(evaluate_expression(part, txt) for part in and_parts)
        
        # Evaluate OR operations
        or_parts = [p.strip() for p in expr.split(' OR ')]
        if len(or_parts) > 1:
            # At least one OR part must be true
            return any(evaluate_expression(part, txt) for part in or_parts)
        
        # Single term - check if it exists
        term = expr.replace('TRUE', '').replace('FALSE', '').strip()
        if not term:
            return True
        
        return check_term(term, txt)
    
    # Normalize expression (remove extra spaces)
    expression_normalized = re.sub(r'\s+', ' ', expression).strip()
    
    # Evaluate the expression
    return evaluate_expression(expression_normalized, text.lower())
