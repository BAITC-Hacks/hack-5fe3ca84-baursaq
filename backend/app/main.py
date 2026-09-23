import os
import secrets
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .agent.service import recommend
from .domain import Engine
from .schemas import CompleteRequest, LoginRequest, RecommendationRequest
from .store import ROOT, Store, decode_employees, decode_history

load_dotenv(ROOT / '.env')


def create_app(store=None):
    app = FastAPI(title='Career Quest API', version='0.1.0')
    store = store or Store()
    engine = Engine(store)
    sessions = {}
    app.state.store, app.state.engine = store, engine

    def session(authorization: str = Header(default='')):
        token = authorization.removeprefix('Bearer ')
        account = sessions.get(token)
        if not account or account['expires_at'] < time.time():
            raise HTTPException(401, 'Войдите в демо-сессию')
        return account

    def hr(account=Depends(session)):
        if account['role'] != 'hr':
            raise HTTPException(403, 'Доступно только HR')
        return account

    def authorize_employee(employee_id, account):
        if account['role'] != 'hr' and account['employee_id'] != employee_id:
            raise HTTPException(403, 'Недоступен профиль другого сотрудника')
        if employee_id not in store.employees:
            raise HTTPException(404, 'Сотрудник не найден')

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'as_of_date': store.as_of_date, 'employee_count': len(store.employees),
                'agent_configured': bool(os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_MODEL'))}

    @app.get('/api/demo/accounts')
    def accounts():
        # Public only because this dataset contains fictional demonstration identities.
        return [{'employee_id': e['employee_id'], 'full_name': e['full_name']} for e in store.employees.values()]

    @app.post('/api/auth/login')
    def login(body: LoginRequest):
        variable, default = ('HR_PASSWORD', 'hr-demo') if body.role == 'hr' else ('EMPLOYEE_PASSWORD', 'employee-demo')
        if not secrets.compare_digest(body.password, os.getenv(variable, default)):
            raise HTTPException(401, 'Неверный пароль')
        if body.role == 'employee' and body.employee_id not in store.employees:
            raise HTTPException(400, 'Выберите существующего сотрудника')
        token = secrets.token_urlsafe(32)
        sessions[token] = {'role': body.role, 'employee_id': body.employee_id if body.role == 'employee' else None,
                           'expires_at': time.time() + 8*60*60}
        return {'token': token, 'role': body.role, 'employee_id': sessions[token]['employee_id']}

    @app.post('/api/auth/logout')
    def logout(authorization: str = Header(default='')):
        sessions.pop(authorization.removeprefix('Bearer '), None)
        return {'ok': True}

    @app.get('/api/employees')
    def employees(account=Depends(session)):
        return [{k: e[k] for k in ('employee_id', 'full_name', 'role', 'grade', 'department')}
                for e in store.employees.values() if account['role'] == 'hr' or e['employee_id'] == account['employee_id']]

    @app.get('/api/employees/{employee_id}')
    def profile(employee_id: str, account=Depends(session)):
        authorize_employee(employee_id, account)
        with store.lock:
            return engine.profile(employee_id)

    @app.get('/api/employees/{employee_id}/candidates')
    def candidates(employee_id: str, account=Depends(session)):
        authorize_employee(employee_id, account)
        with store.lock:
            return engine.candidates(employee_id)

    @app.post('/api/employees/{employee_id}/recommendations')
    async def recommendations(employee_id: str, body: RecommendationRequest, account=Depends(session)):
        authorize_employee(employee_id, account)
        return await recommend(engine, employee_id, body.language)

    @app.post('/api/employees/{employee_id}/complete')
    def complete(employee_id: str, body: CompleteRequest, account=Depends(session)):
        authorize_employee(employee_id, account)
        try:
            return engine.complete(employee_id, body.event_id)
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @app.get('/api/hr/summary')
    def summary(_account=Depends(hr)):
        with store.lock:
            return engine.hr_summary()

    @app.post('/api/import')
    async def import_data(employees: UploadFile = File(...), history: UploadFile | None = File(None), _account=Depends(hr)):
        async def read_upload(upload):
            content = await upload.read(5*1024*1024+1)
            if len(content) > 5*1024*1024:
                raise ValueError('Размер файла превышает 5 МБ')
            return content.decode('utf-8-sig')
        try:
            profiles = decode_employees(await read_upload(employees))
            records = decode_history(await read_upload(history)) if history else []
            return store.import_data(profiles, records)
        except (ValueError, UnicodeError, TypeError) as error:
            raise HTTPException(400, str(error)) from error

    dist = ROOT / 'frontend' / 'dist'
    if (dist / 'assets').exists():
        app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='assets')

    @app.get('/')
    def index():
        if (dist / 'index.html').exists():
            return FileResponse(dist / 'index.html')
        return {'message': 'Frontend ещё не собран. Запустите python run.py --setup', 'api_docs': '/docs'}

    return app


app = create_app()
