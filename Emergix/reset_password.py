from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
db = SQLAlchemy(app)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_management = db.Column(db.Boolean, default=False)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
if __name__ == '__main__':
    with app.app_context():
        management_username = 'management'  # Replace with the actual username
        new_password = 'management123'      # Replace with your desired new password
        user = User.query.filter_by(username=management_username).first()
        if user and user.is_management:
            user.set_password(new_password)
            db.session.commit()
            print(f"Password for user '{management_username}' has been reset successfully to '{new_password}'. You can now log in with this new password.")
        elif not user:
            print(f"User '{management_username}' not found.")
        else:
            print(f"User '{management_username}' is not a management user.")