import os
from flask import Flask
from flask_login import LoginManager
from src.extensions import db
from src.routes.main import main_bp
from src.routes.auth import auth_bp

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fire_fighting_reliability_secret_key")

    # PostgreSQL configuration for Render.com
    database_url = os.environ.get("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///fire_fighting.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize extensions
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        from src.models.user import User  # Import here to avoid circular imports
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    # Create tables and admin user within app context
    with app.app_context():
        db.create_all()
        from src.models.user import User, Role
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(username="admin", email="admin@example.com", role=Role.ADMIN)
            admin.set_password("admin123")  # Change this to a secure password
            db.session.add(admin)
            db.session.commit()
            print("Admin user created")
        
        print("Database tables created successfully")

    return app

app = create_app()

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func
from src.models.substation import db, Substation, InspectionTest, ReliabilityMetric
from src.models.user import Role
from src.forms.substation_forms import SubstationForm # <--- ADD THIS IMPORT
from src.forms.auth_forms import RegistrationForm # Keep this if you register users from main.py

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    # ... (Your existing dashboard logic remains the same) ...
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

    # Effective Reliability Calculation
    effective_reliability = (0.4 * coverage_ratio) + (0.3 * inspection_compliance) + (0.3 * testing_compliance)
    
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
                           effective_reliability=effective_reliability * 100, # Convert to percentage
                           testing_compliance=testing_compliance * 100, # Convert to percentage
                           inspection_compliance=inspection_compliance * 100, # Convert to percentage
                           coverage_data=coverage_data,
                           inspection_data=inspection_data,
                           testing_data=testing_data)

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
        flash("You do not have permission to add substations", "danger")
        return redirect(url_for("main.dashboard"))
        
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
    # Only admins and inspectors can edit substations
    if not current_user.is_inspector():
        flash("You do not have permission to edit substations", "danger")
        return redirect(url_for("main.dashboard"))
        
    substation = Substation.query.get_or_404(id)
    form = SubstationForm(obj=substation) # Pre-populate form with existing data

    if form.validate_on_submit():
        substation.name = form.name.data
        substation.coverage_status = form.coverage_status.data
        db.session.commit()
        flash("Substation updated successfully!", "success")
        return redirect(url_for("main.substations"))
    
    return render_template("edit_substation.html", form=form, substation=substation)


@main_bp.route("/inspections")
@login_required
def inspections():
    inspections = InspectionTest.query.all()
    return render_template("inspections.html", inspections=inspections)

@main_bp.route("/add_inspection", methods=["GET", "POST"])
@login_required
def add_inspection():
    # Only admins and inspectors can add inspection records
    if not current_user.is_inspector():
        flash("You do not have permission to add inspection records", "danger")
        return redirect(url_for("main.dashboard"))
    
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
            flash("Inspection record added successfully!", "success")
            return redirect(url_for("main.inspections"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding inspection record: {e}", "danger")
    
    return render_template("add_inspection.html", substations=substations)

@main_bp.route("/metrics")
@login_required
def metrics():
    # Weekly Trend
    _weekly_metrics = db.session.query(
        func.strftime("%Y-%W", ReliabilityMetric.date).label("week"),
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(weeks=12))).group_by("week").order_by("week").all()

    weekly_metrics = []
    for week_data in _weekly_metrics:
        weekly_metrics.append({
            'date': week_data.week,
            'reliability_score': week_data.avg_reliability,
            'testing_compliance': week_data.avg_testing_compliance,
            'inspection_compliance': week_data.avg_inspection_compliance,
            'coverage_ratio': week_data.avg_coverage_ratio,
            'effective_reliability': week_data.avg_effective_reliability
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
            'date': month_data.month,
            'reliability_score': month_data.avg_reliability,
            'testing_compliance': month_data.avg_testing_compliance,
            'inspection_compliance': month_data.avg_inspection_compliance,
            'coverage_ratio': month_data.avg_coverage_ratio,
            'effective_reliability': month_data.avg_effective_reliability
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
    return render_template("metrics.html",
                           weekly_metrics=weekly_metrics,
                           monthly_metrics=monthly_metrics,
                           yearly_metrics=yearly_metrics)
