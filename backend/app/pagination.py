"""
Pagination helper utilities for the Device Simulator application.
Provides standardized pagination functionality for SQLAlchemy queries.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Query


class PaginationHelper:
    """Helper class for implementing pagination in SQLAlchemy queries."""
    
    @staticmethod
    def paginate(query: Query, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        Paginate a SQLAlchemy query.
        
        Args:
            query: SQLAlchemy query object
            page: Page number (1-based)
            per_page: Number of items per page
            
        Returns:
            Dictionary containing pagination data:
            - items: List of items for current page
            - total: Total number of items
            - page: Current page number
            - per_page: Items per page
            - pages: Total number of pages
            - has_prev: Whether there's a previous page
            - has_next: Whether there's a next page
            - prev_num: Previous page number (None if no previous page)
            - next_num: Next page number (None if no next page)
        """
        # Ensure page is at least 1
        page = max(1, page)
        
        # Get total count
        total = query.count()
        
        # Calculate total pages
        pages = (total + per_page - 1) // per_page if total > 0 else 1
        
        # Ensure page doesn't exceed total pages
        page = min(page, pages)
        
        # Get items for current page
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Convert items to dictionaries if they have to_dict method
        serialized_items = []
        for item in items:
            if hasattr(item, 'to_dict'):
                serialized_items.append(item.to_dict())
            else:
                # Fallback for items without to_dict method
                serialized_items.append(item)
        
        return {
            'items': serialized_items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': pages,
            'has_prev': page > 1,
            'has_next': page < pages,
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if page < pages else None
        }
    
    @staticmethod
    def get_pagination_params(request_args: Dict[str, Any], 
                            default_per_page: int = 20, 
                            max_per_page: int = 100) -> tuple[int, int]:
        """
        Extract and validate pagination parameters from request arguments.
        
        Args:
            request_args: Request arguments dictionary
            default_per_page: Default number of items per page
            max_per_page: Maximum allowed items per page
            
        Returns:
            Tuple of (page, per_page)
        """
        page = max(1, int(request_args.get('page', 1)))
        per_page = min(max_per_page, max(1, int(request_args.get('per_page', default_per_page))))
        
        return page, per_page
    
    @staticmethod
    def create_pagination_response(items: list, 
                                 total: int, 
                                 page: int, 
                                 per_page: int,
                                 additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a standardized pagination response.
        
        Args:
            items: List of items for current page
            total: Total number of items
            page: Current page number
            per_page: Items per page
            additional_data: Optional additional data to include in response
            
        Returns:
            Standardized pagination response dictionary
        """
        pages = (total + per_page - 1) // per_page if total > 0 else 1
        
        response = {
            'items': items,
            'pagination': {
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': pages,
                'has_prev': page > 1,
                'has_next': page < pages,
                'prev_num': page - 1 if page > 1 else None,
                'next_num': page + 1 if page < pages else None
            }
        }
        
        if additional_data:
            response.update(additional_data)
            
        return response
