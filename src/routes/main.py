# src/routes/main.py
import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func
from sqlalchemy.orm import joinedload # <--- ADD THIS IMPORT

from src.extensions import db
from src.models.substation import Substation, InspectionTest, ReliabilityMetric
from src.models.user import Role
from src.forms.substation_forms import SubstationForm


main_bp = Blueprint("main", __name__)

@main_bp.route("/inspections")
@login_required
def inspections():
    # Fetch inspections with related substation and user data *eager loaded*
    inspections = InspectionTest.query.options(joinedload(InspectionTest.substation), joinedload(InspectionTest.user)).all()
    return render_template("inspections.html", inspections=inspections)

@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    total_substations = Substation.query.count()

    fully_covered = Substation.query.filter_by(coverage_status="Fully Covered").count()
    partially_covered = Substation.query.filter_by(coverage_status="Partially Covered").count()

    inspected_substations = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.inspection_status == "Inspected").scalar()
    tested_substations = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "Tested").scalar()

    if total_substations == 0:
        coverage_ratio = 0
        inspection_compliance = 0
        testing_compliance = 0
    else:
        coverage_ratio = (fully_covered + partially_covered * 0.5) / total_substations
        inspection_compliance = inspected_substations / total_substations
        testing_compliance = tested_substations / total_substations

    effective_reliability = (coverage_ratio + inspection_compliance + testing_compliance) / 3 * 100

    # Data for charts
    coverage_data = {
        "Fully Covered": fully_covered,
        "Partially Covered": partially_covered,
        "Not Covered": total_substations - fully_covered - partially_covered
    }

    inspected_count = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.inspection_status == "Inspected").scalar() or 0
    not_inspected_count = total_substations - inspected_count
    inspection_data = {
        "Inspected": inspected_count,
        "Not Inspected": not_inspected_count
    }

    tested_count = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "Tested").scalar() or 0
    not_tested_count = total_substations - tested_count
    testing_data = {
        "Tested": tested_count,
        "Not Tested": not_tested_count
    }

    return render_template("dashboard.html",
                           total_substations=total_substations,
                           effective_reliability=effective_reliability,
                           testing_compliance=testing_compliance * 100,
                           inspection_compliance=inspection_compliance * 100,
                           coverage_data=coverage_data,
                           inspection_data=inspection_data,
                           testing_data=testing_data)

@main_bp.route("/delete_substation/<int:id>", methods=["POST"])
@login_required
def delete_substation(id):
    # Restrict deletion to admin users only
    if not current_user.is_admin():
        flash("You do not have permission to delete substations.", "danger")
        return redirect(url_for("main.substations"))

    substation = Substation.query.get_or_404(id)
    try:
        db.session.delete(substation)
        db.session.commit()
        flash(f"Substation '{substation.name}' and all associated inspection records deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting substation: {e}", "danger")
    return redirect(url_for("main.substations"))

@main_bp.route("/substations")
@login_required
def substations():
    substations = Substation.query.all()
    return render_template("substations.html", substations=substations)

@main_bp.route("/add_substation", methods=["GET", "POST"])
@login_required
def add_substation():
    # Only admins and inspectors can add substations
    if not current_user.is_inspector():
        flash("You do not have permission to add substations.", "danger")
        return redirect(url_for("main.substations"))

    form = SubstationForm()
    if form.validate_on_submit():
        name = form.name.data
        coverage_status = form.coverage_status.data
        existing_substation = Substation.query.filter_by(name=name).first()
        if existing_substation:
            flash(f"Substation with name '{name}' already exists.", "danger")
        else:
            new_substation = Substation(name=name, coverage_status=coverage_status)
            db.session.add(new_substation)
            db.session.commit()
            flash("Substation added successfully!", "success")
            return redirect(url_for("main.substations"))
    return render_template("add_substation.html", form=form)

@main_bp.route("/edit_substation/<int:id>", methods=["GET", "POST"])
@login_required
def edit_substation(id):
    # Only admins and inspectors can edit substations
    if not current_user.is_inspector():
        flash("You do not have permission to edit substations.", "danger")
        return redirect(url_for("main.substations"))

    substation = Substation.query.get_or_404(id)
    form = SubstationForm(obj=substation)
    if form.validate_on_submit():
        substation.name = form.name.data
        substation.coverage_status = form.coverage_status.data
        db.session.commit()
        flash("Substation updated successfully!", "success")
        return redirect(url_for("main.substations"))
    return render_template("edit_substation.html", form=form, substation=substation)

@main_bp.route("/add_inspection", methods=["GET", "POST"])
@login_required
def add_inspection():
    # Only admins and inspectors can add inspection records
    if not current_user.is_inspector():
        flash("You do not have permission to add inspection records.", "danger")
        return redirect(url_for("main.inspections"))

    substations = Substation.query.all()
    # In a real app, you'd use a WTForm for this as well
    if request.method == "POST":
        substation_id = request.form.get("substation_id")
        inspection_date_str = request.form.get("inspection_date")
        testing_date_str = request.form.get("testing_date")
        inspection_status = request.form.get("inspection_status")
        testing_status = request.form.get("testing_status")
        notes = request.form.get("notes")

        try:
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
            flash("Inspection record added successfully!","success")
            return redirect(url_for("main.inspections"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding inspection record: {e}", "danger")

    return render_template("add_inspection.html", substations=substations)


@main_bp.route("/metrics")
@login_required
def metrics():
    # Only admins and inspectors can view metrics
    if not current_user.is_inspector():
        flash("You do not have permission to view metrics.", "danger")
        return redirect(url_for("main.dashboard"))

    # Weekly Trend
    # Using func.strftime for SQLite compatibility
    # For PostgreSQL, consider func.to_char(ReliabilityMetric.date, 'YYYY-MM-DD') for weekly and then group by week number
    weekly_metrics_raw = db.session.query(
        func.strftime("%Y-%W", ReliabilityMetric.date).label("week"), # %W for week number (00-53)
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(weeks=12))).group_by("week").order_by("week").all()

    weekly_metrics = []
    for week_data in weekly_metrics_raw:
        weekly_metrics.append({
            'date': week_data.week,
            'reliability_score': week_data.avg_reliability,
            'testing_compliance': week_data.avg_testing_compliance,
            'inspection_compliance': week_data.avg_inspection_compliance,
            'coverage_ratio': week_data.avg_coverage_ratio,
            'effective_reliability': week_data.avg_effective_reliability
        })

    # Monthly Trend
    # Using func.strftime for SQLite compatibility
    # For PostgreSQL, consider func.to_char(ReliabilityMetric.date, 'YYYY-MM')
    monthly_metrics_raw = db.session.query(
        func.strftime("%Y-%m", ReliabilityMetric.date).label("month"),
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(days=365))).group_by("month").order_by("month").all()

    monthly_metrics = []
    for month_data in monthly_metrics_raw:
        monthly_metrics.append({
            'date': month_data.month,
            'reliability_score': month_data.avg_reliability,
            'testing_compliance': month_data.avg_testing_compliance,
            'inspection_compliance': month_data.avg_inspection_compliance,
            'coverage_ratio': month_data.avg_coverage_ratio,
            'effective_reliability': month_data.avg_effective_reliability
        })

    # Yearly Trend
    # Using func.to_char for PostgreSQL compatibility
    yearly_metrics_raw = db.session.query(
        func.to_char(ReliabilityMetric.date, "YYYY").label("year"),
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(days=365*5))).group_by("year").order_by("year").all()

    yearly_metrics = []
    for year_data in yearly_metrics_raw:
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

@main_bp.route("/upload_substations", methods=["GET", "POST"])
@login_required
def upload_substations():
    # Only admins can upload substation files
    if not current_user.is_admin():
        flash("You do not have permission to upload substation files.", "danger")
        return redirect(url_for("main.substations"))

    if request.method == "POST":
        if 'file' not in request.files:
            flash("No file part", "danger")
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash("No selected file", "danger")
            return redirect(request.url)
        if file and file.filename.endswith('.csv'):
            stream = io.StringIO(file.stream.read().decode("UTF8"))
            csv_reader = csv.reader(stream)
            header = next(csv_reader, None)  # Skip header row

            if not header or 'Substation Name' not in header or 'Coverage Status' not in header:
                flash("CSV file must contain 'Substation Name' and 'Coverage Status' columns.", "danger")
                return redirect(request.url)

            try:
                name_index = header.index('Substation Name')
                coverage_index = header.index('Coverage Status')
            except ValueError as e:
                flash(f"Missing required column in CSV header: {e}. Please ensure 'Substation Name' and 'Coverage Status' columns are present.", "danger")
                return redirect(request.url)


            successful_uploads = 0
            failed_uploads = 0
            for row in csv_reader:
                if len(row) > max(name_index, coverage_index):
                    name = row[name_index].strip()
                    coverage_status = row[coverage_index].strip()

                    # Basic validation for coverage status
                    valid_statuses = ["Fully Covered", "Partially Covered", "Not Covered"]
                    if coverage_status not in valid_statuses:
                        flash(f"Invalid coverage status '{coverage_status}' for substation '{name}'. Skipping.", "warning")
                        failed_uploads += 1
                        continue

                    existing_substation = Substation.query.filter_by(name=name).first()
                    if existing_substation:
                        flash(f"Substation '{name}' already exists. Skipping.", "info")
                        failed_uploads += 1
                    else:
                        try:
                            new_substation = Substation(name=name, coverage_status=coverage_status)
                            db.session.add(new_substation)
                            db.session.commit()
                            successful_uploads += 1
                        except Exception as e:
                            db.session.rollback()
                            flash(f"Error adding substation '{name}': {e}", "danger")
                            failed_uploads += 1
                else:
                    flash(f"Skipping row due to insufficient data: {row}", "warning")
                    failed_uploads += 1

            if successful_uploads > 0:
                flash(f"Successfully uploaded {successful_uploads} substation(s).", "success")
            if failed_uploads > 0:
                flash(f"{failed_uploads} substation(s) failed to upload or were skipped.", "warning")

            return redirect(url_for("main.substations"))
        else:
            flash("Invalid file type. Please upload a CSV file.", "danger")
            return redirect(request.url)

    return render_template("upload_substations.html")

