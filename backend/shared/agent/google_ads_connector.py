"""
Google Ads connector implementation for the Supertrack platform.

This connector provides access to Google Ads API for advertising data.
"""

import logging
import json
import asyncio
import httpx
import time
import re
from typing import Any, Dict, List, Optional, Union, Tuple, Set
from enum import Enum

from .oauth2_connector import (
    OAuth2Connector, 
    OAuth2FlowType,
    OAuth2TokenType,
)
from .connector_agent import (
    ConnectorType,
    ConnectionStatus,
    ConnectionConfig,
    ConnectorResult,
)
from .base_agent import AgentOptions, OpenAIModel

# Configure logging
logger = logging.getLogger(__name__)


class GoogleAdsAPIVersion(str, Enum):
    """Google Ads API versions."""
    V14 = "v14"
    V13 = "v13"
    V12 = "v12"
    V11 = "v11"
    LATEST = "v14"  # Alias for the latest version


class GoogleAdsConnector(OAuth2Connector):
    """
    Connector for Google Ads API.
    
    This connector provides access to Google Ads data via the Google Ads API,
    including campaigns, ad groups, ads, and performance metrics.
    """
    
    @property
    def connector_type(self) -> ConnectorType:
        """Get the connector type."""
        return ConnectorType.REST_API
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        options: Optional[AgentOptions] = None,
        model: Optional[OpenAIModel] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        connection_config: Optional[ConnectionConfig] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the Google Ads connector.
        
        Args:
            session_id: Optional ID for the session
            options: Optional configuration options
            model: OpenAI model instance
            tenant_id: ID of the tenant
            user_id: ID of the user
            connection_config: Configuration for the Google Ads connection
            system_prompt: Custom system prompt
        """
        # Set default Google Ads API configuration
        if connection_config:
            api_version = connection_config.params.get("api_version", GoogleAdsAPIVersion.LATEST)
            
            # Set Google-specific OAuth2 URLs
            connection_config.params.setdefault("authorization_endpoint", "https://accounts.google.com/o/oauth2/auth")
            connection_config.params.setdefault("token_endpoint", "https://oauth2.googleapis.com/token")
            connection_config.params.setdefault("api_base_url", f"https://googleads.googleapis.com/{api_version}")
            
            # Set default flow type
            connection_config.params.setdefault("flow_type", OAuth2FlowType.AUTHORIZATION_CODE)
            
            # Set default scopes
            scopes = connection_config.params.get("scopes", [])
            
            if not scopes:
                # Default scopes for Google Ads API
                default_scopes = [
                    "https://www.googleapis.com/auth/adwords",
                    "https://www.googleapis.com/auth/userinfo.email",
                ]
                connection_config.params["scopes"] = default_scopes
            
            # Add additional parameters for Google OAuth2
            connection_config.params.setdefault("custom_auth_params", {
                "access_type": "offline",  # Get refresh token
                "prompt": "consent",  # Force consent screen
            })
        
        # Initialize the OAuth2 connector with Google-specific prompt
        super().__init__(
            session_id=session_id,
            options=options,
            model=model,
            tenant_id=tenant_id,
            user_id=user_id,
            connection_config=connection_config,
            system_prompt=system_prompt or self._get_google_ads_prompt(),
        )
        
        # Google Ads-specific state
        self.customer_id = None
        self.manager_id = None
        self.customer_ids = []
        self.developer_token = connection_config.credentials.get("developer_token") if connection_config else None
        self.login_customer_id = connection_config.params.get("login_customer_id") if connection_config else None
    
    def _get_google_ads_prompt(self) -> str:
        """
        Get the system prompt for the Google Ads connector.
        
        Returns:
            System prompt
        """
        return """
        You are an AI assistant working within the Supertrack AI Platform. Your role is to help users 
        connect to and interact with Google Ads API. Follow these guidelines:
        
        1. Help users establish connections to Google Ads API
        2. Assist with retrieving advertising data from Google Ads
        3. Format API responses in a clear and useful way
        4. Provide guidance on available endpoints and functionality
        5. Handle API errors and provide troubleshooting assistance
        
        You can help with:
        1. Configuring Google Ads API connections with proper authentication
        2. Building GAQL (Google Ads Query Language) queries
        3. Retrieving campaign, ad group, and ad performance data
        4. Analyzing advertising metrics and performance
        5. Troubleshooting API connection issues
        
        Please provide clear, structured guidance regarding Google Ads API functionality,
        data retrieval, and any error messages that occur.
        """
    
    async def connect(self) -> ConnectorResult:
        """
        Connect to the Google Ads API.
        
        Returns:
            Result of the connection attempt
        """
        # Check for developer token
        if not self.developer_token:
            self.connection_config.status = ConnectionStatus.ERROR
            self.connection_config.error = "Developer token is required for Google Ads API"
            return ConnectorResult.error_result("Developer token is required for Google Ads API")
        
        # Use OAuth2 connector's connect method
        result = await super().connect()
        
        if not result.success:
            return result
        
        # For successful connections, retrieve customer information
        if self.connection_config.status == ConnectionStatus.CONNECTED:
            return await self._initialize_customer_data()
        
        return result
    
    async def _initialize_customer_data(self) -> ConnectorResult:
        """
        Initialize customer data after successful connection.
        
        Returns:
            Result with customer information
        """
        try:
            # Get user email for diagnostics
            user_info_result = await self.query(
                path="https://www.googleapis.com/oauth2/v2/userinfo"
            )
            
            if not user_info_result.success:
                return user_info_result
            
            email = user_info_result.data.get("email")
            
            # Set up API request headers
            if not self.client:
                return ConnectorResult.error_result("Client not initialized")
            
            # Add developer token header for all requests
            self.client.headers["developer-token"] = self.developer_token
            
            # Fetch accessible customers
            list_accessible_customers_result = await self._list_accessible_customers()
            
            if not list_accessible_customers_result.success:
                return list_accessible_customers_result
            
            customer_resource_names = list_accessible_customers_result.data.get("resourceNames", [])
            
            # Extract customer IDs from resource names
            customer_ids = []
            for resource_name in customer_resource_names:
                match = re.search(r'customers/(\d+)', resource_name)
                if match:
                    customer_ids.append(match.group(1))
            
            self.customer_ids = customer_ids
            
            # Set first customer as active if none specified
            if customer_ids and not self.customer_id:
                if self.login_customer_id and self.login_customer_id in customer_ids:
                    self.customer_id = self.login_customer_id
                    self.manager_id = self.login_customer_id
                else:
                    self.customer_id = customer_ids[0]
                
                # Add customer ID header
                if self.login_customer_id:
                    self.client.headers["login-customer-id"] = self.login_customer_id
            
            return ConnectorResult.success_result(
                data={
                    "email": email,
                    "customer_ids": customer_ids,
                    "active_customer_id": self.customer_id,
                    "manager_id": self.manager_id,
                },
                metadata={
                    "customer_count": len(customer_ids),
                    "api_version": self.connection_config.params.get("api_version", GoogleAdsAPIVersion.LATEST),
                }
            )
        except Exception as e:
            logger.error(f"Error initializing Google Ads customer data: {str(e)}")
            return ConnectorResult.error_result(f"Error initializing Google Ads customer data: {str(e)}")
    
    async def _list_accessible_customers(self) -> ConnectorResult:
        """
        List customers accessible by the authenticated user.
        
        Returns:
            Result with accessible customers
        """
        try:
            # Google Ads API endpoint for listing accessible customers
            api_version = self.connection_config.params.get("api_version", GoogleAdsAPIVersion.LATEST)
            path = f"https://googleads.googleapis.com/{api_version}/customers:listAccessibleCustomers"
            
            response = await self.client.get(path)
            
            if response.status_code >= 400:
                # Parse error response
                error_data = response.json() if "application/json" in response.headers.get("content-type", "") else {}
                error_message = error_data.get("error", {}).get("message", f"API error: {response.status_code}")
                
                return ConnectorResult.error_result(
                    error_message,
                    metadata={
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "data": error_data,
                    }
                )
            
            data = response.json()
            
            return ConnectorResult.success_result(
                data=data,
                metadata={
                    "status_code": response.status_code,
                    "resource_count": len(data.get("resourceNames", [])),
                }
            )
        except Exception as e:
            logger.error(f"Error listing accessible customers: {str(e)}")
            return ConnectorResult.error_result(f"Error listing accessible customers: {str(e)}")
    
    async def set_active_customer(self, customer_id: str) -> ConnectorResult:
        """
        Set the active customer ID for subsequent operations.
        
        Args:
            customer_id: Customer ID to set as active
            
        Returns:
            Result of the operation
        """
        try:
            if customer_id not in self.customer_ids:
                return ConnectorResult.error_result(f"Customer ID {customer_id} not found in accessible customers")
            
            self.customer_id = customer_id
            
            # Update header if needed
            if self.client:
                self.client.headers["login-customer-id"] = self.login_customer_id if self.login_customer_id else customer_id
            
            return ConnectorResult.success_result(
                data={"message": f"Customer ID {customer_id} set as active"},
                metadata={"customer_id": customer_id}
            )
        except Exception as e:
            logger.error(f"Error setting active customer: {str(e)}")
            return ConnectorResult.error_result(f"Error setting active customer: {str(e)}")
    
    async def search_google_ads(self, query: str, customer_id: Optional[str] = None) -> ConnectorResult:
        """
        Execute a GAQL (Google Ads Query Language) search query.
        
        Args:
            query: GAQL query string
            customer_id: Optional customer ID to use for this query
            
        Returns:
            Result containing search results
        """
        try:
            # Use specified customer ID or active customer ID
            customer_id = customer_id or self.customer_id
            
            if not customer_id:
                return ConnectorResult.error_result("No customer ID specified or selected")
            
            # Google Ads API endpoint for search
            api_version = self.connection_config.params.get("api_version", GoogleAdsAPIVersion.LATEST)
            path = f"https://googleads.googleapis.com/{api_version}/customers/{customer_id}/googleAds:search"
            
            # Build request
            data = {
                "query": query
            }
            
            # Add page token if available
            page_size = self.connection_config.params.get("page_size")
            if page_size:
                data["pageSize"] = page_size
            
            # Execute request
            response = await self.client.post(path, json=data)
            
            if response.status_code >= 400:
                # Parse error response
                error_data = response.json() if "application/json" in response.headers.get("content-type", "") else {}
                error_message = error_data.get("error", {}).get("message", f"API error: {response.status_code}")
                
                return ConnectorResult.error_result(
                    error_message,
                    metadata={
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "data": error_data,
                    }
                )
            
            # Parse response
            result_data = response.json()
            
            # Process results
            processed_results = []
            
            if "results" in result_data:
                for row in result_data["results"]:
                    processed_row = {}
                    
                    # Flatten the nested structure for easier access
                    for field_name, field_value in row.items():
                        if isinstance(field_value, dict):
                            for sub_field, sub_value in field_value.items():
                                # Handle nested structures
                                if isinstance(sub_value, dict) and "value" in sub_value:
                                    processed_row[f"{field_name}.{sub_field}"] = sub_value["value"]
                                else:
                                    processed_row[f"{field_name}.{sub_field}"] = sub_value
                        else:
                            processed_row[field_name] = field_value
                    
                    processed_results.append(processed_row)
            
            # Add metadata about next page
            metadata = {
                "next_page_token": result_data.get("nextPageToken"),
                "total_results_count": result_data.get("totalResultsCount"),
                "field_mask": result_data.get("fieldMask"),
                "results_count": len(result_data.get("results", [])),
            }
            
            return ConnectorResult.success_result(
                data={
                    "results": processed_results,
                    "raw_results": result_data.get("results", []),
                    "next_page_token": result_data.get("nextPageToken"),
                },
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Error executing Google Ads search: {str(e)}")
            return ConnectorResult.error_result(f"Error executing Google Ads search: {str(e)}")
    
    async def get_campaigns(self, params: Dict[str, Any]) -> ConnectorResult:
        """
        Get campaigns for the selected customer.
        
        Args:
            params: Parameters for the query
                - status: Optional filter by status
                - limit: Optional result limit
                - page_token: Optional page token for pagination
                
        Returns:
            Result containing campaign data
        """
        try:
            # Build GAQL query
            status_filter = params.get("status")
            date_range = params.get("date_range", "LAST_30_DAYS")
            
            # Base query
            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    campaign.advertising_channel_type,
                    campaign.advertising_channel_sub_type,
                    campaign.bidding_strategy_type,
                    campaign.start_date,
                    campaign.end_date,
                    campaign.serving_status,
                    campaign.budget_remaining_micros,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.average_cpm
                FROM campaign
                WHERE segments.date DURING {date_range}
            """
            
            # Add status filter if provided
            if status_filter:
                if isinstance(status_filter, list):
                    status_conditions = " OR ".join([f"campaign.status = '{status}'" for status in status_filter])
                    query += f" AND ({status_conditions})"
                else:
                    query += f" AND campaign.status = '{status_filter}'"
            
            # Add ordering
            query += " ORDER BY campaign.name"
            
            # Add limit if provided
            limit = params.get("limit")
            if limit:
                query += f" LIMIT {limit}"
            
            # Execute query
            result = await self.search_google_ads(query)
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving campaigns: {str(e)}")
            return ConnectorResult.error_result(f"Error retrieving campaigns: {str(e)}")
    
    async def get_ad_groups(self, params: Dict[str, Any]) -> ConnectorResult:
        """
        Get ad groups for the selected customer.
        
        Args:
            params: Parameters for the query
                - campaign_id: Optional campaign ID to filter by
                - status: Optional filter by status
                - limit: Optional result limit
                - page_token: Optional page token for pagination
                
        Returns:
            Result containing ad group data
        """
        try:
            # Build GAQL query
            campaign_id = params.get("campaign_id")
            status_filter = params.get("status")
            date_range = params.get("date_range", "LAST_30_DAYS")
            
            # Base query
            query = f"""
                SELECT
                    ad_group.id,
                    ad_group.name,
                    ad_group.status,
                    ad_group.type,
                    campaign.id,
                    campaign.name,
                    ad_group.base_ad_group,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.ctr,
                    metrics.average_cpc
                FROM ad_group
                WHERE segments.date DURING {date_range}
            """
            
            # Add campaign filter if provided
            if campaign_id:
                query += f" AND campaign.id = {campaign_id}"
            
            # Add status filter if provided
            if status_filter:
                if isinstance(status_filter, list):
                    status_conditions = " OR ".join([f"ad_group.status = '{status}'" for status in status_filter])
                    query += f" AND ({status_conditions})"
                else:
                    query += f" AND ad_group.status = '{status_filter}'"
            
            # Add ordering
            query += " ORDER BY ad_group.name"
            
            # Add limit if provided
            limit = params.get("limit")
            if limit:
                query += f" LIMIT {limit}"
            
            # Execute query
            result = await self.search_google_ads(query)
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving ad groups: {str(e)}")
            return ConnectorResult.error_result(f"Error retrieving ad groups: {str(e)}")
    
    async def get_ads(self, params: Dict[str, Any]) -> ConnectorResult:
        """
        Get ads for the selected customer.
        
        Args:
            params: Parameters for the query
                - ad_group_id: Optional ad group ID to filter by
                - campaign_id: Optional campaign ID to filter by
                - status: Optional filter by status
                - limit: Optional result limit
                - page_token: Optional page token for pagination
                
        Returns:
            Result containing ad data
        """
        try:
            # Build GAQL query
            ad_group_id = params.get("ad_group_id")
            campaign_id = params.get("campaign_id")
            status_filter = params.get("status")
            date_range = params.get("date_range", "LAST_30_DAYS")
            
            # Base query
            query = f"""
                SELECT
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.name,
                    ad_group_ad.ad.type,
                    ad_group_ad.status,
                    ad_group_ad.ad.final_urls,
                    ad_group.id,
                    ad_group.name,
                    campaign.id,
                    campaign.name,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.ctr,
                    metrics.average_cpc
                FROM ad_group_ad
                WHERE segments.date DURING {date_range}
            """
            
            # Add filters if provided
            if ad_group_id:
                query += f" AND ad_group.id = {ad_group_id}"
            
            if campaign_id:
                query += f" AND campaign.id = {campaign_id}"
            
            # Add status filter if provided
            if status_filter:
                if isinstance(status_filter, list):
                    status_conditions = " OR ".join([f"ad_group_ad.status = '{status}'" for status in status_filter])
                    query += f" AND ({status_conditions})"
                else:
                    query += f" AND ad_group_ad.status = '{status_filter}'"
            
            # Add ordering
            query += " ORDER BY ad_group_ad.ad.name"
            
            # Add limit if provided
            limit = params.get("limit")
            if limit:
                query += f" LIMIT {limit}"
            
            # Execute query
            result = await self.search_google_ads(query)
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving ads: {str(e)}")
            return ConnectorResult.error_result(f"Error retrieving ads: {str(e)}")
    
    async def get_keywords(self, params: Dict[str, Any]) -> ConnectorResult:
        """
        Get keywords for the selected customer.
        
        Args:
            params: Parameters for the query
                - ad_group_id: Optional ad group ID to filter by
                - campaign_id: Optional campaign ID to filter by
                - status: Optional filter by status
                - limit: Optional result limit
                - page_token: Optional page token for pagination
                
        Returns:
            Result containing keyword data
        """
        try:
            # Build GAQL query
            ad_group_id = params.get("ad_group_id")
            campaign_id = params.get("campaign_id")
            status_filter = params.get("status")
            date_range = params.get("date_range", "LAST_30_DAYS")
            
            # Base query
            query = f"""
                SELECT
                    ad_group_criterion.criterion_id,
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    ad_group_criterion.status,
                    ad_group_criterion.quality_info.quality_score,
                    ad_group.id,
                    ad_group.name,
                    campaign.id,
                    campaign.name,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.average_position
                FROM keyword_view
                WHERE segments.date DURING {date_range}
            """
            
            # Add filters if provided
            if ad_group_id:
                query += f" AND ad_group.id = {ad_group_id}"
            
            if campaign_id:
                query += f" AND campaign.id = {campaign_id}"
            
            # Add status filter if provided
            if status_filter:
                if isinstance(status_filter, list):
                    status_conditions = " OR ".join([f"ad_group_criterion.status = '{status}'" for status in status_filter])
                    query += f" AND ({status_conditions})"
                else:
                    query += f" AND ad_group_criterion.status = '{status_filter}'"
            
            # Add ordering
            query += " ORDER BY metrics.impressions DESC"
            
            # Add limit if provided
            limit = params.get("limit")
            if limit:
                query += f" LIMIT {limit}"
            
            # Execute query
            result = await self.search_google_ads(query)
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving keywords: {str(e)}")
            return ConnectorResult.error_result(f"Error retrieving keywords: {str(e)}")
    
    async def get_performance_metrics(self, params: Dict[str, Any]) -> ConnectorResult:
        """
        Get performance metrics for the selected customer.
        
        Args:
            params: Parameters for the query
                - date_range: Date range (e.g., LAST_7_DAYS, LAST_30_DAYS, etc.)
                - dimensions: List of dimensions to group by
                - metrics: List of metrics to retrieve
                - limit: Optional result limit
                
        Returns:
            Result containing performance metrics data
        """
        try:
            # Build GAQL query
            date_range = params.get("date_range", "LAST_30_DAYS")
            dimensions = params.get("dimensions", ["segments.date"])
            metrics = params.get("metrics", [
                "metrics.impressions",
                "metrics.clicks",
                "metrics.cost_micros",
                "metrics.conversions",
                "metrics.ctr",
                "metrics.average_cpc",
                "metrics.conversion_rate",
                "metrics.cost_per_conversion",
            ])
            
            # Convert lists to strings
            dimensions_str = ", ".join(dimensions)
            metrics_str = ", ".join(metrics)
            
            # Base query
            query = f"""
                SELECT
                    {dimensions_str},
                    {metrics_str}
                FROM campaign
                WHERE segments.date DURING {date_range}
            """
            
            # Add ordering by date if date is a dimension
            if "segments.date" in dimensions:
                query += " ORDER BY segments.date"
            
            # Add limit if provided
            limit = params.get("limit")
            if limit:
                query += f" LIMIT {limit}"
            
            # Execute query
            result = await self.search_google_ads(query)
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving performance metrics: {str(e)}")
            return ConnectorResult.error_result(f"Error retrieving performance metrics: {str(e)}")
    
    async def execute(self, **kwargs) -> ConnectorResult:
        """
        Execute a Google Ads-specific operation.
        
        Args:
            **kwargs: Parameters for the operation
                - operation: Operation name
                - params: Parameters for the operation
                
        Returns:
            Result of the operation
        """
        try:
            # Get operation details
            operation = kwargs.get("operation")
            params = kwargs.get("params", {})
            
            if not operation:
                # Delegate to parent class for standard HTTP requests
                return await super().execute(**kwargs)
            
            # Google Ads-specific operations
            if operation == "set_active_customer":
                return await self.set_active_customer(params.get("customer_id"))
            elif operation == "search":
                return await self.search_google_ads(params.get("query"), params.get("customer_id"))
            elif operation == "get_campaigns":
                return await self.get_campaigns(params)
            elif operation == "get_ad_groups":
                return await self.get_ad_groups(params)
            elif operation == "get_ads":
                return await self.get_ads(params)
            elif operation == "get_keywords":
                return await self.get_keywords(params)
            elif operation == "get_performance_metrics":
                return await self.get_performance_metrics(params)
            else:
                return ConnectorResult.error_result(f"Unsupported Google Ads operation: {operation}")
        except Exception as e:
            logger.error(f"Error executing Google Ads operation: {str(e)}")
            return ConnectorResult.error_result(f"Error executing Google Ads operation: {str(e)}")
    
    async def get_metadata(self, **kwargs) -> ConnectorResult:
        """
        Get metadata about the Google Ads connection.
        
        Args:
            **kwargs: Parameters for the metadata retrieval
                - type: Type of metadata to retrieve
                
        Returns:
            Result containing metadata
        """
        metadata_type = kwargs.get("type", "connection")
        
        if metadata_type == "connection":
            # Use parent class for connection metadata
            result = await super().get_metadata(**kwargs)
            
            if result.success and "data" in result.data:
                # Add Google Ads-specific metadata
                result.data["data"].update({
                    "active_customer_id": self.customer_id,
                    "manager_id": self.manager_id,
                    "customer_ids": self.customer_ids,
                    "customer_count": len(self.customer_ids),
                    "api_version": self.connection_config.params.get("api_version", GoogleAdsAPIVersion.LATEST),
                    "has_developer_token": bool(self.developer_token),
                })
            
            return result
        elif metadata_type == "customers":
            # Return customer information
            return ConnectorResult.success_result(
                data={
                    "customer_ids": self.customer_ids,
                    "active_customer_id": self.customer_id,
                    "manager_id": self.manager_id,
                }
            )
        else:
            return ConnectorResult.error_result(f"Unsupported metadata type: {metadata_type}")