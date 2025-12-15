import logging
from typing import Optional

class TaxonomyTool():

    def __init__(self):
        logging.info("Initializing TaxonomyTool")
        
        
        # Define domain hint mappings
        self.domain_hints = {
            "Workshops": {
                "description": "Workshop and event metadata",
                "terms": ["Workshop", "WorkshopID", "WorkshopName", "location_id"],
                "common_filters": ["location_id"]
            },
            "Locations": {
                "description": "Location details for workshops",
                "terms": ["Location", "LocationID", "City", "State", "Country"],
                "common_filters": ["Country", "State"]
            },
            "Payments": {
                "description": "Payment and benefits information",
                "terms": ["Payment", "Short Term Incentive (STI)", "Bonus", "Salary", "HealthInsurance"],
                "common_filters": ["Salary", "Bonus"]
            }
        }

    def list_all_domains(self) -> str:
        """List all domain categories with descriptions and common filters.
        
        Returns:
            Formatted string with all domain information.
        """
        logging.info("Listing all domain categories")
        
        result = "Domain Categories:\n\n"
        
        for domain_name, domain_info in self.domain_hints.items():
            result += f"{domain_name}: {domain_info['description']}\n"
            result += f"  Common filters: {', '.join(domain_info['common_filters'])}\n\n"
        
        return result

    def get_domain_hints(self, table_name: Optional[str] = None) -> str:
        """Get domain hints for a specific table or all tables.
        
        Args:
            table_name: Optional table name to get hints for. If None, returns all hints.
            
        Returns:
            Comma-separated string of domain hints.
        """
        logging.info("Fetching domain hints for table: %s", table_name)
        
        if table_name is None:
            # Return all hints
            all_hints = []
            for domain in self.domain_hints.values():
                all_hints.extend(domain["terms"])
            return ", ".join(all_hints)
        
        # Return hints for specific table
        domain = self.domain_hints.get(table_name)
        if domain:
            return ", ".join(domain["terms"])
        else:
            logging.warning(f"No domain hints found for table: {table_name}")
            return ""
    
    def get_term_hints(self, search_term: str) -> str:
        """Search for hints related to a specific term or keyword.
        
        Args:
            search_term: The term to search for in domain hints.
            
        Returns:
            Formatted string with relevant domain information.
        """
        logging.info("Searching for term: %s", search_term)
        
        search_lower = search_term.lower()
        results = []
        
        for domain_name, domain_info in self.domain_hints.items():
            # Check if term matches any hints in this domain
            matching_terms = [
                term for term in domain_info["terms"]
                if search_lower in term.lower()
            ]
            
            if matching_terms:
                result = f"\n{domain_name}: {domain_info['description']}\n"
                result += f"  Matching terms: {', '.join(matching_terms)}\n"
                result += f"  Common filters: {', '.join(domain_info['common_filters'])}"
                results.append(result)
        
        if not results:
            return f"No domain hints found for term: '{search_term}'"
        
        return "\n".join(results)

    
    def get_all_query_hints(self) -> str:
        """Get all query hints including joins, key conditions, and table purposes.
        
        Returns:
            Formatted string with comprehensive query hints.
        """
        logging.info("Fetching all query hints")
        
        result = "Comprehensive Query Hints:\n\n"
        
        return result

  
