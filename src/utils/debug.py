import time
import asyncio
import functools
import atexit
import signal
import sys
import uuid
import subprocess
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select
from .models import get_async_engine, init_db, ExecutionSession
from .visualization import show_execution_visuals
from .db_operations import save_execution_session


class ExecutionTracker:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExecutionTracker, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.execution_times = defaultdict(list)
        self.execution_order = []
        self.timeline_events = []
        self._execution_data_shown = False
        self.execution_session_id = str(uuid.uuid4())
        self._setup_handlers()
        self.git_performance_branch = "performance_tracking"
        self._db_initialized = False  # New flag to track DB initialization

    async def _ensure_db_initialized(self, db_uri="execution_data.db"):
        if not self._db_initialized:
            engine = get_async_engine(db_uri)
            await init_db(engine)
            await engine.dispose()
            self._db_initialized = True

    async def save_execution_data(self, db_uri="execution_data.db"):
        await self._ensure_db_initialized(db_uri)  # Ensure DB is initialized before saving
        engine = get_async_engine(db_uri)
        async_session = async_sessionmaker(engine, class_=AsyncSession)
        
        async with async_session() as session:
            try:
                result = await session.execute(
                    select(ExecutionSession)
                    .where(ExecutionSession.session_id == self.execution_session_id)
                )
                existing_session = result.scalar_one_or_none()
                
                if existing_session is None:
                    git_commit = self.get_git_info()
                    await save_execution_session(
                        session=session,
                        execution_session_id=self.execution_session_id,
                        execution_times=self.execution_times,
                        execution_order=self.execution_order,
                        timeline_events=self.timeline_events,
                        git_commit=git_commit
                    )
            except Exception as e:
                print(f"Error saving execution data: {e}")
                raise

    def _setup_handlers(self):
        atexit.register(self._handle_exit)
        sys.excepthook = self._sync_handle_excepthook  # Changed to sync version
        
        for sig_name in ['SIGINT', 'SIGTERM', 'SIGHUP']:
            if hasattr(signal, sig_name):
                try:
                    signal.signal(getattr(signal, sig_name), self._handle_exit)
                except (ValueError, RuntimeError):
                    pass

    def _handle_exit(self, signum=None, frame=None):
        try:
            loop = asyncio.new_event_loop()  # Create new event loop
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_cleanup())
            loop.close()
        except Exception as e:
            print(f"Error during exit cleanup: {e}", file=sys.stderr)
        finally:
            sys.exit(0)

    def _sync_handle_excepthook(self, exc_type, exc_value, traceback):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_cleanup())
            loop.close()
        except Exception as e:
            print(f"Error during exception cleanup: {e}", file=sys.stderr)
        finally:
            sys.__excepthook__(exc_type, exc_value, traceback)

    async def _async_cleanup(self):
        """Centralized async cleanup method"""
        try:
            await self.save_execution_data()
            self.show_execution_times()
        except Exception as e:
            print(f"Error during async cleanup: {e}", file=sys.stderr)

    def show_execution_times(self):
        if self._execution_data_shown:
            return
        self._execution_data_shown = True  # Fix: use self. instead of local variable

        try:
            self.fetch_last_session_data()
        except Exception as e:
            print(f"Error executing: {e}", file=sys.stderr)

    # Move fetch_last_session_data outside of show_execution_times
    def fetch_last_session_data(self):
        try:
            show_execution_visuals()
        except Exception as e:
            print(f"Error loading data: {e}", file=sys.stderr)

    def timing_decorator(self, func):
        """
        Decorador que mide el tiempo de ejecución de funciones y almacena los resultados.
        Compatible con funciones síncronas y asíncronas.
        """
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            return mid_wrapper(result, start_time)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            return mid_wrapper(result, start_time)

        def mid_wrapper(result, start_time):
            end_time = time.time()
            execution_time = end_time - start_time
            self.execution_times[func.__name__].append(execution_time)
            self.execution_order.append((func.__name__, execution_time))
            self.timeline_events.append((func.__name__, start_time, end_time))
            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    def get_git_info(self):
        """Get current Git commit information"""
        try:
            # Get current branch
            current_branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                text=True
            ).strip()
            
            # Create performance branch if it doesn't exist
            subprocess.run(
                ["git", "branch", "--no-track", self.git_performance_branch],
                capture_output=True,
                check=False
            )
            
            # Stash changes, switch to performance branch, and apply changes
            subprocess.run(["git", "stash"], capture_output=True)
            subprocess.run(["git", "checkout", self.git_performance_branch], capture_output=True)
            subprocess.run(["git", "stash", "apply"], capture_output=True)
            
            # Create commit with execution session ID
            commit_message = f"Performance measurement session: {self.execution_session_id}"
            subprocess.run(["git", "add", "."], capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                capture_output=True,
                text=True
            )
            
            # Get commit hash
            commit_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                text=True
            ).strip()
            
            # Switch back to original branch
            subprocess.run(["git", "checkout", current_branch], capture_output=True)
            
            return commit_hash
        except Exception as e:
            print(f"Error getting Git info: {e}", file=sys.stderr)
            return None

_tracker = ExecutionTracker()

# Alias para mayor comodidad
def timeit(func):
    return _tracker.timing_decorator(func)

def show_execution_times():
    _tracker.show_execution_times()

async def save_execution_data(db_uri="execution_data.db"):
    await _tracker.save_execution_data(db_uri)