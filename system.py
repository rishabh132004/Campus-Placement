import json # Import json module for data serialization
import csv # Import csv module for report generation
import os # Import os module for file path operations
from models import Student, Company, PlacementDrive, Interview, JobOffer # Import data models
from utils import * # Import custom exceptions, decorators, and utilities

class CampusPlacementSystem: # Main class to manage the placement system
    # Class Attribute
    total_placements_institution_wide = 0 # Track total placements across the institution

    def __init__(self): # Constructor to initialize the system state
        self.students = {} # Dictionary to store student objects with student_id as key
        self.companies = {} # Dictionary to store company objects with company_id as key
        self.drives = [] # List to store all placement drive records
        self.interviews = [] # List to store all scheduled interview objects
        self.interview_schedules = [] # List of tuples to store fixed schedules
        self.offers = [] # List to store job offer objects
        self.reports = [] # List to store generated report metadata
        
        # Define paths relative to this script directory for deployment environments
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_file = os.path.join(self.base_dir, 'data.json')
        self.report_file = os.path.join(self.base_dir, 'student_report.csv')

    @log_action("Student Registration") # Decorator to log the registration process
    def register_student(self, student_data): # Method to add a new student
        student_id = student_data.get("student_id") # Extract student ID from data
        if student_id in self.students: # Check for existing registration
            raise DuplicateRegistration(f"Student ID {student_id} already exists.") # Raise error if duplicate
        
        try: # Validate CGPA input
            cgpa = float(student_data.get("cgpa", 0.0)) # Convert CGPA to float
            if cgpa < 0 or cgpa > 10.0: # Check valid range
                raise InvalidCGPAEntry("CGPA must be between 0 and 10.") # Raise error for out of range
        except ValueError: # Handle non-numeric CGPA
            raise InvalidCGPAEntry("Invalid CGPA format.") # Raise error for bad format
            
        try: # Validate backlogs input
            backlogs = int(student_data.get("backlogs", 0))
            if backlogs < 0:
                raise ValueError()
            student_data["backlogs"] = backlogs
        except ValueError:
            raise IncorrectUserInput("Backlogs must be a non-negative integer.")

        student = Student(**student_data) # Instantiate Student object using unpacked dictionary
        self.students[student_id] = student # Store student in the dictionary
        print(f"Successfully registered student: {student.name}") # Confirm registration

    def register_company(self, company_data): # Method to add a new company
        company_id = company_data.get("company_id") # Extract company ID
        if company_id in self.companies: # Check for existing registration
            raise DuplicateRegistration(f"Company ID {company_id} already exists.") # Raise error if duplicate
            
        # Parse required_skills if it's a comma-separated string
        req_skills = company_data.get("required_skills")
        if isinstance(req_skills, str):
            company_data["required_skills"] = [s.strip() for s in req_skills.split(",") if s.strip()]
            
        try:
            max_backlogs = int(company_data.get("max_backlogs_allowed", 0))
            if max_backlogs < 0:
                raise ValueError()
            company_data["max_backlogs_allowed"] = max_backlogs
        except ValueError:
            raise IncorrectUserInput("Max backlogs allowed must be a non-negative integer.")
        
        company = Company(**company_data) # Instantiate Company object
        self.companies[company_id] = company # Store company in the dictionary
        print(f"Successfully registered company: {company.company_name}") # Confirm registration

    @log_action("Drive Creation") # Decorator to log drive creation
    def create_drive(self, drive_data): # Method to initiate a placement drive
        company_id = drive_data.get("company") # Extract company ID associated with drive
        if company_id not in self.companies: # Validate company existence
            raise InvalidCompanyID(f"Company ID {company_id} not found.") # Raise error if missing
        
        drive = PlacementDrive(**drive_data) # Instantiate PlacementDrive object
        self.drives.append(drive) # Add drive to the system list
        print(f"Successfully created drive for {self.companies[company_id].company_name}") # Confirm creation

    def check_eligibility(self, student_id, company_id): # Method to verify student eligibility
        if student_id not in self.students: # Validate student existence
            raise InvalidStudentID(f"Student ID {student_id} not found.") # Raise error if missing
        if company_id not in self.companies: # Validate company existence
            raise InvalidCompanyID(f"Company ID {company_id} not found.") # Raise error if missing
            
        student = self.students[student_id] # Retrieve student object
        company = self.companies[company_id] # Retrieve company object
        
        # 1. CGPA Verification
        if not Utils.check_eligibility(student.cgpa, company.eligibility_cgpa):
            raise StudentNotEligible(f"Student {student.name} is not eligible for {company.company_name} (Requires {company.eligibility_cgpa} CGPA, has {student.cgpa})")
            
        # 2. Backlog Verification
        if student.backlogs > company.max_backlogs_allowed:
            raise StudentNotEligible(f"Student {student.name} has {student.backlogs} backlog(s). {company.company_name} allows maximum {company.max_backlogs_allowed} backlog(s).")
            
        # 3. Skill Matching
        if company.required_skills:
            student_skills_lower = {s.lower().strip() for s in student.skills}
            company_skills_lower = {s.lower().strip() for s in company.required_skills}
            overlap = student_skills_lower.intersection(company_skills_lower)
            if not overlap:
                required_str = ", ".join(company.required_skills)
                raise StudentNotEligible(f"Student {student.name} lacks required skills. {company.company_name} requires: [{required_str}]")
                
        return True

    def schedule_interviews(self, interview_data): # Method to record an interview session
        student_id = interview_data.get("student") # Extract student ID
        company_id = interview_data.get("company") # Extract company ID
        
        if student_id not in self.students: # Validate student
            raise InvalidStudentID(f"Student ID {student_id} not found.") # Raise error if missing
        if company_id not in self.companies: # Validate company
            raise InvalidCompanyID(f"Company ID {company_id} not found.") # Raise error if missing
            
        interview = Interview(**interview_data) # Instantiate Interview object
        self.interviews.append(interview) # Add to system interviews list
        print(f"Scheduled interview for Student {student_id} with Company {company_id}") # Confirm scheduling

    @log_action("Offer Generation") # Decorator to log offer generation
    def generate_offer(self, offer_data): # Method to issue a job offer
        student_id = offer_data.get("student") # Extract student ID
        company_id = offer_data.get("company") # Extract company ID
        
        if student_id not in self.students: # Validate student
            raise InvalidStudentID(f"Student ID {student_id} not found.") # Raise error if missing
        if company_id not in self.companies: # Validate company
            raise InvalidCompanyID(f"Company ID {company_id} not found.") # Raise error if missing
            
        offer = JobOffer(**offer_data) # Instantiate JobOffer object
        self.offers.append(offer) # Add to system offers list
        
        self.students[student_id].placement_status = "Placed" # Update student's status to Placed
        CampusPlacementSystem.increment_placements() # Increment the global placement counter
            
        print(f"Generated offer for Student {student_id}") # Confirm offer generation

    @classmethod # Class method to modify class-level attribute
    def increment_placements(cls): # Method to increase placement count
        cls.total_placements_institution_wide += 1 # Increment the static counter

    @classmethod # Class method to access class-level attribute
    def generate_institution_wide_stats(cls): # Method to get total placement count
        return f"Total Institutional Placements: {cls.total_placements_institution_wide}" # Return formatted string

    @log_action("Report Generation") # Decorator to log report generation
    def generate_reports(self): # Method to export system data to CSV
        # 1. Student Placement Report
        with open(self.report_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Student ID', 'Name', 'Email', 'Branch', 'CGPA', 'Backlogs', 'Skills', 'Status', 'Resume Link'])
            for s in self.students.values():
                writer.writerow([s.student_id, s.name, s.email, s.branch, s.cgpa, s.backlogs, ", ".join(s.skills), s.placement_status, s.resume_url])
        print(f"Generated Student Placement Report: {self.report_file}")
        
        # 2. Company Recruitment Report
        company_report = os.path.join(self.base_dir, 'company_report.csv')
        with open(company_report, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Company ID', 'Company Name', 'Job Role', 'Package (LPA)', 'Min CGPA', 'Max Backlogs', 'Required Skills', 'Offers Made'])
            for c in self.companies.values():
                offers_count = sum(1 for o in self.offers if o.company == c.company_id)
                writer.writerow([c.company_id, c.company_name, c.job_role, c.package, c.eligibility_cgpa, c.max_backlogs_allowed, ", ".join(c.required_skills), offers_count])
        print(f"Generated Company Recruitment Report: {company_report}")
                
        # 3. Placement Statistics Report
        stats_report = os.path.join(self.base_dir, 'placement_stats_report.csv')
        with open(stats_report, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Metric', 'Value'])
            total_students = len(self.students)
            placed_count = sum(1 for s in self.students.values() if s.placement_status == "Placed")
            placement_pct = (placed_count / total_students * 100) if total_students > 0 else 0.0
            packages = [o.package for o in self.offers]
            highest_package = max(packages, default=0.0)
            avg_package = Utils.calculate_average_package(packages)
            
            writer.writerow(['Total Students', total_students])
            writer.writerow(['Placed Students', placed_count])
            writer.writerow(['Placement Percentage (%)', f"{placement_pct:.2f}%"])
            writer.writerow(['Highest Package (LPA)', highest_package])
            writer.writerow(['Average Package (LPA)', f"{avg_package:.2f}"])
            writer.writerow([])
            writer.writerow(['Branch', 'Total Students', 'Placed Students', 'Placement Rate (%)', 'Highest Package (LPA)', 'Average Package (LPA)'])
            
            branch_stats = self.get_branch_stats()
            for branch, stat in branch_stats.items():
                writer.writerow([
                    branch, 
                    stat['total'], 
                    stat['placed'], 
                    f"{stat['placement_rate']:.2f}%", 
                    stat['highest_package'], 
                    f"{stat['avg_package']:.2f}"
                ])
        print(f"Generated Placement Statistics Report: {stats_report}")
                
        # 4. Offer Summary Report
        offer_report = os.path.join(self.base_dir, 'offer_summary_report.csv')
        with open(offer_report, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Offer ID', 'Student ID', 'Student Name', 'Company ID', 'Company Name', 'Package (LPA)', 'Status'])
            for o in self.offers:
                s = self.students.get(o.student)
                s_name = s.name if s else "Unknown Student"
                c = self.companies.get(o.company)
                c_name = c.company_name if c else "Unknown Company"
                writer.writerow([o.offer_id, o.student, s_name, o.company, c_name, o.package, o.offer_status])
        print(f"Generated Offer Summary Report: {offer_report}")

    def save_data(self): # Method to persist all system data to a JSON file
        data = { # Create a dictionary structure to hold all system objects
            "students": {k: v.to_dict() for k, v in self.students.items()}, # Convert student objects to dictionaries
            "companies": {k: v.to_dict() for k, v in self.companies.items()}, # Convert company objects to dictionaries
            "drives": [d.to_dict() for d in self.drives], # Convert drive objects to list of dicts
            "interviews": [i.to_dict() for i in self.interviews], # Convert interview objects to list of dicts
            "offers": [o.to_dict() for o in self.offers] # Convert offer objects to list of dicts
        }
        with open(self.data_file, 'w') as f: # Open JSON file for writing
            json.dump(data, f, indent=4) # Write serialized data with indentation
        print(f"Data saved successfully to {self.data_file}.") # Confirm data save

    def load_data(self): # Method to load system data from JSON file
        if not os.path.exists(self.data_file): # Check if data file exists
            print("No saved data found.") # Inform user if file is missing
            return # Exit method
            
        try: # Start error handling for file reading
            with open(self.data_file, 'r') as f: # Open JSON file for reading
                data = json.load(f) # Parse JSON data into dictionary
                
            self.students = {k: Student.from_dict(v) for k, v in data.get("students", {}).items()} # Reconstruct student objects
            self.companies = {k: Company.from_dict(v) for k, v in data.get("companies", {}).items()} # Reconstruct company objects
            self.drives = [PlacementDrive.from_dict(v) for v in data.get("drives", [])] # Reconstruct drive objects
            self.interviews = [Interview.from_dict(v) for v in data.get("interviews", [])] # Reconstruct interview objects
            self.offers = [JobOffer.from_dict(v) for v in data.get("offers", [])] # Reconstruct offer objects
            
            CampusPlacementSystem.total_placements_institution_wide = sum(1 for s in self.students.values() if s.placement_status == "Placed") # Recalculate global placement count
            print(f"Data loaded successfully from {self.data_file}.") # Confirm data load
        except Exception as e: # Catch any errors during loading
            print(f"Error loading data: {e}") # Print error message

    def search_student_recursive(self, student_ids, target_id, index=0): # Recursive function to find a student by ID
        if index >= len(student_ids): # Base case: index out of bounds
            return None # Student not found
        if student_ids[index] == target_id: # Base case: ID matches
            return self.students[target_id] # Return the student object
        return self.search_student_recursive(student_ids, target_id, index + 1) # Recursive call with next index
        
    def get_students_sorted_by_cgpa(self): # Method to get students sorted by performance
        return sorted(self.students.values(), key=lambda s: s.cgpa, reverse=True) # Return list sorted by CGPA descending
        
    def get_companies_sorted_by_package(self): # Method to get companies sorted by salary
        return sorted(self.companies.values(), key=lambda c: c.package, reverse=True) # Return list sorted by package descending
        
    def get_eligible_students(self, min_cgpa): # Method to filter students by CGPA
        return [s for s in self.students.values() if s.cgpa >= min_cgpa] # Return list of students meeting criteria using list comprehension

    def get_branch_stats(self): # Method to calculate statistics per branch
        stats = {}
        for s in self.students.values():
            branch = s.branch
            if branch not in stats:
                stats[branch] = {
                    'total': 0,
                    'placed': 0,
                    'packages': []
                }
            stats[branch]['total'] += 1
            if s.placement_status == "Placed":
                stats[branch]['placed'] += 1
                
        for o in self.offers:
            # We only track accepted or pending offers, but package is offered anyway
            # Let's verify student branch
            s = self.students.get(o.student)
            if s:
                branch = s.branch
                if branch in stats:
                    stats[branch]['packages'].append(o.package)
                    
        results = {}
        for branch, data in stats.items():
            total = data['total']
            placed = data['placed']
            rate = (placed / total * 100) if total > 0 else 0.0
            highest = max(data['packages'], default=0.0)
            avg = Utils.calculate_average_package(data['packages'])
            results[branch] = {
                'total': total,
                'placed': placed,
                'placement_rate': round(rate, 2),
                'highest_package': round(highest, 2),
                'avg_package': round(avg, 2)
            }
        return results
