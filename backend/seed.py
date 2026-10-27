from app.database import SessionLocal, init_db
from app.models import Task, User
init_db()
db = SessionLocal()
user = db.query(User).first() or User(phone_number='+15550007777')
db.add(user)
db.commit()
task = Task(user_id=user.id, title='Review Hackathon Submission', first_micro_step='Check README and verify API endpoints', estimated_minutes=15, energy_required='high', status='in_progress')
db.add(task)
db.commit()
print('Successfully seeded task:', task.title)
