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
    substations = Substation.query.all() 
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
def edit_substation(id):
    if not current_user.is_inspector():
        flash("You do not have permission to edit substations.")
        return redirect(url_for("main.dashboard"))
    substation = Substation.query.get_or_404(id)
    if request.method == "POST":
        substation.name = request.form["name"]
        substation.coverage_status = request.form["coverage_status"]
        db.session.commit()
        flash("Substation updated successfully!")
        return redirect(url_for("main.substations"))
    return render_template("edit_substation.html", substation=substation)

@main_bp.route("/delete_substation/<int:id>")
@login_required
def delete_substation(id):
    if not current_user.is_inspector():
        flash("You do not have permission to delete substations.")
        return redirect(url_for("main.dashboard"))
    substation = Substation.query.get_or_404(id)
    db.session.delete(substation)
    db.session.commit()
    flash("Substation deleted successfully!")
    return redirect(url_for("main.substations"))

@main_bp.route("/inspections")
@login_required
def inspections():
    if not current_user.is_inspector():
        flash("You do not have permission to view inspections.")
        return redirect(url_for("main.dashboard"))
    inspections = InspectionTest.query.order_by(InspectionTest.created_at.desc()).all()
    return render_template("inspections.html", inspections=inspections)

@main_bp.route("/add_inspection", methods=["GET", "POST"])
@login_required
def add_inspection():
    if not current_user.is_inspector():
        flash("You do not have permission to add inspections.")
        return redirect(url_for("main.dashboard"))
    substations = Substation.query.all()
    if request.method == "POST":
        substation_id = request.form["substation_id"]
        inspection_date_str = request.form["inspection_date"]
        testing_date_str = request.form.get("testing_date")
        inspection_status = request.form["inspection_status"]
        testing_status = request.form.get("testing_status")
        notes = request.form["notes"]

        inspection_date = datetime.strptime(inspection_date_str, "%Y-%m-%d").date()
        testing_date = datetime.strptime(testing_date_str, "%Y-%m-%d").date() if testing_date_str else None

        new_inspection = InspectionTest(
            substation_id=substation_id,
            inspection_date=inspection_date,
            testing_date=testing_date,
            inspection_status=inspection_status,
            testing_status=testing_status,
            notes=notes,
            user_id=current_user.id
        )
        db.session.add(new_inspection)
        db.session.commit()
        flash("Inspection/Test record added successfully!")
        return redirect(url_for("main.inspections"))
    return render_template("add_inspection.html", substations=substations)

@main_bp.route("/metrics")
@login_required
def metrics():
    if not current_user.is_admin():
        flash("You do not have permission to view metrics.")
        return redirect(url_for("main.dashboard"))
    
    # Weekly Trend
    _weekly_metrics = ReliabilityMetric.query.filter(ReliabilityMetric.date >= (date.today() - timedelta(weeks=12))).order_by(ReliabilityMetric.date).all()
    weekly_metrics = []
    for metric in _weekly_metrics:
        weekly_metrics.append({
            'date': metric.date.isoformat(), # Convert date to ISO format string
            'reliability_score': metric.reliability_score,
            'testing_compliance': metric.testing_compliance,
            'inspection_compliance': metric.inspection_compliance,
            'coverage_ratio': metric.coverage_ratio,
            'effective_reliability': metric.effective_reliability
        })
    
    # Monthly Trend
    _monthly_metrics = db.session.query(
        func.to_char(ReliabilityMetric.date, "YYYY-MM").label("month"),
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(days=365))).group_by("month").order_by("month").all()

    monthly_metrics = []
    for month_data in _monthly_metrics:
        monthly_metrics.append({
            'month': month_data.month,
            'avg_reliability': month_data.avg_reliability,
            'avg_testing_compliance': month_data.avg_testing_compliance,
            'avg_inspection_compliance': month_data.avg_inspection_compliance,
            'avg_coverage_ratio': month_data.avg_coverage_ratio,
            'avg_effective_reliability': month_data.avg_effective_reliability
        })

    # Yearly Trend
    _yearly_metrics = db.session.query(
        func.to_char(ReliabilityMetric.date, "YYYY").label("year"),
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(days=365*5))).group_by("year").order_by("year").all()
    
    yearly_metrics = []
    for year_data in _yearly_metrics:
        yearly_metrics.append({
            'year': year_data.year,
            'avg_reliability': year_data.avg_reliability,
            'avg_testing_compliance': year_data.avg_testing_compliance,
            'avg_inspection_compliance': year_data.avg_inspection_compliance,
            'avg_coverage_ratio': year_data.avg_coverage_ratio,
            'avg_effective_reliability': year_data.avg_effective_reliability
        })

    return render_template("metrics.html", 
                           weekly_metrics=weekly_metrics,
                           monthly_metrics=monthly_metrics,
                           yearly_metrics=yearly_metrics)
