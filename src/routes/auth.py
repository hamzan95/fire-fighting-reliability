from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from src.models.user import User, db, Role
from werkzeug.urls import url_parse
from src.forms.auth_forms import LoginForm, RegistrationForm

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("auth.login"))
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("main.dashboard")
        return redirect(next_page)
    
    return render_template("login.html", title="Sign In", form=form)

@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

@auth_bp.route("/register", methods=["GET", "POST"])
@login_required
def register():
    # Only admins can register new users
    if not current_user.is_admin():
        flash("You do not have permission to register new users")
        return redirect(url_for("main.dashboard"))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role=form.role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f"User {form.username.data} has been registered")
        return redirect(url_for("auth.users"))
    
    return render_template("register.html", title="Register User", form=form)

@auth_bp.route("/users")
@login_required
def users():
    # Only admins can view user list
    if not current_user.is_admin():
        flash("You do not have permission to view users")
        return redirect(url_for("main.dashboard"))
    
    users = User.query.all()
    return render_template("users.html", title="Users", users=users)

