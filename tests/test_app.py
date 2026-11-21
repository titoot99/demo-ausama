import pytest
from app import app,db,User,ServiceOrder
from werkzeug.security import generate_password_hash

@pytest.fixture()
def client(tmp_path):
    app.config.update(TESTING=True,SQLALCHEMY_DATABASE_URI="sqlite:///"+str(tmp_path/"test.db"),WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.drop_all(); db.create_all()
        db.session.add(User(username="admin",password_hash=generate_password_hash("secret123")))
        db.session.commit()
    with app.test_client() as c: yield c

def login(c): return c.post("/login",data={"username":"admin","password":"secret123"},follow_redirects=True)

def test_login_and_dashboard(client):
    r=login(client); assert r.status_code==200; assert "الطلبات" in r.get_data(as_text=True)

def test_create_order(client):
    login(client)
    r=client.post("/orders/new",data={"title":"اختبار","address":"الحلة","description":"طلب تجريبي","priority":"high","status":"new"},follow_redirects=True)
    assert r.status_code==200
    with app.app_context(): assert ServiceOrder.query.filter_by(title="اختبار").count()==1
