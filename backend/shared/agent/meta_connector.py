"""
Meta (Facebook/Instagram) connector implementation for the Supertrack platform.

This connector provides access to Meta's Graph API for both advertising
and organic data from Facebook and Instagram.
"""

import logging
import json
import asyncio
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


class MetaAPIVersion(str, Enum):
    """Meta Graph API versions."""
    V18 = "v18.0"
    V17 = "v17.0"
    V16 = "v16.0"
    V15 = "v15.0"
    V14 = "v14.0"
    LATEST = "v18.0"  # Alias for the latest version


class MetaProductType(str, Enum):
    """Meta product types for data access."""
    FACEBOOK_ADS = "facebook_ads"
    INSTAGRAM_ADS = "instagram_ads"
    FACEBOOK_ORGANIC = "facebook_organic"
    INSTAGRAM_ORGANIC = "instagram_organic"


class MetaConnector(OAuth2Connector):
    """
    Connector for Meta platforms (Facebook and Instagram).
    
    This connector provides access to:
    - Facebook Ads data via the Marketing API
    - Instagram Ads data via the Marketing API
    - Facebook organic page data via the Graph API
    - Instagram organic profile data via the Graph API
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
        Initialize the Meta connector.
        
        Args:
            session_id: Optional ID for the session
            options: Optional configuration options
            model: OpenAI model instance
            tenant_id: ID of the tenant
            user_id: ID of the user
            connection_config: Configuration for the Meta connection
            system_prompt: Custom system prompt
        """
        # Set default Meta API configuration
        if connection_config:
            api_version = connection_config.params.get("api_version", MetaAPIVersion.LATEST)
            
            # Set Meta-specific OAuth2 URLs
            connection_config.params.setdefault("authorization_endpoint", "https://www.facebook.com/v18.0/dialog/oauth")
            connection_config.params.setdefault("token_endpoint", f"https://graph.facebook.com/{api_version}/oauth/access_token")
            connection_config.params.setdefault("api_base_url", f"https://graph.facebook.com/{api_version}")
            
            # Set default flow type
            connection_config.params.setdefault("flow_type", OAuth2FlowType.AUTHORIZATION_CODE)
            
            # Set default scopes for different product types
            product_types = connection_config.params.get("product_types", [])
            scopes = connection_config.params.get("scopes", [])
            
            if not scopes:
                default_scopes = set(["public_profile"])
                
                for product_type in product_types:
                    if product_type == MetaProductType.FACEBOOK_ADS:
                        default_scopes.update([
                            "ads_management",
                            "ads_read",
                            "business_management",
                            "read_insights",
                        ])
                    elif product_type == MetaProductType.INSTAGRAM_ADS:
                        default_scopes.update([
                            "ads_management",
                            "ads_read",
                            "business_management",
                            "instagram_basic",
                            "instagram_manage_insights",
                            "read_insights",
                        ])
                    elif product_type == MetaProductType.FACEBOOK_ORGANIC:
                        default_scopes.update([
                            "pages_read_engagement",
                            "pages_read_user_content",
                            "pages_show_list",
                            "read_insights",
                        ])
                    elif product_type == MetaProductType.INSTAGRAM_ORGANIC:
                        default_scopes.update([
                            "instagram_basic",
                            "instagram_manage_insights",
                            "pages_show_list",
                            "read_insights",
                        ])
                
                connection_config.params["scopes"] = list(default_scopes)
        
        # Initialize the OAuth2 connector with Meta-specific prompt
        super().__init__(
            session_id=session_id,
            options=options,
            model=model,
            tenant_id=tenant_id,
            user_id=user_id,
            connection_config=connection_config,
            system_prompt=system_prompt or self._get_meta_prompt(),
        )
        
        # Meta-specific state
        self.ad_accounts = {}
        self.pages = {}
        self.instagram_accounts = {}
        self.selected_account_id = None
        self.selected_page_id = None
        self.selected_instagram_id = None
    
    def _get_meta_prompt(self) -> str:
        """
        Get the system prompt for the Meta connector.
        
        Returns:
            System prompt
        """
        return """
        You are an AI assistant working within the Supertrack AI Platform. Your role is to help users 
        connect to and interact with Meta platforms (Facebook and Instagram). Follow these guidelines:
        
        1. Help users establish connections to Meta APIs
        2. Assist with retrieving data from Facebook and Instagram
        3. Format API responses in a clear and useful way
        4. Provide guidance on available endpoints and functionality
        5. Handle API errors and provide troubleshooting assistance
        
        You can help with:
        1. Configuring Meta API connections with proper authentication
        2. Retrieving advertising data from Facebook Ads Manager
        3. Accessing organic content from Facebook Pages
        4. Retrieving Instagram profile data and insights
        5. Building complex queries for Meta's Graph API
        
        Please provide clear, structured guidance regarding Meta API functionality,
        data retrieval, and any error messages that occur.
        """
    
    async def connect(self) -> ConnectorResult:
        """
        Connect to the Meta Graph API.
        
        Returns:
            Result of the connection attempt
        """
        # Use OAuth2 connector's connect method
        result = await super().connect()
        
        if not result.success:
            return result
        
        # For successful connections, retrieve available accounts
        if self.connection_config.status == ConnectionStatus.CONNECTED:
            return await self._initialize_account_data()
        
        return result
    
    async def _initialize_account_data(self) -> ConnectorResult:
        """
        Initialize account data after successful connection.
        
        Returns:
            Result with account information
        """
        try:
            # Load Meta-specific configuration
            product_types = self.connection_config.params.get("product_types", [])
            
            # Get user ID
            me_result = await self.query(path="/me", params={"fields": "id,name"})
            
            if not me_result.success:
                return me_result
            
            user_id = me_result.data.get("id")
            user_name = me_result.data.get("name")
            
            if not user_id:
                return ConnectorResult.error_result("Failed to retrieve user ID")
            
            # Fetch relevant account data based on product types
            accounts_data = {
                "user_id": user_id,
                "user_name": user_name,
            }
            
            # Get ad accounts if needed
            if (MetaProductType.FACEBOOK_ADS in product_types or 
                MetaProductType.INSTAGRAM_ADS in product_types):
                ad_accounts_result = await self.query(
                    path=f"/{user_id}/adaccounts",
                    params={"fields": "id,name,account_id,account_status,business,currency,timezone_name"}
                )
                
                if ad_accounts_result.success and "data" in ad_accounts_result.data:
                    self.ad_accounts = {
                        account["id"]: account for account in ad_accounts_result.data["data"]
                    }
                    accounts_data["ad_accounts"] = ad_accounts_result.data["data"]
            
            # Get pages if needed
            if MetaProductType.FACEBOOK_ORGANIC in product_types:
                pages_result = await self.query(
                    path=f"/{user_id}/accounts",
                    params={"fields": "id,name,access_token,category,fan_count,verification_status"}
                )
                
                if pages_result.success and "data" in pages_result.data:
                    self.pages = {
                        page["id"]: page for page in pages_result.data["data"]
                    }
                    accounts_data["pages"] = pages_result.data["data"]
            
            # Get Instagram accounts if needed
            if MetaProductType.INSTAGRAM_ORGANIC in product_types:
                # First need to get pages, then Instagram accounts connected to pages
                if not self.pages:
                    pages_result = await self.query(
                        path=f"/{user_id}/accounts",
                        params={"fields": "id,name,access_token"}
                    )
                    
                    if pages_result.success and "data" in pages_result.data:
                        self.pages = {
                            page["id"]: page for page in pages_result.data["data"]
                        }
                
                instagram_accounts = []
                
                for page_id in self.pages:
                    ig_accounts_result = await self.query(
                        path=f"/{page_id}/instagram_accounts",
                        params={"fields": "id,username,profile_pic,name"}
                    )
                    
                    if ig_accounts_result.success and "data" in ig_accounts_result.data:
                        for account in ig_accounts_result.data["data"]:
                            account["page_id"] = page_id
                            instagram_accounts.append(account)
                            self.instagram_accounts[account["id"]] = account
                
                if instagram_accounts:
                    accounts_data["instagram_accounts"] = instagram_accounts
            
            return ConnectorResult.success_result(
                data=accounts_data,
                metadata={
                    "product_types": product_types,
                    "ad_accounts_count": len(self.ad_accounts),
                    "pages_count": len(self.pages),
                    "instagram_accounts_count": len(self.instagram_accounts),
                }
            )
        except Exception as e:
            logger.error(f"Error initializing Meta account data: {str(e)}")
            return ConnectorResult.error_result(f"Error initializing Meta account data: {str(e)}")
    
    async def set_active_account(self, account_type: str, account_id: str) -> ConnectorResult:
        """
        Set the active account for subsequent operations.
        
        Args:
            account_type: Type of account ('ad_account', 'page', 'instagram')
            account_id: ID of the account to set as active
            
        Returns:
            Result of the operation
        """
        try:
            if account_type == "ad_account":
                if account_id not in self.ad_accounts:
                    return ConnectorResult.error_result(f"Ad account {account_id} not found")
                
                self.selected_account_id = account_id
                
                return ConnectorResult.success_result(
                    data={"message": f"Ad account {account_id} set as active"},
                    metadata={"account": self.ad_accounts[account_id]}
                )
            elif account_type == "page":
                if account_id not in self.pages:
                    return ConnectorResult.error_result(f"Page {account_id} not found")
                
                self.selected_page_id = account_id
                
                return ConnectorResult.success_result(
                    data={"message": f"Page {account_id} set as active"},
                    metadata={"account": self.pages[account_id]}
                )
            elif account_type == "instagram":
                if account_id not in self.instagram_accounts:
                    return ConnectorResult.error_result(f"Instagram account {account_id} not found")
                
                self.selected_instagram_id = account_id
                
                return ConnectorResult.success_result(
                    data={"message": f"Instagram account {account_id} set as active"},
                    metadata={"account": self.instagram_accounts[account_id]}
                )
            else:
                return ConnectorResult.error_result(f"Invalid account type: {account_type}")
        except Exception as e:
            logger.error(f"Error setting active account: {str(e)}")
            return ConnectorResult.error_result(f"Error setting active account: {str(e)}")
    
    async def get_ads_insights(self, params: Dict[str, Any]) -> ConnectorResult:
        """
        Get insights for Facebook/Instagram ads.
        
        Args:
            params: Parameters for the insights query
                - time_range: Dictionary with 'since' and 'until' dates
                - fields: List of metrics to retrieve
                - breakdowns: List of dimensions to break down by
                - level: Level of data (ad, adset, campaign, account)
                - filtering: List of filters to apply
                
        Returns:
            Result containing ads insights data
        """
        if not self.selected_account_id:
            return ConnectorResult.error_result("No ad account selected")
        
        try:
            # Default parameters
            time_range = params.get("time_range", {
                "since": (time.strftime("%Y-%m-%d", time.localtime(time.time() - 30*86400))),
                "until": (time.strftime("%Y-%m-%d", time.localtime())),
            })
            
            fields = params.get("fields", [
                "impressions",
                "clicks",
                "spend",
                "reach",
                "cpm",
                "cpc",
                "conversions",
            ])
            
            level = params.get("level", "account")
            breakdowns = params.get("breakdowns", [])
            filtering = params.get("filtering", [])
            
            # Build API parameters
            api_params = {
                "time_range": json.dumps(time_range),
                "fields": ",".join(fields),
                "level": level,
            }
            
            if breakdowns:
                api_params["breakdowns"] = ",".join(breakdowns)
            
            if filtering:
                api_params["filtering"] = json.dumps(filtering)
            
            # Make API request
            path = f"/{self.selected_account_id}/insights"
            
            result = await self.query(path=path, params=api_params)
            
            if not result.success:
                return result
            
            # Add account information
            account_info = self.ad_accounts.get(self.selected_account_id, {})
            
            # Add some helpful metadata
            return ConnectorResult.success_result(
                data=result.data,
                metadata={
                    "account_id": self.selected_account_id,
                    "account_name": account_info.get("name"),
                    "time_range": time_range,
                    "level": level,
                }
            )
        except Exception as e:
            logger.error(f"Error retrieving ads insights: {str(e)}")
            return ConnectorResult.error_result(f"Error retrieving ads insights: {str(e)}")
    
    async def get_campaigns(self, params: Dict[str, Any]) -> ConnectorResult:
        """
        Get campaigns from the selected ad account.
        
        Args:
            params: Parameters for the campaigns query
                - status: Filter by status
                - fields: List of fields to retrieve
                - limit: Number of results to return
                
        Returns:
            Result containing campaigns data
        """
        if not self.selected_account_id:
            return ConnectorResult.error_result("No ad account selected")
        
        try:
            # Default parameters
            status = params.get("status", ["ACTIVE", "PAUSED"])
            fields = params.get("fields", [
                "id", 
                "name", 
                "status", 
                "objective", 
                "created_time", 
                "start_time", 
                "stop_time", 
                "daily_budget",
                "lifetime_budget",
                "buying_type",
                "special_ad_categories",
            ])
            limit = params.get("limit", 100)
            
            # Build API parameters
            api_params = {
                "fields": ",".join(fields),
                "limit": limit,
            }
            
            if status:
                if isinstance(status, list):
                    api_params["effective_status"] = json.dumps(status)
                else:
                    api_params["effective_status"] = f'["{status}"]'
            
            # Make API request
            path = f"/{self.selected_account_id}/campaigns"
            
            result = await self.query(path=path, params=api_params)
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving campaigns: {str(e)}")
            return ConnectorResult.error_result(f"Error retrieving campaigns: {str(e)}")
    
    async def get_ad_sets(self, params: Dict[str, Any]) -> ConnectorResult:
        """
        Get ad sets from the selected ad account.
        
        Args:
            params: Parameters for the ad sets query
                - campaign_id: Optional campaign ID to filter by
                - status: Filter by status
                - fields: List of fields to retrieve
                - limit: Number of results to return
                
        Returns:
            Result containing ad sets data
        """
        if not self.selected_account_id:
            return ConnectorResult.error_result("No ad account selected")
        
        try:
            # Default parameters
            campaign_id = params.get("campaign_id")
            status = params.get("status", ["ACTIVE", "PAUSED"])
            fields = params.get("fields", [
                "id", 
                "name", 
                "status", 
                "campaign_id", 
                "daily_budget", 
                "lifetime_budget",
                "targeting",
                "created_time",
                "start_time",
                "end_time",
                "bid_strategy",
                "billing_event",
                "optimization_goal",
            ])
            limit = params.get("limit", 100)
            
            # Build API parameters
            api_params = {
                "fields": ",".join(fields),
                "limit": limit,
            }
            
            if status:
                if isinstance(status, list):
                    api_params["effective_status"] = json.dumps(status)
                else:
                    api_params["effective_status"] = f'["{status}"]'
            
            # Make API request - either from ad account or campaign
            if campaign_id:
                path = f"/{campaign_id}/adsets"
            else:
                path = f"/{self.selected_account_id}/adsets"
            
            result = await self.query(path=path, params=api_params)
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving ad sets: {str(e)}")
            return ConnectorResult.error_result(f"Error retrieving ad sets: {str(e)}")
    
    async def get_ads(self, params: Dict[str, Any]) -> ConnectorResult:
        """
        Get ads from the selected ad account.
        
        Args:
            params: Parameters for the ads query
                - campaign_id: Optional campaign ID to filter by
                - adset_id: Optional ad set ID to filter by
                - status: Filter by status
                - fields: List of fields to retrieve
                - limit: Number of results to return
                
        Returns:
            Result containing ads data
        """
        if not self.selected_account_id:
            return ConnectorResult.error_result("No ad account selected")
        
        try:
            # Default parameters
            campaign_id = params.get("campaign_id")
            adset_id = params.get("adset_id")
            status = params.get("status", ["ACTIVE", "PAUSED"])
            fields = params.get("fields", [
                "id", 
                "name", 
                "status", 
                "adset_id", 
                "campaign_id", 
                "created_time", 
                "updated_time",
                "creative",
                "tracking_specs",
                "bid_amount",
            ])
            limit = params.get("limit", 100)
            
            # Build API parameters
            api_params = {
                "fields": ",".join(fields),
                "limit": limit,
            }
            
            if status:
                if isinstance(status, list):
                    api_params["effective_status"] = json.dumps(status)
                else:
                    api_params["effective_status"] = f'["{status}"]'
            
            # Make API request
            if adset_id:
                path = f"/{adset_id}/ads"
            elif campaign_id:
                path = f"/{campaign_id}/ads"
            else:
                path = f"/{self.selected_account_id}/ads"
            
            result = await self.query(path=path, params=api_params)
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving ads: {str(e)}")
            return ConnectorResult.error_result(f"Error retrieving ads: {str(e)}")
    
    async def get_page_posts(self, params: Dict[str, Any]) -> ConnectorResult:
        """
        Get posts from the selected Facebook page.
        
        Args:
            params: Parameters for the posts query
                - fields: List of fields to retrieve
                - limit: Number of results to return
                - since: Optional date filter (YYYY-MM-DD)
                - until: Optional date filter (YYYY-MM-DD)
                
        Returns:
            Result containing page posts data
        """
        if not self.selected_page_id:
            return ConnectorResult.error_result("No Facebook page selected")
        
        try:
            # Default parameters
            fields = params.get("fields", [
                "id", 
                "message", 
                "created_time", 
                "permalink_url", 
                "type", 
                "shares", 
                "likes.summary(true)",
                "comments.summary(true)",
                "insights.metric(post_impressions,post_impressions_unique,post_reactions_by_type_total)",
            ])
            limit = params.get("limit", 25)
            since = params.get("since")
            until = params.get("until")
            
            # Build API parameters
            api_params = {
                "fields": ",".join(fields),
                "limit": limit,
            }
            
            if since:
                api_params["since"] = since
            
            if until:
                api_params["until"] = until
            
            # Make API request
            path = f"/{self.selected_page_id}/posts"
            
            result = await self.query(path=path, params=api_params)
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving page posts: {str(e)}")
            return ConnectorResult.error_result(f"Error retrieving page posts: {str(e)}")
    
    async def get_page_insights(self, params: Dict[str, Any]) -> ConnectorResult:
        """
        Get insights for the selected Facebook page.
        
        Args:
            params: Parameters for the insights query
                - metrics: List of metrics to retrieve
                - period: Period for the data (day, week, days_28, month, lifetime)
                - since: Optional date filter (YYYY-MM-DD)
                - until: Optional date filter (YYYY-MM-DD)
                
        Returns:
            Result containing page insights data
        """
        if not self.selected_page_id:
            return ConnectorResult.error_result("No Facebook page selected")
        
        try:
            # Default parameters
            metrics = params.get("metrics", [
                "page_impressions",
                "page_impressions_unique",
                "page_engaged_users",
                "page_post_engagements",
                "page_fans",
                "page_fan_adds",
                "page_views_total",
            ])
            period = params.get("period", "day")
            since = params.get("since")
            until = params.get("until")
            
            # Build API parameters
            api_params = {
                "metric": ",".join(metrics),
                "period": period,
            }
            
            if since:
                api_params["since"] = since
            
            if until:
                api_params["until"] = until
            
            # Make API request
            path = f"/{self.selected_page_id}/insights"
            
            result = await self.query(path=path, params=api_params)
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving page insights: {str(e)}")
            return ConnectorResult.error_result(f"Error retrieving page insights: {str(e)}")
    
    async def get_instagram_media(self, params: Dict[str, Any]) -> ConnectorResult:
        """
        Get media from the selected Instagram account.
        
        Args:
            params: Parameters for the media query
                - fields: List of fields to retrieve
                - limit: Number of results to return
                
        Returns:
            Result containing Instagram media data
        """
        if not self.selected_instagram_id:
            return ConnectorResult.error_result("No Instagram account selected")
        
        try:
            # Default parameters
            fields = params.get("fields", [
                "id", 
                "caption", 
                "media_type", 
                "media_url", 
                "permalink", 
                "thumbnail_url", 
                "timestamp",
                "username",
                "like_count",
                "comments_count",
                "insights.metric(impressions,reach,engagement)",
            ])
            limit = params.get("limit", 25)
            
            # Build API parameters
            api_params = {
                "fields": ",".join(fields),
                "limit": limit,
            }
            
            # Make API request
            path = f"/{self.selected_instagram_id}/media"
            
            result = await self.query(path=path, params=api_params)
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving Instagram media: {str(e)}")
            return ConnectorResult.error_result(f"Error retrieving Instagram media: {str(e)}")
    
    async def get_instagram_insights(self, params: Dict[str, Any]) -> ConnectorResult:
        """
        Get insights for the selected Instagram account.
        
        Args:
            params: Parameters for the insights query
                - metrics: List of metrics to retrieve
                - period: Period for the data (day, week, days_28, lifetime)
                - since: Optional date filter (YYYY-MM-DD)
                - until: Optional date filter (YYYY-MM-DD)
                
        Returns:
            Result containing Instagram insights data
        """
        if not self.selected_instagram_id:
            return ConnectorResult.error_result("No Instagram account selected")
        
        try:
            # Default parameters
            metrics = params.get("metrics", [
                "impressions",
                "reach",
                "profile_views",
                "follower_count",
                "website_clicks",
                "email_contacts",
                "get_directions_clicks",
                "phone_call_clicks",
                "text_message_clicks",
            ])
            period = params.get("period", "day")
            since = params.get("since")
            until = params.get("until")
            
            # Build API parameters
            api_params = {
                "metric": ",".join(metrics),
                "period": period,
            }
            
            if since:
                api_params["since"] = since
            
            if until:
                api_params["until"] = until
            
            # Make API request
            path = f"/{self.selected_instagram_id}/insights"
            
            result = await self.query(path=path, params=api_params)
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving Instagram insights: {str(e)}")
            return ConnectorResult.error_result(f"Error retrieving Instagram insights: {str(e)}")
    
    async def execute(self, **kwargs) -> ConnectorResult:
        """
        Execute a Meta-specific operation.
        
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
            
            # Meta-specific operations
            if operation == "set_active_account":
                return await self.set_active_account(
                    account_type=params.get("account_type"),
                    account_id=params.get("account_id"),
                )
            elif operation == "get_ads_insights":
                return await self.get_ads_insights(params)
            elif operation == "get_campaigns":
                return await self.get_campaigns(params)
            elif operation == "get_ad_sets":
                return await self.get_ad_sets(params)
            elif operation == "get_ads":
                return await self.get_ads(params)
            elif operation == "get_page_posts":
                return await self.get_page_posts(params)
            elif operation == "get_page_insights":
                return await self.get_page_insights(params)
            elif operation == "get_instagram_media":
                return await self.get_instagram_media(params)
            elif operation == "get_instagram_insights":
                return await self.get_instagram_insights(params)
            else:
                return ConnectorResult.error_result(f"Unsupported Meta operation: {operation}")
        except Exception as e:
            logger.error(f"Error executing Meta operation: {str(e)}")
            return ConnectorResult.error_result(f"Error executing Meta operation: {str(e)}")
    
    async def get_metadata(self, **kwargs) -> ConnectorResult:
        """
        Get metadata about the Meta connection.
        
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
                # Add Meta-specific metadata
                result.data["data"].update({
                    "selected_ad_account": self.selected_account_id,
                    "selected_page": self.selected_page_id,
                    "selected_instagram_account": self.selected_instagram_id,
                    "ad_accounts_count": len(self.ad_accounts),
                    "pages_count": len(self.pages),
                    "instagram_accounts_count": len(self.instagram_accounts),
                    "product_types": self.connection_config.params.get("product_types", []),
                    "api_version": self.connection_config.params.get("api_version", MetaAPIVersion.LATEST),
                })
            
            return result
        elif metadata_type == "accounts":
            # Return account information
            return ConnectorResult.success_result(
                data={
                    "ad_accounts": list(self.ad_accounts.values()),
                    "pages": list(self.pages.values()),
                    "instagram_accounts": list(self.instagram_accounts.values()),
                    "selected_ad_account": self.selected_account_id,
                    "selected_page": self.selected_page_id,
                    "selected_instagram_account": self.selected_instagram_id,
                }
            )
        else:
            return ConnectorResult.error_result(f"Unsupported metadata type: {metadata_type}")