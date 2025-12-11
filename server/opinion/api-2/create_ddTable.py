import os
from sqlalchemy import create_engine
from shared.models import Base, DDQuestion, DDQuestionReferencedDoc

def create_tables():
    # Get your database connection string from environment variables
    database_url = "postgresql://aishopmain:Upka6iAo4nvktFKP8th4T6N5AV33ukFuqfZ1URP@alchemy-aishop-apps-db.postgres.database.azure.com:5432/postgres?sslmode=require"  # or however you store your DB connection
    
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        return
    
    # Create engine
    engine = create_engine(database_url)
    
    # Create only the new tables
    DDQuestion.__table__.create(engine, checkfirst=True)
    DDQuestionReferencedDoc.__table__.create(engine, checkfirst=True)
    
    print("Tables created successfully!")

if __name__ == "__main__":
    create_tables()