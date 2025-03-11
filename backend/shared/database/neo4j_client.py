"""
Neo4j client for graph database operations and vector search.
"""

import logging
from typing import Any, Dict, List, Optional, Union, Tuple
import time

from neo4j import GraphDatabase, Driver, AsyncDriver, AsyncSession
from neo4j.exceptions import Neo4jError
import numpy as np

from ..utils.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Client for Neo4j graph database operations with vector search support.
    
    This client provides methods for CRUD operations on Neo4j and
    specialized methods for vector search and graph traversal.
    """
    
    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None, database: Optional[str] = None):
        """
        Initialize the Neo4j client.
        
        Args:
            uri: Neo4j connection URI. Defaults to settings.neo4j_uri.
            user: Neo4j username. Defaults to settings.neo4j_user.
            password: Neo4j password. Defaults to settings.neo4j_password.
            database: Neo4j database name. Defaults to None (uses default database).
        """
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        self.database = database
        
        # Initialize driver
        self.driver = self._create_driver()
    
    def _create_driver(self) -> Driver:
        """Create and return a Neo4j driver."""
        try:
            return GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
        except Exception as e:
            logger.error(f"Error creating Neo4j driver: {str(e)}")
            raise
    
    def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
    
    async def verify_connectivity(self) -> bool:
        """
        Verify that the connection to Neo4j is working.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Use a simple query to test the connection
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 AS test")
                record = result.single()
                return record and record["test"] == 1
        except Exception as e:
            logger.error(f"Neo4j connectivity check failed: {str(e)}")
            return False
    
    async def run_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Run a Cypher query and return the results.
        
        Args:
            query: Cypher query string
            parameters: Optional parameters for the query
            
        Returns:
            List of records as dictionaries
        """
        if parameters is None:
            parameters = {}
            
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters)
                return [record.data() for record in result]
        except Neo4jError as e:
            logger.error(f"Neo4j query error: {str(e)}")
            raise
    
    async def create_node(
        self, 
        labels: Union[str, List[str]], 
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a node with the given labels and properties.
        
        Args:
            labels: Single label or list of labels for the node
            properties: Properties for the node
            
        Returns:
            The created node as a dictionary
        """
        if isinstance(labels, str):
            labels = [labels]
            
        # Build label string for Cypher
        label_string = ":".join(labels)
        
        query = f"""
        CREATE (n:{label_string} $properties)
        RETURN n
        """
        
        try:
            results = await self.run_query(query, {"properties": properties})
            if results and len(results) > 0:
                return results[0].get("n", {})
            return {}
        except Exception as e:
            logger.error(f"Error creating node: {str(e)}")
            raise
    
    async def merge_node(
        self, 
        labels: Union[str, List[str]], 
        match_properties: Dict[str, Any],
        set_properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Find a node or create it if it doesn't exist (MERGE operation).
        
        Args:
            labels: Single label or list of labels for the node
            match_properties: Properties to match for finding the node
            set_properties: Additional properties to set if the node is created
            
        Returns:
            The matched or created node as a dictionary
        """
        if isinstance(labels, str):
            labels = [labels]
            
        # Build label string for Cypher
        label_string = ":".join(labels)
        
        # Build property match string
        prop_matches = []
        for key in match_properties:
            prop_matches.append(f"n.{key} = ${key}")
        
        match_string = " AND ".join(prop_matches)
        
        if set_properties:
            # MERGE with ON CREATE SET for additional properties
            query = f"""
            MERGE (n:{label_string} {{{match_string}}})
            ON CREATE SET n += $set_properties
            RETURN n
            """
            params = {**match_properties, "set_properties": set_properties}
        else:
            # Simple MERGE without additional properties
            query = f"""
            MERGE (n:{label_string} {{{match_string}}})
            RETURN n
            """
            params = match_properties
        
        try:
            results = await self.run_query(query, params)
            if results and len(results) > 0:
                return results[0].get("n", {})
            return {}
        except Exception as e:
            logger.error(f"Error merging node: {str(e)}")
            raise
    
    async def create_relationship(
        self, 
        start_node_match: Dict[str, Any],
        end_node_match: Dict[str, Any],
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a relationship between two nodes.
        
        Args:
            start_node_match: Properties to match for the start node
            end_node_match: Properties to match for the end node
            relationship_type: Type of relationship to create
            properties: Optional properties for the relationship
            
        Returns:
            The created relationship as a dictionary
        """
        if properties is None:
            properties = {}
            
        # Build match conditions for nodes
        start_conditions = " AND ".join([f"a.{k} = ${k}" for k in start_node_match.keys()])
        end_conditions = " AND ".join([f"b.{k} = $end_{k}" for k in end_node_match.keys()])
        
        # Prefix end node parameters to avoid name collisions
        end_params = {f"end_{k}": v for k, v in end_node_match.items()}
        params = {**start_node_match, **end_params, "props": properties}
        
        query = f"""
        MATCH (a) WHERE {start_conditions}
        MATCH (b) WHERE {end_conditions}
        CREATE (a)-[r:{relationship_type} $props]->(b)
        RETURN a, r, b
        """
        
        try:
            results = await self.run_query(query, params)
            if results and len(results) > 0:
                return results[0]
            return {}
        except Exception as e:
            logger.error(f"Error creating relationship: {str(e)}")
            raise
    
    async def vector_search(
        self, 
        node_label: str,
        vector_property: str,
        query_vector: List[float],
        top_k: int = 10,
        min_similarity: float = 0.0,
        additional_filters: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform a vector similarity search.
        
        Args:
            node_label: Label of nodes to search
            vector_property: Name of the property containing vectors
            query_vector: Query vector for similarity search
            top_k: Maximum number of results to return
            min_similarity: Minimum similarity score (0.0 to 1.0)
            additional_filters: Optional additional WHERE clause
            
        Returns:
            List of nodes with similarity scores
        """
        # Build WHERE clause
        where_clause = ""
        if additional_filters:
            where_clause = f"WHERE {additional_filters}"
        
        query = f"""
        MATCH (n:{node_label}) {where_clause}
        WITH n, gds.similarity.cosine(n.{vector_property}, $query_vector) AS score
        WHERE score >= $min_similarity
        RETURN n, score
        ORDER BY score DESC
        LIMIT $top_k
        """
        
        params = {
            "query_vector": query_vector,
            "min_similarity": min_similarity,
            "top_k": top_k
        }
        
        try:
            return await self.run_query(query, params)
        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            raise
    
    async def create_vector_index(
        self,
        index_name: str,
        node_label: str,
        vector_property: str,
        dimension: int,
        similarity_metric: str = "cosine"
    ) -> bool:
        """
        Create a vector index for faster similarity searches.
        
        Args:
            index_name: Name for the vector index
            node_label: Label of nodes to index
            vector_property: Name of the property containing vectors
            dimension: Dimension of the vectors
            similarity_metric: Similarity metric to use (default: cosine)
            
        Returns:
            True if index was created successfully
        """
        query = """
        CALL db.index.vector.createNodeIndex(
          $index_name,
          $node_label,
          $vector_property,
          $dimension,
          $similarity_metric
        )
        """
        
        params = {
            "index_name": index_name,
            "node_label": node_label,
            "vector_property": vector_property,
            "dimension": dimension,
            "similarity_metric": similarity_metric
        }
        
        try:
            await self.run_query(query, params)
            logger.info(f"Vector index '{index_name}' created successfully")
            return True
        except Neo4jError as e:
            if "already exists" in str(e):
                logger.info(f"Vector index '{index_name}' already exists")
                return True
            logger.error(f"Error creating vector index: {str(e)}")
            raise
    
    async def hybrid_search(
        self,
        node_label: str,
        text_property: str,
        vector_property: str,
        query_text: str,
        query_vector: List[float],
        top_k: int = 10,
        vector_weight: float = 0.5,
        text_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Perform a hybrid (text + vector) search.
        
        Args:
            node_label: Label of nodes to search
            text_property: Name of the property containing text
            vector_property: Name of the property containing vectors
            query_text: Text query for keyword search
            query_vector: Vector query for similarity search
            top_k: Maximum number of results to return
            vector_weight: Weight for vector similarity (0.0 to 1.0)
            text_weight: Weight for text relevance (0.0 to 1.0)
            
        Returns:
            List of nodes with combined scores
        """
        # Normalize weights
        total_weight = vector_weight + text_weight
        v_weight = vector_weight / total_weight
        t_weight = text_weight / total_weight
        
        query = f"""
        CALL db.index.fulltext.queryNodes("text_index", $query_text) YIELD node, score as textScore
        WHERE node:{node_label}
        WITH node, textScore
        
        // Combine with vector similarity
        WITH node, textScore, gds.similarity.cosine(node.{vector_property}, $query_vector) AS vectorScore
        
        // Calculate combined score
        WITH node, 
            (textScore * $text_weight) + (vectorScore * $vector_weight) AS combinedScore
        
        RETURN node, combinedScore
        ORDER BY combinedScore DESC
        LIMIT $top_k
        """
        
        params = {
            "query_text": query_text,
            "query_vector": query_vector,
            "text_weight": t_weight,
            "vector_weight": v_weight,
            "top_k": top_k
        }
        
        try:
            return await self.run_query(query, params)
        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            raise


# Create a default client instance
default_neo4j_client = Neo4jClient()


def get_tenant_neo4j_client(tenant_id: str) -> Neo4jClient:
    """
    Get a Neo4j client for a specific tenant.
    
    Args:
        tenant_id: ID of the tenant
        
    Returns:
        A Neo4jClient instance for the tenant database
    """
    # In Neo4j, we use separate databases for tenant isolation
    database = f"tenant_{tenant_id}"
    return Neo4jClient(database=database)