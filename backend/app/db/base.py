from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Removed model imports to avoid circular import issues
# Models should import Base from here, but this file should not import models

# Importing models after Base initialization ensures they are registered with Base.metadata for Alembic autogenerate