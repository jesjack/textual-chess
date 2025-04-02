import numpy as np
import sqlite3
import pandas as pd
import plotly.graph_objects as go

def show_execution_visuals():
    db_path = "C:/Users/jesja/PycharmProjects/chess_app/execution_data.db"
    db_conn = sqlite3.connect(db_path)

    query = """
    WITH SessionNumbers AS (
        SELECT session_id, ROW_NUMBER() OVER (ORDER BY session_id) as session_number
        FROM (SELECT DISTINCT session_id FROM execution_times)
    )
    SELECT 
        sn.session_number, et.function_name,
        COUNT(*) as execution_count,
        MIN(et.execution_time) as min_time,
        AVG(et.execution_time) as avg_time,
        MAX(et.execution_time) as max_time
    FROM execution_times et
    JOIN SessionNumbers sn ON et.session_id = sn.session_id
    GROUP BY sn.session_number, et.function_name
    """
    df = pd.read_sql_query(query, db_conn)
    
    total_sessions = df['session_number'].max()
    initial_visible_sessions = min(10, total_sessions)

    fig = go.Figure()

    colors = ['rgba(33, 150, 243, 0.7)', 'rgba(244, 67, 54, 0.7)', 
              'rgba(76, 175, 80, 0.7)', 'rgba(255, 152, 0, 0.7)']
    
    unique_functions = df['function_name'].unique()
    
    for idx, function in enumerate(unique_functions):
        function_data = df[df['function_name'] == function]
        color = colors[idx % len(colors)]
        
        fig.add_trace(go.Scatter3d(
            x=function_data['session_number'],
            y=[idx] * len(function_data),
            z=function_data['avg_time'],
            mode='lines+markers',
            name=function,
            line=dict(color=color, width=3),
            marker=dict(
                size=6,
                color=color
            ),
            hovertemplate=(
                "<b>%{text}</b><br>" +
                "Session: %{x}<br>" +
                "Executions: %{customdata}<br>" +
                "Avg Time: %{z:.6f}s<br>" +
                "<extra></extra>"
            ),
            text=[function] * len(function_data),
            customdata=function_data['execution_count']
        ))

    fig.update_layout(
        title={
            'text': 'Function Execution Times Analysis',
            'font': {'size': 20}
        },
        scene=dict(
            xaxis_title='Session Number',
            yaxis=dict(
                title='Function Name',
                ticktext=list(unique_functions),
                tickvals=list(range(len(unique_functions))),
                tickmode='array'
            ),
            zaxis_title='Average Execution Time (s)',
            zaxis=dict(type='log'),
            camera=dict(
                eye=dict(x=2, y=2, z=1.5),
                center=dict(x=0, y=0, z=0)
            )
        ),
        width=1000,
        height=700,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99,
            bgcolor="rgba(255, 255, 255, 0.8)"
        ),
        # Agregar slider
        sliders=[{
            'active': initial_visible_sessions - 2,  # Set initial active position
            'currentvalue': {
                'prefix': 'Last sessions shown: ',
                'font': {'size': 16}
            },
            'pad': {'t': 50},
            'steps': [
                {
                    'method': 'update',
                    'label': str(i),
                    'args': [
                        {'visible': True},  # Keep traces visible
                        {
                            'scene.xaxis.range': [
                                max(1, total_sessions - i + 1),
                                total_sessions + 0.5
                            ]
                        }
                    ]
                } for i in range(2, total_sessions + 1)
            ]
        }]
    )

    # Set initial view range
    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[
                max(1, total_sessions - initial_visible_sessions + 1),
                total_sessions + 0.5
            ])
        )
    )

    fig.show()
    db_conn.close()

if __name__ == "__main__":
    show_execution_visuals()