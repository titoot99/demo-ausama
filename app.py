import os
import secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.csrf import CSRFError
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, PasswordField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length
from dotenv import load_dotenv

load_dotenv()
app=Flask(__name__)
app.config["SECRET_KEY"]=os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///"+os.path.join(os.path.dirname(__file__),"instance","service.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False
app.config["SESSION_COOKIE_HTTPONLY"]=True
app.config["SESSION_COOKIE_SAMESITE"]="Lax"
app.config["SESSION_COOKIE_SECURE"]=os.getenv("SESSION_COOKIE_SECURE","0")=="1"
db=SQLAlchemy(app); csrf=CSRFProtect(app)

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(80),unique=True,nullable=False)
    password_hash=db.Column(db.String(255),nullable=False)

class ServiceOrder(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(160),nullable=False)
    address=db.Column(db.String(255),nullable=False)
    description=db.Column(db.Text,nullable=False)
    priority=db.Column(db.String(20),nullable=False,default="medium")
    status=db.Column(db.String(20),nullable=False,default="new")
    created_at=db.Column(db.DateTime,default=datetime.utcnow,nullable=False)

class LoginForm(FlaskForm):
    username=StringField("اسم المستخدم",validators=[DataRequired(),Length(max=80)])
    password=PasswordField("كلمة المرور",validators=[DataRequired(),Length(min=6,max=128)])

class OrderForm(FlaskForm):
    title=StringField("العنوان",validators=[DataRequired(),Length(max=160)])
    address=StringField("العنوان التفصيلي",validators=[DataRequired(),Length(max=255)])
    description=TextAreaField("الوصف",validators=[DataRequired(),Length(max=5000)])
    priority=SelectField("الأولوية",choices=[("low","منخفضة"),("medium","متوسطة"),("high","عالية"),("urgent","عاجلة")],default="medium")
    status=SelectField("الحالة",choices=[("new","جديد"),("in_progress","قيد التنفيذ"),("completed","مكتمل")],default="new")

def current_user():
    uid=session.get("user_id")
    return db.session.get(User,uid) if uid else None

@app.context_processor
def inject_user(): return {"current_user":current_user()}

def login_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped(*args,**kwargs):
        if not current_user(): return redirect(url_for("login",next=request.path))
        return view(*args,**kwargs)
    return wrapped

@app.cli.command("init-db")
def init_db():
    os.makedirs(os.path.join(os.path.dirname(__file__),"instance"),exist_ok=True)
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin",password_hash=generate_password_hash(os.getenv("ADMIN_PASSWORD","ChangeMe123!"))))
    if ServiceOrder.query.count()==0:
        samples=[
          ("تسرب ماء","بابل - الحلة","فحص مضخة الخزان","urgent","new"),
          ("عطل كهربائي","بغداد - الكرادة","لوحة التوزيع لا تعمل","high","in_progress"),
          ("صيانة مكيف","بابل - الحلة","تنظيف وفحص الوحدة","medium","completed"),
          ("إصلاح شبكة","بابل - المحاويل","انقطاع في نقطة الشبكة","high","new"),
          ("صيانة مولدة","بغداد - الدورة","فحص الزيت والبطارية","medium","in_progress"),
          ("إصلاح باب","بابل - الحلة","استبدال القفل","low","completed")]
        db.session.add_all([ServiceOrder(title=a,address=b,description=c,priority=d,status=e) for a,b,c,d,e in samples])
    db.session.commit()

@app.route("/login",methods=["GET","POST"])
def login():
    if current_user(): return redirect(url_for("dashboard"))
    form=LoginForm()
    if form.validate_on_submit():
        user=User.query.filter_by(username=form.username.data.strip()).first()
        if user and check_password_hash(user.password_hash,form.password.data):
            session.clear(); session["user_id"]=user.id
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("بيانات الدخول غير صحيحة","danger")
    return render_template("login.html",form=form)

@app.post("/logout")
@login_required
def logout():
    session.clear(); return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    q=request.args.get("q","").strip(); status=request.args.get("status",""); priority=request.args.get("priority","")
    query=ServiceOrder.query
    if q: query=query.filter(db.or_(ServiceOrder.title.contains(q),ServiceOrder.address.contains(q),ServiceOrder.description.contains(q)))
    if status: query=query.filter_by(status=status)
    if priority: query=query.filter_by(priority=priority)
    orders=query.order_by(ServiceOrder.created_at.desc()).all()
    return render_template("dashboard.html",orders=orders,stats={
        "total":ServiceOrder.query.count(),"new":ServiceOrder.query.filter_by(status="new").count(),
        "in_progress":ServiceOrder.query.filter_by(status="in_progress").count(),
        "completed":ServiceOrder.query.filter_by(status="completed").count()})

@app.route("/orders/new",methods=["GET","POST"])
@login_required
def new_order():
    form=OrderForm()
    if form.validate_on_submit():
        db.session.add(ServiceOrder(title=form.title.data,address=form.address.data,description=form.description.data,priority=form.priority.data,status=form.status.data))
        db.session.commit(); flash("تمت إضافة الطلب","success"); return redirect(url_for("dashboard"))
    return render_template("order_form.html",form=form,title="طلب صيانة جديد")

@app.route("/orders/<int:order_id>/edit",methods=["GET","POST"])
@login_required
def edit_order(order_id):
    order=db.get_or_404(ServiceOrder,order_id); form=OrderForm(obj=order)
    if form.validate_on_submit():
        form.populate_obj(order); db.session.commit(); flash("تم تحديث الطلب","success"); return redirect(url_for("dashboard"))
    return render_template("order_form.html",form=form,title=f"تعديل الطلب #{order.id}")

@app.post("/orders/<int:order_id>/delete")
@login_required
def delete_order(order_id):
    order=db.get_or_404(ServiceOrder,order_id); db.session.delete(order); db.session.commit()
    flash("تم حذف الطلب","success"); return redirect(url_for("dashboard"))

@app.errorhandler(CSRFError)
def csrf_error(e): return "CSRF validation failed",400

with app.app_context():
    os.makedirs(os.path.join(os.path.dirname(__file__),"instance"),exist_ok=True)
    db.create_all()
