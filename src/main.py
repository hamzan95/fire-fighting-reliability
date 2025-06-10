# src/routes/main.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func
from sqlalchemy.orm import joinedload # Import joinedload for eager loading

from src.extensions import db
from src.models.substation import Substation, InspectionTest, ReliabilityMetric
from src.models.user import Role
from src.forms.substation_forms import SubstationForm # Assuming this is used for add/edit substation

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
        inspection_compliance = (inspected_substations / total_substations) * 100 if inspected_substations is not None else 0
        testing_compliance = (tested_substations / total_substations) * 100 if tested_substations is not None else 0

    # Effective Reliability Calculation - Example (adjust as per your actual formula)
    # This is a placeholder; refine based on what "effective reliability" truly means in your context.
    effective_reliability = (coverage_ratio * 0.4 + (inspection_compliance / 100) * 0.3 + (testing_compliance / 100) * 0.3) * 100
    
    # Data for charts (assuming you pass these to dashboard.html for Chart.js)
    coverage_data = {
        "Fully Covered": fully_covered,
        "Partially Covered": partially_covered,
        "Not Covered": total_substations - fully_covered - partially_covered
    }
    
    inspected_count = InspectionTest.query.filter_by(inspection_status="Inspected").count()
    not_inspected_count = InspectionTest.query.filter_by(inspection_status="Not Inspected").count()
    # If a substation has no inspection records, it's implicitly 'Not Inspected' for the purpose of the chart
    # This calculation needs to be more robust if you want to include all substations
    inspection_data = {
        "Inspected": inspected_count,
        "Not Inspected": not_inspected_count
    }

    tested_count = InspectionTest.query.filter_by(testing_status="Tested").count()
    not_tested_count = InspectionTest.query.filter_by(testing_status="Not Tested").count()
    testing_data = {
        "Tested": tested_count,
        "Not Tested": not_tested_count
    }

    return render_template("dashboard.html",
                           total_substations=total_substations,
                           effective_reliability=effective_reliability,
                           testing_compliance=testing_compliance,
                           inspection_compliance=inspection_compliance,
                           coverage_data=coverage_data,
                           inspection_data=inspection_data,
                           testing_data=testing_data)

@main_bp.route("/substations")
@login_required
def substations():
    _substations = Substation.query.all()
    return render_template("substations.html", substations=_substations)

@main_bp.route("/add_substation", methods=["GET", "POST"])
@login_required
def add_substation():
    if not current_user.is_inspector():
        flash("You do not have permission to add substations.", "danger")
        return redirect(url_for("main.substations"))

    form = SubstationForm()
    if form.validate_on_submit():
        new_substation = Substation(name=form.name.data, coverage_status=form.coverage_status.data)
        db.session.add(new_substation)
        db.session.commit()
        flash("Substation added successfully!", "success")
        return redirect(url_for("main.substations"))
    return render_template("add_substation.html", form=form)

@main_bp.route("/edit_substation/<int:id>", methods=["GET", "POST"])
@login_required
def edit_substation(id):
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

@main_bp.route("/delete_substation/<int:id>", methods=["POST"])
@login_required
def delete_substation(id):
    if not current_user.is_admin():
        flash("You do not have permission to delete substations.", "danger")
        return redirect(url_for("main.substations"))

    substation = Substation.query.get_or_404(id)
    try:
        # Delete associated inspection records first
        InspectionTest.query.filter_by(substation_id=substation.id).delete()
        db.session.delete(substation)
        db.session.commit()
        flash("Substation and all associated inspection records deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting substation: {e}", "danger")
    return redirect(url_for("main.substations"))

@main_bp.route("/inspections")
@login_required
def inspections():
    # Fetch inspections with related substation and user data eager loaded
    inspections = InspectionTest.query.options(joinedload(InspectionTest.substation), joinedload(InspectionTest.user)).all()
    return render_template("inspections.html", inspections=inspections)

@main_bp.route("/add_inspection", methods=["GET", "POST"])
@login_required
def add_inspection():
    if not current_user.is_inspector():
        flash("You do not have permission to add inspection records.", "danger")
        return redirect(url_for("main.inspections"))
    
    substations = Substation.query.all()
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
            flash("Inspection record added successfully!", "success")
            return redirect(url_for("main.inspections"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding inspection record: {e}", "danger")
    
    return render_template("add_inspection.html", substations=substations)

@main_bp.route("/metrics")
@login_required
def metrics():
    # Ensure current_user is available and has necessary attributes
    if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
        flash("Please log in to access metrics.", "warning")
        return redirect(url_for("auth.login"))

    # Only admins and inspectors can view metrics
    if not (current_user.is_admin() or current_user.is_inspector()):
        flash("You do not have permission to view metrics.", "danger")
        return redirect(url_for("main.dashboard"))


    # Weekly Trend (Last 12 Weeks)
    # Cast date to DATE for proper grouping and ordering in PostgreSQL
    weekly_metrics_raw = db.session.query(
        func.to_char(ReliabilityMetric.date, "YYYY-MM-DD").label("date"),
        ReliabilityMetric.reliability_score,
        ReliabilityMetric.testing_compliance,
        ReliabilityMetric.inspection_compliance,
        ReliabilityMetric.coverage_ratio,
        ReliabilityMetric.effective_reliability
    ).filter(
        ReliabilityMetric.date >= (date.today() - timedelta(weeks=12))
    ).order_by(ReliabilityMetric.date).all()

    weekly_metrics = []
    for week_data in weekly_metrics_raw:
        weekly_metrics.append({
            'date': week_data.date,
            'reliability_score': week_data.reliability_score,
            'testing_compliance': week_data.testing_compliance,
            'inspection_compliance': week_data.inspection_compliance,
            'coverage_ratio': week_data.coverage_ratio,
            'effective_reliability': week_data.effective_reliability
        })

    # Monthly Trend (Last 12 Months)
    # Using func.to_char for PostgreSQL compatibility
    monthly_metrics_raw = db.session.query(
        func.to_char(ReliabilityMetric.date, "YYYY-MM").label("month"),
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(
        ReliabilityMetric.date >= (date.today() - timedelta(days=30*12)) # Approximately 12 months
    ).group_by("month").order_by("month").all()
    
    monthly_metrics = []
    for month_data in monthly_metrics_raw:
        monthly_metrics.append({
            'month': month_data.month,
            'avg_reliability': month_data.avg_reliability,
            'avg_testing_compliance': month_data.avg_testing_compliance,
            'avg_inspection_compliance': month_data.avg_inspection_compliance,
            'avg_coverage_ratio': month_data.avg_coverage_ratio,
            'avg_effective_reliability': month_data.avg_effective_reliability
        })

    # Yearly Trend (Last 5 Years)
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

@main_bp.route("/import_substations", methods=["GET", "POST"])
@login_required
def import_substations():
    # Only admins can import substations
    if not current_user.is_admin():
        flash("You do not have permission to import substations.", "danger")
        return redirect(url_for("main.dashboard"))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            try:
                # Read CSV using pandas
                df = pd.read_csv(file)
                
                # Assuming CSV has 'name' and 'coverage_status' columns
                # Add validation for columns and data types if necessary
                
                imported_count = 0
                for index, row in df.iterrows():
                    name = row['name']
                    coverage_status = row['coverage_status']
                    
                    # Check if substation already exists
                    existing_substation = Substation.query.filter_by(name=name).first()
                    if not existing_substation:
                        new_substation = Substation(name=name, coverage_status=coverage_status)
                        db.session.add(new_substation)
                        imported_count += 1
                    else:
                        flash(f"Substation '{name}' already exists and was skipped.", "info")

                db.session.commit()
                flash(f"Successfully imported {imported_count} new substations!", "success")
                return redirect(url_for("main.substations"))
            except Exception as e:
                db.session.rollback()
                flash(f"Error importing CSV: {e}", "danger")
        else:
            flash('Invalid file type. Please upload a CSV file.', 'danger')
            
    return render_template("import_substations.html")

@main_bp.route("/reset_substation_ids", methods=["POST"])
@login_required
def reset_substation_ids():
    if not current_user.is_admin():
        flash("You do not have permission to reset substation IDs.", "danger")
        return redirect(url_for("main.dashboard"))
    
    try:
        # Delete all records from related tables first to avoid foreign key constraints
        # Ensure to delete from children tables before parent tables
        InspectionTest.query.delete()
        Substation.query.delete()
        ReliabilityMetric.query.delete() # Assuming reliability metrics are related to substations or generated based on them

        # Reset the auto-increment sequence for PostgreSQL if you are using it
        # This part is highly database-specific. For SQLite, it's usually handled automatically or not needed as directly.
        # For PostgreSQL, you'd execute raw SQL:
        # from sqlalchemy.sql import text
        # db.session.execute(text("ALTER SEQUENCE substation_id_seq RESTART WITH 1;"))
        # db.session.execute(text("ALTER SEQUENCE inspectiontest_id_seq RESTART WITH 1;"))
        # db.session.execute(text("ALTER SEQUENCE reliabilitymetric_id_seq RESTART WITH 1;"))

        db.session.commit()
        flash("All substation and inspection records have been deleted and IDs reset.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error resetting substation IDs: {e}", "danger")
    
    return redirect(url_for("main.substations"))

@main_bp.route("/bulk_edit_substations", methods=["POST"])
@login_required
def bulk_edit_substations():
    if not current_user.is_inspector(): # Only inspectors and admins can bulk edit
        flash("You do not have permission to perform bulk edits on substations.", "danger")
        return redirect(url_for("main.substations"))

    selected_ids_str = request.form.get("selected_substation_ids")
    new_coverage_status = request.form.get("new_coverage_status")

    if not selected_ids_str:
        flash("No substations selected for bulk edit.", "warning")
        return redirect(url_for("main.substations"))
    
    if not new_coverage_status:
        flash("No new coverage status selected.", "warning")
        return redirect(url_for("main.substations"))

    try:
        substation_ids = [int(s_id) for s_id in selected_ids_str.split(',') if s_id.strip()]
        
        # Perform the bulk update
        # Using synchronize_session='fetch' or False can affect how SQLAlchemy handles existing objects in session
        # 'evaluate' (default) might not work well with .in_() for updates
        # 'fetch' reloads affected objects, 'False' assumes objects are not in session or handles them manually
        num_updated = db.session.query(Substation).filter(Substation.id.in_(substation_ids)).update(
            {"coverage_status": new_coverage_status},
            synchronize_session='fetch'
        )
        db.session.commit()
        flash(f"Successfully updated coverage status for {num_updated} substations to '{new_coverage_status}'.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error during bulk edit: {e}", "danger")
    
    return redirect(url_for("main.substations"))
