# src/routes/main.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func
from sqlalchemy.orm import joinedload # Import joinedload for eager loading

from src.extensions import db
from src.models.substation import Substation, InspectionTest, ReliabilityMetric
from src.models.user import Role, User # Ensure User is imported
from src.forms.substation_forms import SubstationForm
from src.forms.inspection_forms import InspectionTestForm # Keep this import

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    # Calculate current metrics
    total_substations = Substation.query.count()
    
    fully_covered = Substation.query.filter_by(coverage_status="Fully Covered").count()
    partially_covered = Substation.query.filter_by(coverage_status="Partially Covered").count()
    not_covered = Substation.query.filter_by(coverage_status="Not Covered").count()

    # Calculate inspected and not inspected substations
    # Get count of distinct substations that have at least one 'Inspected' inspection
    inspected_count = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.inspection_status == "Inspected").scalar()
    if inspected_count is None: # Handle case where no inspections exist
        inspected_count = 0

    # Calculate not inspected substations by counting substations that don't have any 'Inspected' status
    # This is more accurate: check if a substation has *any* inspection, and if so, what its latest status is.
    # For chart purposes, it's simpler to consider total_substations - inspected_count if 'Inspected' implies completion.
    # If a substation has NO inspections, it's 'Not Inspected'.
    # If a substation has inspections but none are 'Inspected', it's 'Not Inspected'.
    # To be precise for the chart:
    inspected_substation_ids = db.session.query(func.distinct(InspectionTest.substation_id)).filter(InspectionTest.inspection_status == "Inspected").all()
    inspected_substation_ids = [s_id[0] for s_id in inspected_substation_ids] # Extract IDs
    
    not_inspected_substation_count = total_substations - len(inspected_substation_ids) # Correctly calculate not inspected based on substations

    # Calculate tested substations
    tested_substations_count = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "Tested").scalar()
    if tested_substations_count is None: # Handle case where no testing records exist
        tested_substations_count = 0
    
    # Handle division by zero
    if total_substations == 0:
        coverage_ratio = 0
        inspection_compliance = 0
        testing_compliance = 0
    else:
        coverage_ratio = (fully_covered / total_substations) * 100
        inspection_compliance = (len(inspected_substation_ids) / total_substations) * 100 # Use actual inspected count
        testing_compliance = (tested_substations_count / total_substations) * 100

    # Prepare data for charts
    coverage_data = {
        "Fully Covered": fully_covered,
        "Partially Covered": partially_covered,
        "Not Covered": not_covered
    }

    inspection_data = {
        "labels": ["Inspected", "Not Inspected"],
        "datasets": [{
            "data": [len(inspected_substation_ids), not_inspected_substation_count], # Corrected data
            "backgroundColor": ["#28a745", "#dc3545"] # Green for Inspected, Red for Not Inspected
        }]
    }

    testing_data = {
        "Tested": tested_substations_count,
        "Pending": db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "Pending").scalar() or 0,
        "Failed": db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "Failed").scalar() or 0,
        "N/A": db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "N/A").scalar() or 0
    }

    recent_inspections = InspectionTest.query.options(joinedload(InspectionTest.substation))\
                                            .order_by(InspectionTest.inspection_date.desc()).limit(10).all()

    total_users = User.query.count()

    return render_template("dashboard.html",
                           total_substations=total_substations,
                           effective_reliability=75.0, # Placeholder, replace with actual calculation if available
                           testing_compliance=testing_compliance,
                           inspection_compliance=inspection_compliance,
                           coverage_data=coverage_data,
                           inspection_data=inspection_data,
                           testing_data=testing_data,
                           recent_inspections=recent_inspections,
                           total_users=total_users
                           )


@main_bp.route("/substations")
@login_required
def substations():
    if not current_user.is_inspector() and not current_user.is_admin():
        flash("You do not have permission to view substations.", "danger")
        return redirect(url_for("main.dashboard"))
    
    substations = Substation.query.all()
    form = SubstationForm()
    
    substations_with_status = []
    for sub in substations:
        latest_inspection = InspectionTest.query.filter_by(substation_id=sub.id)\
                                .order_by(InspectionTest.inspection_date.desc()).first()
        sub_status = {
            "id": sub.id,
            "name": sub.name,
            "coverage_status": sub.coverage_status,
            "last_inspection_date": latest_inspection.inspection_date.strftime('%Y-%m-%d') if latest_inspection else 'N/A',
            "inspection_status": latest_inspection.inspection_status if latest_inspection else 'Not Inspected',
            "testing_status": latest_inspection.testing_status if latest_inspection else 'N/A',
            "created_at": sub.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        substations_with_status.append(sub_status)


    return render_template("substations.html", substations=substations_with_status, form=form)

@main_bp.route("/substations/add", methods=["GET", "POST"])
@login_required
def add_substation():
    if not current_user.is_admin():
        flash("You do not have permission to add substations.", "danger")
        return redirect(url_for("main.dashboard"))
    
    form = SubstationForm()
    if form.validate_on_submit():
        new_substation = Substation(name=form.name.data, coverage_status=form.coverage_status.data)
        db.session.add(new_substation)
        try:
            db.session.commit()
            flash("Substation added successfully!", "success")
            return redirect(url_for("main.substations"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding substation: {e}", "danger")
    return render_template("add_substation.html", form=form)

@main_bp.route("/substations/edit/<int:substation_id>", methods=["GET", "POST"])
@login_required
def edit_substation(substation_id):
    if not current_user.is_admin():
        flash("You do not have permission to edit substations.", "danger")
        return redirect(url_for("main.dashboard"))
    
    substation = Substation.query.get_or_404(substation_id)
    form = SubstationForm(obj=substation)

    if form.validate_on_submit():
        substation.name = form.name.data
        substation.coverage_status = form.coverage_status.data
        try:
            db.session.commit()
            flash("Substation updated successfully!", "success")
            return redirect(url_for("main.substations"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating substation: {e}", "danger")
    
    return render_template("edit_substation.html", form=form, substation_id=substation.id)

@main_bp.route("/substations/delete/<int:substation_id>", methods=["POST"])
@login_required
def delete_substation(substation_id):
    if not current_user.is_admin():
        flash("You do not have permission to delete substations.", "danger")
        return redirect(url_for("main.dashboard"))

    substation = Substation.query.get_or_404(substation_id)
    try:
        db.session.delete(substation)
        db.session.commit()
        flash("Substation deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting substation: {e}", "danger")
    return redirect(url_for("main.substations"))

@main_bp.route("/inspections")
@login_required
def inspections():
    if not current_user.is_inspector() and not current_user.is_admin():
        flash("You do not have permission to view inspections.", "danger")
        return redirect(url_for("main.dashboard"))

    all_substations = Substation.query.options(joinedload(Substation.inspections)).all()

    tested_substations = []
    not_tested_substations = []

    for sub in all_substations:
        # Get the most recent inspection for this substation by sorting in Python
        # orderBy() on the query level is removed to avoid index errors.
        latest_inspection = next(
            (i for i in sorted(sub.inspections, key=lambda x: x.inspection_date if x.inspection_date else date.min, reverse=True)),
            None
        )

        sub_data = {
            "id": sub.id,
            "name": sub.name,
            "coverage_status": sub.coverage_status,
            "latest_inspection_date": latest_inspection.inspection_date.strftime('%Y-%m-%d') if latest_inspection and latest_inspection.inspection_date else 'N/A',
            "inspection_status": latest_inspection.inspection_status if latest_inspection else 'Not Inspected',
            "testing_status": latest_inspection.testing_status if latest_inspection else 'N/A',
            "notes": latest_inspection.notes if latest_inspection else '',
            "user_recorded": latest_inspection.user.username if latest_inspection and latest_inspection.user else 'N/A',
            "created_at": sub.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

        if latest_inspection and latest_inspection.testing_status == "Tested":
            tested_substations.append(sub_data)
        else:
            not_tested_substations.append(sub_data)

    return render_template("inspections.html", 
                           tested_substations=tested_substations,
                           not_tested_substations=not_tested_substations)

@main_bp.route("/inspections/add", methods=["GET", "POST"])
@login_required
def add_inspection():
    if not current_user.is_inspector() and not current_user.is_admin():
        flash("You do not have permission to add inspections.", "danger")
        return redirect(url_for("main.dashboard"))
    
    form = InspectionTestForm()
    substations = Substation.query.all()
    form.substation_id.choices = [(s.id, s.name) for s in substations]

    if form.validate_on_submit():
        new_inspection = InspectionTest(
            substation_id=form.substation_id.data,
            inspection_date=form.inspection_date.data,
            testing_date=form.testing_date.data if form.testing_date.data else None,
            inspection_status=form.inspection_status.data,
            testing_status=form.testing_status.data,
            notes=form.notes.data,
            user_id=current_user.id
        )
        db.session.add(new_inspection)
        try:
            db.session.commit()
            flash("Inspection record added successfully!", "success")
            return redirect(url_for("main.inspections"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding inspection: {e}", "danger")
    return render_template("add_inspection.html", form=form, substations=substations)

@main_bp.route("/inspections/edit/<int:inspection_id>", methods=["GET", "POST"])
@login_required
def edit_inspection(inspection_id):
    if not current_user.is_inspector() and not current_user.is_admin():
        flash("You do not have permission to edit inspections.", "danger")
        return redirect(url_for("main.dashboard"))

    inspection = InspectionTest.query.get_or_404(inspection_id)
    form = InspectionTestForm(obj=inspection)
    substations = Substation.query.all()
    form.substation_id.choices = [(s.id, s.name) for s in substations]

    if form.validate_on_submit():
        inspection.substation_id = form.substation_id.data
        inspection.inspection_date = form.inspection_date.data
        inspection.testing_date = form.testing_date.data if form.testing_date.data else None
        inspection.inspection_status = form.inspection_status.data
        inspection.testing_status = form.testing_status.data
        inspection.notes = form.notes.data
        try:
            db.session.commit()
            flash("Inspection record updated successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating inspection: {e}", "danger")
    
    return render_template("edit_inspection.html", form=form, inspection_id=inspection.id, substations=substations)

@main_bp.route("/inspections/delete/<int:inspection_id>", methods=["POST"])
@login_required
def delete_inspection(inspection_id):
    if not current_user.is_admin():
        flash("You do not have permission to delete inspections.", "danger")
        return redirect(url_for("main.dashboard"))

    inspection = InspectionTest.query.get_or_404(inspection_id)
    try:
        db.session.delete(inspection)
        db.session.commit()
        flash("Inspection record deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting inspection: {e}", "danger")
    return redirect(url_for("main.inspections"))

@main_bp.route("/inspections/bulk_update", methods=["POST"])
@login_required
def bulk_update_inspections():
    if not current_user.is_admin() and not current_user.is_inspector():
        flash("You do not have permission to perform bulk updates.", "danger")
        return redirect(url_for("main.dashboard"))

    selected_substation_ids_str = request.form.get("selected_substation_ids")
    new_inspection_status = request.form.get("new_inspection_status")
    new_testing_status = request.form.get("new_testing_status")

    if not selected_substation_ids_str:
        flash("No substations selected for bulk update.", "warning")
        return redirect(url_for("main.inspections"))

    substation_ids = [int(s_id) for s_id in selected_substation_ids_str.split(',') if s_id.strip()]

    try:
        for sub_id in substation_ids:
            substation = Substation.query.get(sub_id)
            if substation:
                # Find the latest inspection record for this substation
                latest_inspection = InspectionTest.query.filter_by(substation_id=sub_id)\
                                                      .order_by(InspectionTest.inspection_date.desc()).first()
                
                if latest_inspection:
                    # Update existing record
                    if new_inspection_status:
                        latest_inspection.inspection_status = new_inspection_status
                    if new_testing_status:
                        latest_inspection.testing_status = new_testing_status
                    latest_inspection.user_id = current_user.id # Update who performed the change
                    latest_inspection.created_at = datetime.utcnow() # Update timestamp to reflect last modification
                else:
                    # Create a new inspection record if none exists for this substation
                    new_inspection = InspectionTest(
                        substation_id=sub_id,
                        inspection_date=date.today(), # Use current date for new entry
                        testing_date=date.today() if new_testing_status and new_testing_status != 'N/A' else None, # Set testing date if testing status is provided and not N/A
                        inspection_status=new_inspection_status or "Pending", # Default to Pending if not provided
                        testing_status=new_testing_status or "N/A", # Default to N/A if not provided
                        notes="Bulk updated",
                        user_id=current_user.id
                    )
                    db.session.add(new_inspection)
        db.session.commit()
        flash(f"Successfully updated inspection/testing records for {len(substation_ids)} substations.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error during bulk update: {e}", "danger")
    
    return redirect(url_for("main.inspections"))


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
