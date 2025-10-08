@echo off
echo ================================================
echo PostgreSQL Storage Backend - Test Suite
echo ================================================
echo.

REM Set PostgreSQL connection
set POSTGRES_URL=postgresql://ai_foundation:ai_foundation_pass@localhost:5432/ai_foundation

echo [1/5] Checking PostgreSQL connection...
python -c "import psycopg2; conn = psycopg2.connect('%POSTGRES_URL%'); print(' PostgreSQL connected'); conn.close()" || goto :error

echo.
echo [2/5] Running schema creation tests...
pytest tests\test_postgresql_storage.py::TestPostgreSQLSchema -v || goto :error

echo.
echo [3/5] Running CRUD operation tests...
pytest tests\test_postgresql_storage.py::TestNoteOperations -v || goto :error

echo.
echo [4/5] Running concurrent write tests (10 AIs)...
pytest tests\test_postgresql_storage.py::TestConcurrentWrites::test_10_concurrent_writes -v || goto :error

echo.
echo [5/5] Running storage adapter tests...
pytest tests\test_postgresql_storage.py::TestStorageAdapter -v || goto :error

echo.
echo ================================================
echo  ALL TESTS PASSED
echo ================================================
goto :end

:error
echo.
echo ================================================
echo  TESTS FAILED
echo ================================================
exit /b 1

:end
