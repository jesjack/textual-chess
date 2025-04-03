import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy.orm import Session
from .models import get_sync_engine
from .db_operations import get_execution_stats

def show_execution_visuals():
    """
    Creates and displays an interactive 3D visualization of function execution statistics.
    
    The visualization shows:
    - Function execution times across different sessions
    - Number of executions per function
    - Average execution time trends
    
    The plot features:
    - 3D scatter plot with connected lines
    - Interactive legend
    - Logarithmic scale for execution times
    - Session range slider
    - Hover information with detailed statistics
    
    Returns:
        None. Displays the interactive plot in the default browser.
    """
    # Initialize database connection
    db_path = "C:/Users/jesja/PycharmProjects/chess_app/execution_data.db"
    engine = get_sync_engine(db_path)
    
    with Session(engine) as session:
        # Fetch execution statistics from database
        result = get_execution_stats(session)
        # Create data structure for DataFrame
        data = {
            'function_name': [],
            'execution_count': [],
            'min_time': [],
            'avg_time': [],
            'max_time': [],
            'session_id': []
        }
        # Populate data dictionary from query results
        for row in result:
            data['function_name'].append(row[0])
            data['execution_count'].append(row[1])
            data['min_time'].append(row[2])
            data['avg_time'].append(row[3])
            data['max_time'].append(row[4])
            data['session_id'].append(row[5])
        
        # Create DataFrame and sort by session_id to maintain chronological order
        df = pd.DataFrame(data)
        df = df.sort_values('session_id')
        # Create session numbers based on unique sorted session IDs
        session_map = {sid: idx + 1 for idx, sid in enumerate(df['session_id'].unique())}
        df['session_number'] = df['session_id'].apply(lambda x: session_map[x])
    
    # Calculate view parameters
    total_sessions = len(session_map)  # Use the number of unique sessions
    initial_visible_sessions = min(10, total_sessions)
    
    # Initialize the figure
    fig = go.Figure()

    # Generate random colors based on function names
    def get_color_from_name(func_name, alpha=0.7):
        # Use hash of function name as seed for reproducibility
        hash_val = abs(hash(func_name)) % (2**32 - 1)  # Ensure positive value within valid range
        np.random.seed(hash_val)
        rgb = np.random.rand(3)
        return f'rgba({int(rgb[0]*255)}, {int(rgb[1]*255)}, {int(rgb[2]*255)}, {alpha})'
    
    unique_functions = df['function_name'].unique()
    
    # Create traces for each function
    for idx, function in enumerate(unique_functions):
        function_data = df[df['function_name'] == function]
        color = get_color_from_name(function)
        
        # Add 3D scatter plot trace
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

    # Configure layout settings
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
        height=800,  # Increased height to accommodate slider
        margin=dict(t=100, b=100),  # Added margins for slider space
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99,
            bgcolor="rgba(255, 255, 255, 0.8)"
        )
    )

    # Add session range slider only if there are enough sessions
    if total_sessions > 1:
        fig.update_layout(
            sliders=[{
                'active': max(0, initial_visible_sessions - 2),
                'currentvalue': {
                    'prefix': 'Last sessions shown: ',
                    'font': {'size': 16},
                    'visible': True,
                    'xanchor': 'center'
                },
                'pad': {'t': 50, 'b': 10},
                'len': 0.9,  # Slider length
                'x': 0.1,    # Slider x position
                'y': 0,      # Slider y position
                'yanchor': 'bottom',
                'steps': [
                    {
                        'method': 'update',
                        'label': str(i),
                        'args': [
                            {'visible': True},
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

    # Set initial view range only if there are sessions
    if total_sessions > 0:
        fig.update_layout(
            scene=dict(
                xaxis=dict(range=[
                    max(1, total_sessions - initial_visible_sessions + 1),
                    total_sessions + 0.5
                ])
            )
        )

    # Display the interactive plot
    fig.show()

if __name__ == "__main__":
    show_execution_visuals()
