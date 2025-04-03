import time
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict
from .models import (
    ExecutionTime, ExecutionSession, ExecutionOrder, 
    TimelineEvent, GitTracking, get_sync_engine, get_async_engine
)

async def save_execution_session(
    session: AsyncSession,
    execution_session_id: str,
    execution_times: dict,
    execution_order: list,
    timeline_events: list,
    git_commit: Optional[str] = None
):
    async with session.begin():
        # Create new session
        new_session = ExecutionSession(
            session_id=execution_session_id,
            timestamp=time.time()
        )
        session.add(new_session)
        
        # Add execution times
        for func_name, times in execution_times.items():
            for exec_time in times:
                session.add(ExecutionTime(
                    session_id=execution_session_id,
                    function_name=func_name,
                    execution_time=exec_time
                ))
        
        # Add execution order
        for idx, (func_name, exec_time) in enumerate(execution_order):
            session.add(ExecutionOrder(
                session_id=execution_session_id,
                order_index=idx,
                function_name=func_name,
                execution_time=exec_time
            ))
        
        # Add timeline events
        for func_name, start, end in timeline_events:
            session.add(TimelineEvent(
                session_id=execution_session_id,
                function_name=func_name,
                start_time=start,
                end_time=end
            ))
        
        # Add Git tracking if available
        if git_commit:
            session.add(GitTracking(
                session_id=execution_session_id,
                git_commit=git_commit,
                timestamp=time.time()
            ))
        
        await session.commit()

def get_execution_stats(session: Session):
    query = (
        select(
            ExecutionTime.function_name,
            func.count().label('execution_count'),
            func.min(ExecutionTime.execution_time).label('min_time'),
            func.avg(ExecutionTime.execution_time).label('avg_time'),
            func.max(ExecutionTime.execution_time).label('max_time'),
            ExecutionTime.session_id  # Add session_id to the query
        )
        .join(ExecutionSession)
        .group_by(ExecutionTime.session_id, ExecutionTime.function_name)
        .order_by(ExecutionSession.timestamp)  # Order by timestamp to maintain chronological order
    )
    
    return session.execute(query)

async def get_last_session_data(session: AsyncSession):
    # Get the latest session
    stmt = select(ExecutionSession).order_by(ExecutionSession.timestamp.desc()).limit(1)
    result = await session.execute(stmt)
    session_row = result.scalar_one_or_none()
    
    if not session_row:
        return None, None, None
    
    # Get execution times
    stmt = select(ExecutionTime).where(ExecutionTime.session_id == session_row.session_id)
    result = await session.execute(stmt)
    exec_times = result.all()
    execution_times = defaultdict(list)
    for row in exec_times:
        execution_times[row.ExecutionTime.function_name].append(row.ExecutionTime.execution_time)
    
    # Get execution order
    stmt = select(ExecutionOrder).where(
        ExecutionOrder.session_id == session_row.session_id
    ).order_by(ExecutionOrder.order_index)
    result = await session.execute(stmt)
    exec_order = [(row.ExecutionOrder.function_name, row.ExecutionOrder.execution_time) 
                 for row in result.all()]
    
    # Get timeline events
    stmt = select(TimelineEvent).where(
        TimelineEvent.session_id == session_row.session_id
    ).order_by(TimelineEvent.start_time)
    result = await session.execute(stmt)
    timeline = [(row.TimelineEvent.function_name, 
                row.TimelineEvent.start_time,
                row.TimelineEvent.end_time) 
               for row in result.all()]
    
    return execution_times, exec_order, timeline