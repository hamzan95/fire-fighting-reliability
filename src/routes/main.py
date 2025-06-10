from flask import Blueprint, render_template, request, redirect, url_for, flash
from src.models.substation import db, Substation, InspectionTest, ReliabilityMetric
from datetime import datetime, date, timedelta
from sqlalchemy import func
from flask_login import login_required, current_user
from src.models.user import Role

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    # Calculate current metrics
    total_substations = Substation.query.count()
    
    fully_covered = Substation.query.filter_by(coverage_status="Fully Covered").count()
    partially_covered = Substation.query.filter_by(coverage_status="Partially Covered").count()
    
    inspected_substations = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.inspection_status == "Inspected").scalar()
    tested_substations = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "Tested").scalar()

    # Handle division by zero
    if total_substations == 0:
        coverage_ratio = 0
        inspection_compliance = 0
        testing_compliance = 0
    else:
        coverage_ratio = (fully_covered + partially_covered * 0.5) / total_substations
        inspection_compliance = inspected_substations / total_substations
        testing_compliance = tested_substations / total_substations

    # Effective Reliability Calculation
    effective_reliability = coverage_ratio * inspection_compliance * testing_compliance * 100

    # Store daily metric (only if there's data)
    if total_substations > 0:
        today = date.today()
        metric = ReliabilityMetric.query.filter_by(date=today).first()
        if not metric:
            metric = ReliabilityMetric(
                date=today,
                reliability_score=effective_reliability,
                testing_compliance=testing_compliance * 100,
                inspection_compliance=inspection_compliance * 100,
                coverage_ratio=coverage_ratio * 100,
                effective_reliability=effective_reliability
            )
            db.session.add(metric)
        else:
            metric.reliability_score = effective_reliability
            metric.testing_compliance = testing_compliance * 100
            metric.inspection_compliance = inspection_compliance * 100
            metric.coverage_ratio = coverage_ratio * 100
            metric.effective_reliability = effective_reliability
        db.session.commit()

    # Data for charts
    coverage_data = {
        "Fully Covered": fully_covered,
        "Partially Covered": partially_covered,
        "Not Covered": total_substations - fully_covered - partially_covered
    }
    
    inspection_data = {
        "Inspected": inspected_substations,
        "Not Inspected": total_substations - inspected_substations
    }
    
    testing_data = {
        "Tested": tested_substations,
        "Not Tested": total_substations - tested_substations
    }

    return render_template("dashboard.html", 
                           total_substations=total_substations,
                           effective_reliability=effective_reliability,
                           testing_compliance=testing_compliance * 100,
                           inspection_compliance=inspection_compliance * 100,
                           coverage_ratio=coverage_ratio * 100,
                           coverage_data=coverage_data,
                           inspection_data=inspection_data,
                           testing_data=testing_data)

@main_bp.route("/substations")
@login_required
def substations():
    if not current_user.is_inspector():
        flash("You do not have permission to view substations.")
        return redirect(url_for("main.dashboard"))
    substations = Substation.query.all()
    return render_template("substations.html", substations=substations)

@main_bp.route("/add_substation", methods=["GET", "POST"])
@login_required
def add_substation():
    if not current_user.is_inspector():
        flash("You do not have permission to add substations.")
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        name = request.form["name"]
        coverage_status = request.form["coverage_status"]
        new_substation = Substation(name=name, coverage_status=coverage_status)
        db.session.add(new_substation)
        db.session.commit()
        flash("Substation added successfully!")
        return redirect(url_for("main.substations"))
    return render_template("add_substation.html")

@main_bp.route("/edit_substation/<int:id>", methods=["GET", "POST"])
@login_required
def edit_sub

