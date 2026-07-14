"""
==============================================
  Flask REST API - Campus Placement System
==============================================
This file creates a web server that connects 
the frontend (HTML/CSS/JS) to the existing 
Python backend (system.py, models.py, utils.py).

Each API endpoint maps to a CampusPlacementSystem method.
"""

from flask import Flask, render_template, request, jsonify
from system import CampusPlacementSystem
from utils import (
    InvalidStudentID, InvalidCompanyID,
    StudentNotEligible, DuplicateRegistration,
    InvalidCGPAEntry, Utils
)

# ── Initialize Flask App ──────────────────────
app = Flask(__name__)

# Create a single instance of the placement system
# This is shared across all API requests
cps = CampusPlacementSystem()
cps.load_data()  # Load any previously saved data on startup


# ══════════════════════════════════════════════
#  PAGE ROUTE - Serves the frontend
# ══════════════════════════════════════════════

@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('index.html')


# ══════════════════════════════════════════════
#  STUDENT API ENDPOINTS
# ══════════════════════════════════════════════

@app.route('/api/students', methods=['GET'])
def get_students():
    """Get all students sorted by CGPA (highest first)"""
    students = cps.get_students_sorted_by_cgpa()
    return jsonify([s.to_dict() for s in students])


@app.route('/api/students', methods=['POST'])
def register_student():
    """Register a new student from JSON request body"""
    try:
        data = request.get_json()
        # Split comma-separated skills into a list
        if isinstance(data.get('skills'), str):
            data['skills'] = [s.strip() for s in data['skills'].split(',')]
        cps.register_student(data)
        cps.save_data()
        return jsonify({"success": True, "message": f"Student '{data.get('name')}' registered!"})
    except (DuplicateRegistration, InvalidCGPAEntry, IncorrectUserInput) as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/students/search/<student_id>', methods=['GET'])
def search_student(student_id):
    """Search for a student using recursive search algorithm"""
    student_ids = list(cps.students.keys())
    student = cps.search_student_recursive(student_ids, student_id)
    if student:
        return jsonify({"success": True, "student": student.to_dict()})
    return jsonify({"success": False, "message": "Student not found"}), 404


# ══════════════════════════════════════════════
#  COMPANY API ENDPOINTS
# ══════════════════════════════════════════════

@app.route('/api/companies', methods=['GET'])
def get_companies():
    """Get all companies sorted by package (highest first)"""
    companies = cps.get_companies_sorted_by_package()
    return jsonify([c.to_dict() for c in companies])


@app.route('/api/companies', methods=['POST'])
def register_company():
    """Register a new recruiting company"""
    try:
        data = request.get_json()
        cps.register_company(data)
        cps.save_data()
        return jsonify({"success": True, "message": f"Company '{data.get('company_name')}' registered!"})
    except (DuplicateRegistration, IncorrectUserInput) as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ══════════════════════════════════════════════
#  PLACEMENT DRIVE API ENDPOINTS
# ══════════════════════════════════════════════

@app.route('/api/drives', methods=['GET'])
def get_drives():
    """Get all placement drives"""
    return jsonify([d.to_dict() for d in cps.drives])


@app.route('/api/drives', methods=['POST'])
def create_drive():
    """Create a new placement drive for a company"""
    try:
        data = request.get_json()
        cps.create_drive(data)
        cps.save_data()
        return jsonify({"success": True, "message": "Drive created successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


# ══════════════════════════════════════════════
#  ELIGIBILITY CHECK API
# ══════════════════════════════════════════════

@app.route('/api/eligibility', methods=['POST'])
def check_eligibility():
    """Check if a student meets a company's CGPA requirement"""
    try:
        data = request.get_json()
        result = cps.check_eligibility(data['student_id'], data['company_id'])
        return jsonify({"eligible": True, "message": "Student is eligible! ✅"})
    except StudentNotEligible as e:
        return jsonify({"eligible": False, "message": str(e)})
    except (InvalidStudentID, InvalidCompanyID) as e:
        return jsonify({"eligible": False, "message": str(e)}), 404


# ══════════════════════════════════════════════
#  INTERVIEW API ENDPOINTS
# ══════════════════════════════════════════════

@app.route('/api/interviews', methods=['GET'])
def get_interviews():
    """Get all scheduled interviews"""
    return jsonify([i.to_dict() for i in cps.interviews])


@app.route('/api/interviews', methods=['POST'])
def schedule_interview():
    """Schedule a new interview between student and company"""
    try:
        data = request.get_json()
        cps.schedule_interviews(data)
        cps.save_data()
        return jsonify({"success": True, "message": "Interview scheduled!"})
    except (InvalidStudentID, InvalidCompanyID) as e:
        return jsonify({"success": False, "message": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ══════════════════════════════════════════════
#  JOB OFFER API ENDPOINTS
# ══════════════════════════════════════════════

@app.route('/api/offers', methods=['GET'])
def get_offers():
    """Get all job offers"""
    return jsonify([o.to_dict() for o in cps.offers])


@app.route('/api/offers', methods=['POST'])
def generate_offer():
    """Generate a job offer for a student"""
    try:
        data = request.get_json()
        cps.generate_offer(data)
        cps.save_data()
        return jsonify({"success": True, "message": "Job offer generated!"})
    except (InvalidStudentID, InvalidCompanyID) as e:
        return jsonify({"success": False, "message": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/offers/<offer_id>/status', methods=['POST'])
def update_offer_status(offer_id):
    """Accept or reject a job offer"""
    try:
        data = request.get_json()
        status = data.get("status") # "Accepted" or "Rejected"
        if status not in ["Accepted", "Rejected"]:
            return jsonify({"success": False, "message": "Invalid status. Must be 'Accepted' or 'Rejected'."}), 400
            
        # Find the offer in the list
        offer = None
        for o in cps.offers:
            if o.offer_id == offer_id:
                offer = o
                break
                
        if not offer:
            return jsonify({"success": False, "message": "Offer not found."}), 404
            
        if status == "Accepted":
            offer.accept_offer()
            if offer.student in cps.students:
                cps.students[offer.student].placement_status = "Placed"
        else:
            offer.reject_offer()
            # Verify if student has other accepted offers
            has_other_accepted = False
            for other_o in cps.offers:
                if other_o.student == offer.student and other_o.offer_id != offer_id and other_o.offer_status == "Accepted":
                    has_other_accepted = True
                    break
            if offer.student in cps.students:
                cps.students[offer.student].placement_status = "Placed" if has_other_accepted else "Not Placed"
                
        # Recalculate static placement count
        CampusPlacementSystem.total_placements_institution_wide = sum(1 for s in cps.students.values() if s.placement_status == "Placed")
        
        cps.save_data()
        return jsonify({"success": True, "message": f"Offer {offer_id} marked as {status}!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ══════════════════════════════════════════════
#  STATISTICS API
# ══════════════════════════════════════════════

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Calculate and return all placement statistics"""
    total_students = len(cps.students)
    total_companies = len(cps.companies)
    placed = len([s for s in cps.students.values() if s.placement_status == "Placed"])
    packages = [o.package for o in cps.offers]

    return jsonify({
        "total_students": total_students,
        "total_companies": total_companies,
        "placed_students": placed,
        "not_placed": total_students - placed,
        "placement_pct": round((placed / total_students * 100) if total_students > 0 else 0, 2),
        "total_drives": len(cps.drives),
        "total_interviews": len(cps.interviews),
        "total_offers": len(cps.offers),
        "highest_package": max(packages, default=0),
        "avg_package": round(Utils.calculate_average_package(packages), 2),
        "branch_stats": cps.get_branch_stats()
    })


# ══════════════════════════════════════════════
#  REPORT & DATA MANAGEMENT API
# ══════════════════════════════════════════════

@app.route('/api/reports', methods=['POST'])
def generate_report():
    """Generate a CSV report of all student data"""
    try:
        cps.generate_reports()
        return jsonify({"success": True, "message": "Report saved to student_report.csv"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/data/save', methods=['POST'])
def save_data():
    """Save all system data to data.json"""
    try:
        cps.save_data()
        return jsonify({"success": True, "message": "Data saved!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/data/load', methods=['POST'])
def load_data():
    """Reload data from data.json"""
    try:
        cps.load_data()
        return jsonify({"success": True, "message": "Data loaded!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ══════════════════════════════════════════════
#  START THE SERVER
# ══════════════════════════════════════════════

if __name__ == '__main__':
    print("\n=== Campus Placement Management System ===")
    print("    Open http://localhost:5000 in your browser\n")
    app.run(debug=True, port=5000)
