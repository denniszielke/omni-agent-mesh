import logging
from typing import Optional

class TaxonomyTool():

    def __init__(self):
        logging.info("Initializing TaxonomyTool")
        
        
        # Define domain hint mappings based on available agent capabilities
        self.domain_hints = {
            "OfficeLocations": {
                "description": "Company office locations and location-specific news",
                "terms": ["office", "location", "St. Louis", "London", "Berlin", "Leverkusen", "site", "facilities"],
                "common_filters": ["location", "city"]
            },
            "Departments": {
                "description": "Company departments and department news",
                "terms": ["department", "team", "HR", "Finance", "Engineering", "Marketing", "Sales", "Customer Support", "IT", "Legal", "Operations", "R&D", "organization", "structure"],
                "common_filters": ["department"]
            },
            "IntranetNews": {
                "description": "Company news, announcements, and updates",
                "terms": ["news", "announcements", "updates", "events", "initiatives"],
                "common_filters": ["location", "department"]
            },
            "VacationLeave": {
                "description": "Vacation days, leave policies, and time-off entitlements",
                "terms": ["vacation", "leave", "time-off", "PTO", "BUrlG", "statutory leave", "parental leave", "sabbatical", "unpaid leave", "carry over", "entitlement"],
                "common_filters": ["leave_type", "country"]
            },
            "PerformanceCareer": {
                "description": "Performance evaluations, promotions, and career development",
                "terms": ["performance", "evaluation", "promotion", "training", "mentorship", "tuition", "career", "development", "programs"],
                "common_filters": ["evaluation_type"]
            },
            "CompensationBenefits": {
                "description": "Salary, bonuses, incentives, and employee benefits",
                "terms": ["salary", "payment", "bonus", "incentive", "overtime", "expense", "reimbursement", "health benefits", "retirement", "compensation", "benefits"],
                "common_filters": ["benefit_type"]
            },
            "HRPolicies": {
                "description": "HR policies, workplace guidelines, and compliance",
                "terms": ["HR", "policy", "working hours", "remote work", "dress code", "complaint", "harassment", "violation", "conflict resolution", "workplace", "guidelines"],
                "common_filters": ["policy_type"]
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

  
