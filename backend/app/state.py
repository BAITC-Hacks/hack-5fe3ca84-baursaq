from app.config import settings
from app.services.store import DataStore

store = DataStore(settings.data_dir)
